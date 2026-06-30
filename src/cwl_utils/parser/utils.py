"""CWL parser utility functions."""

import copy
import logging
from collections.abc import Mapping
from collections.abc import MutableMapping, MutableSequence, Sequence
from pathlib import Path
from typing import (
    Any,
    Final,
    cast,
    Literal,
    TypeAlias,
    overload,
)
from urllib.parse import unquote_plus, urlparse

from schema_salad.exceptions import ValidationException
from schema_salad.metaschema import ArraySchema
from schema_salad.runtime import file_uri, shortname, save, LoadingOptions
from schema_salad.sourceline import SourceLine, strip_dup_lineno
from schema_salad.utils import yaml_no_ts

from . import (
    Process,
    Workflow,
    WorkflowStep,
    WorkflowStepInput,
    cwl_v1_0,
    cwl_v1_0_utils,
    cwl_v1_1,
    cwl_v1_1_utils,
    cwl_v1_2,
    cwl_v1_2_utils,
    load_document_by_uri,
    OutputArraySchema,
    InputArraySchema,
    OutputParameter,
    InputParameter,
    InputRecordSchema,
    CommandOutputRecordSchema,
    OutputRecordSchema,
    InputRecordField,
    OutputRecordField,
)
from ..errors import WorkflowException
from ..types import is_sequence
from ..utils import yaml_dumps

_logger = logging.getLogger("cwl_utils")


BasicInputTypeSchemas: TypeAlias = (
    cwl_v1_0_utils.BasicInputTypeSchemas
    | cwl_v1_1_utils.BasicInputTypeSchemas
    | cwl_v1_2_utils.BasicInputTypeSchemas
)


InputTypeSchemas: TypeAlias = (
    cwl_v1_0_utils.InputTypeSchemas
    | cwl_v1_1_utils.InputTypeSchemas
    | cwl_v1_2_utils.InputTypeSchemas
)


BasicOutputTypeSchemas: TypeAlias = (
    cwl_v1_0_utils.BasicOutputTypeSchemas
    | cwl_v1_1_utils.BasicOutputTypeSchemas
    | cwl_v1_2_utils.BasicOutputTypeSchemas
)


OutputTypeSchemas: TypeAlias = (
    cwl_v1_0_utils.OutputTypeSchemas
    | cwl_v1_1_utils.OutputTypeSchemas
    | cwl_v1_2_utils.OutputTypeSchemas
)


SrcSink: TypeAlias = (
    cwl_v1_0_utils.SrcSink | cwl_v1_1_utils.SrcSink | cwl_v1_2_utils.SrcSink
)


def _compare_records(
    src: InputRecordSchema | OutputRecordSchema,
    sink: InputRecordSchema | OutputRecordSchema,
    strict: bool = False,
) -> bool:
    """
    Compare two records, ensuring they have compatible fields.

    This handles normalizing record names, which will be relative to workflow
    step, so that they can be compared.
    """
    srcfields = {
        shortname(field.name): cast(
            InputTypeSchemas | OutputTypeSchemas | None, field.type_
        )
        for field in cast(
            Sequence[InputRecordField | OutputRecordField], src.fields or []
        )
    }
    sinkfields = {
        shortname(field.name): cast(
            InputTypeSchemas | OutputTypeSchemas | None, field.type_
        )
        for field in cast(
            Sequence[InputRecordField | OutputRecordField], sink.fields or []
        )
    }
    for key in sinkfields.keys():
        if (
            not can_assign_src_to_sink(
                srcfields.get(key, "null"), sinkfields.get(key, "null"), strict
            )
            and sinkfields.get(key) is not None
        ):
            _logger.info(
                "Record comparison failure for %s and %s\n"
                "Did not match fields for %s: %s and %s",
                cast(InputRecordSchema | CommandOutputRecordSchema, src).name,
                cast(InputRecordSchema | CommandOutputRecordSchema, sink).name,
                key,
                srcfields.get(key),
                sinkfields.get(key),
            )
            return False
    return True


def can_assign_src_to_sink(
    src: InputTypeSchemas | OutputTypeSchemas | None,
    sink: InputTypeSchemas | OutputTypeSchemas | None,
    strict: bool = False,
) -> bool:
    """
    Check for identical type specifications, ignoring extra keys like inputBinding.

    src: admissible source types
    sink: admissible sink types

    In non-strict comparison, at least one source type must match one sink type,
    except for 'null'.
    In strict comparison, all source types must match at least one sink type.
    """
    if "Any" in (src, sink):
        return True
    if isinstance(src, InputArraySchema | OutputArraySchema) and isinstance(
        sink, InputArraySchema | OutputArraySchema
    ):
        return can_assign_src_to_sink(
            cast(InputTypeSchemas | OutputTypeSchemas | None, src.items),
            cast(InputTypeSchemas | OutputTypeSchemas | None, sink.items),
            strict,
        )
    if isinstance(src, InputRecordSchema | OutputRecordSchema) and isinstance(
        sink, InputRecordSchema | OutputRecordSchema
    ):
        return _compare_records(src, sink, strict)
    if isinstance(src, MutableSequence):
        if strict:
            for this_src in src:
                if not can_assign_src_to_sink(this_src, sink):
                    return False
            return True
        for this_src in src:
            if this_src != "null" and can_assign_src_to_sink(this_src, sink):
                return True
        return False
    if isinstance(sink, MutableSequence):
        for this_sink in sink:
            if can_assign_src_to_sink(src, this_sink):
                return True
        return False
    return bool(src == sink)


def check_types(
    srctype: InputTypeSchemas | OutputTypeSchemas | None,
    sinktype: InputTypeSchemas | OutputTypeSchemas | None,
    linkMerge: str | None,
    valueFrom: str | None = None,
) -> str:
    """
    Check if the source and sink types are correct.

    Acceptable types are "pass", "warning", or "exception".
    """
    if valueFrom is not None:
        return "pass"
    if linkMerge is None:
        if can_assign_src_to_sink(srctype, sinktype, strict=True):
            return "pass"
        if can_assign_src_to_sink(srctype, sinktype, strict=False):
            return "warning"
        return "exception"
    if linkMerge == "merge_nested":
        return check_types(
            ArraySchema(items=srctype, type_="array"), sinktype, None, None
        )
    if linkMerge == "merge_flattened":
        return check_types(merge_flatten_type(srctype), sinktype, None, None)
    raise ValidationException(f"Invalid value {linkMerge} for linkMerge field.")


def convert_stdstreams_to_files(process: Process) -> None:
    """Convert stdin, stdout and stderr type shortcuts to files."""
    match process:
        case cwl_v1_0.CommandLineTool():
            cwl_v1_0_utils.convert_stdstreams_to_files(process)
        case cwl_v1_1.CommandLineTool():
            cwl_v1_1_utils.convert_stdstreams_to_files(process)
        case cwl_v1_2.CommandLineTool():
            cwl_v1_2_utils.convert_stdstreams_to_files(process)


def load_inputfile_by_uri(
    version: str,
    path: str | Path,
    loadingOptions: LoadingOptions | None = None,
) -> Any:
    """Load a CWL input file from a URI or a path."""
    if isinstance(path, str):
        uri = urlparse(path)
        if not uri.scheme or uri.scheme == "file":
            real_path = Path(unquote_plus(uri.path)).resolve().as_uri()
        else:
            real_path = path
    else:
        real_path = path.resolve().as_uri()

    if version is None:
        raise ValidationException("could not get the cwlVersion")

    baseuri: str = real_path

    if loadingOptions is None:
        loadingOptions = LoadingOptions(fileuri=baseuri)

    doc = loadingOptions.fetcher.fetch_text(real_path)
    return load_inputfile_by_string(version, doc, baseuri, loadingOptions)


def load_inputfile(
    version: str,
    doc: Any,
    baseuri: str | None = None,
    loadingOptions: LoadingOptions | None = None,
) -> Any:
    """Load a CWL input file from a serialized YAML string or a YAML object."""
    if baseuri is None:
        baseuri = file_uri(str(Path.cwd())) + "/"
    if isinstance(doc, str):
        return load_inputfile_by_string(version, doc, baseuri, loadingOptions)
    return load_inputfile_by_yaml(version, doc, baseuri, loadingOptions)


def load_inputfile_by_string(
    version: str,
    string: str,
    uri: str,
    loadingOptions: LoadingOptions | None = None,
) -> Any:
    """Load a CWL input file from a serialized YAML string."""
    result = yaml_no_ts().load(string)
    return load_inputfile_by_yaml(version, result, uri, loadingOptions)


def load_inputfile_by_yaml(
    version: str,
    yaml: Any,
    uri: str,
    loadingOptions: LoadingOptions | None = None,
) -> Any:
    """Load a CWL input file from a YAML object."""
    match version:
        case "v1.0":
            return cwl_v1_0_utils.load_inputfile_by_yaml(yaml, uri, loadingOptions)
        case "v1.1":
            return cwl_v1_1_utils.load_inputfile_by_yaml(yaml, uri, loadingOptions)
        case "v1.2":
            return cwl_v1_2_utils.load_inputfile_by_yaml(yaml, uri, loadingOptions)
        case None:
            raise ValidationException("could not get the cwlVersion")
        case _:
            raise ValidationException(
                f"Version error. Did not recognise {version} as a CWL version"
            )


def load_step(
    step: WorkflowStep,
) -> Process:
    if isinstance(step.run, str):
        step_run = load_document_by_uri(
            path=step.loadingOptions.fetcher.urljoin(
                base_url=cast(str, step.loadingOptions.fileuri),
                url=step.run,
            ),
            loadingOptions=step.loadingOptions,
        )
        return cast(Process, step_run)
    return copy.deepcopy(step.run)


def merge_flatten_type(src: Any) -> Any:
    """Return the merge flattened type of the source type."""
    if isinstance(src, MutableSequence):
        return [merge_flatten_type(t) for t in src]
    if isinstance(src, ArraySchema):
        return src
    return ArraySchema(type_="array", items=src)


def param_for_source_id(
    process: Process,
    sourcenames: str | Sequence[str],
    parent: Workflow | None = None,
    scatter_context: list[tuple[int, str] | None] | None = None,
) -> (
    InputParameter | OutputParameter | MutableSequence[InputParameter | OutputParameter]
):
    """Find the process input parameter that matches one of the given sourcenames."""
    if isinstance(sourcenames, str):
        sourcenames = [sourcenames]
    params: MutableSequence[InputParameter | OutputParameter] = []
    for sourcename in sourcenames:
        if not isinstance(process, Workflow):
            for param in process.inputs:
                if param.id.split("#")[-1] == sourcename.split("#")[-1]:
                    params.append(param)
                    if scatter_context is not None:
                        scatter_context.append(None)
        targets = [process]
        if parent:
            targets.append(parent)
        for target in targets:
            if isinstance(target, Workflow):
                for inp in target.inputs:
                    if inp.id.split("#")[-1] == sourcename.split("#")[-1]:
                        params.append(inp)
                        if scatter_context is not None:
                            scatter_context.append(None)
                for step in target.steps:
                    if (
                        "/".join(sourcename.split("#")[-1].split("/")[:-1])
                        == step.id.split("#")[-1]
                        and step.out
                    ):
                        step_run = load_step(step)
                        convert_stdstreams_to_files(step_run)
                        for outp in step.out:
                            outp_id = outp if isinstance(outp, str) else outp.id
                            if (
                                outp_id.split("#")[-1].split("/")[-1]
                                == sourcename.split("#")[-1].split("/")[-1]
                            ):
                                if step_run and step_run.outputs:
                                    for output in step_run.outputs:
                                        if (
                                            output.id.split("#")[-1].split("/")[-1]
                                            == sourcename.split("#")[-1].split("/")[-1]
                                        ):
                                            params.append(output)
                                            if scatter_context is not None:
                                                match step.scatter:
                                                    case str():
                                                        scatter_context.append(
                                                            (
                                                                1,
                                                                step.scatterMethod
                                                                or "dotproduct",
                                                            )
                                                        )
                                                    case Sequence():
                                                        scatter_context.append(
                                                            (
                                                                len(step.scatter),
                                                                step.scatterMethod
                                                                or "dotproduct",
                                                            )
                                                        )
                                                    case _:
                                                        scatter_context.append(None)
    if len(params) == 1:
        return params[0]
    elif len(params) > 1:
        return params
    raise WorkflowException(
        "param {} not found in {}\n{}.".format(
            sourcename,
            yaml_dumps(save(process)),
            (f" or\n {yaml_dumps(save(parent))}" if parent is not None else ""),
        )
    )


def static_checker(workflow: Workflow) -> None:
    """Check if all source and sink types of a workflow are compatible before run time."""
    step_inputs: Final[MutableSequence[WorkflowStepInput]] = []
    step_outputs = []
    type_dict: dict[str, InputTypeSchemas | OutputTypeSchemas | None] = {}
    param_to_step: Final[MutableMapping[str, WorkflowStep]] = {}
    for step in workflow.steps:
        if step.in_ is not None:
            step_inputs.extend(step.in_)
            param_to_step.update({s.id: step for s in step.in_})
            type_dict.update(
                {
                    s.id: type_for_step_input(step, s, cast(str, workflow.cwlVersion))
                    for s in step.in_
                }
            )
        if step.out is not None:
            # FIXME: the correct behaviour here would be to create WorkflowStepOutput directly at load time
            match workflow.cwlVersion:
                case "v1.0":
                    step_outs = [
                        cwl_v1_0.WorkflowStepOutput(s) if isinstance(s, str) else s
                        for s in step.out
                    ]
                case "v1.1":
                    step_outs = [
                        cwl_v1_1.WorkflowStepOutput(s) if isinstance(s, str) else s
                        for s in step.out
                    ]
                case "v1.2":
                    step_outs = [
                        cwl_v1_2.WorkflowStepOutput(s) if isinstance(s, str) else s
                        for s in step.out
                    ]
                case _:
                    raise Exception(f"Unsupported CWL version {workflow.cwlVersion}")
            step_outputs.extend(step_outs)
            param_to_step.update({s.id: step for s in step_outs})
            type_dict.update(
                {
                    s.id: type_for_step_output(step, s.id, workflow.cwlVersion)
                    for s in step_outs
                }
            )
    src_dict = {
        **{param.id: param for param in workflow.inputs},
        **{param.id: param for param in step_outputs},
    }
    type_dict = {
        **type_dict,
        **{param.id: param.type_ for param in workflow.inputs},
        **{param.id: param.type_ for param in workflow.outputs},
    }

    step_inputs_val: Mapping[str, Sequence[SrcSink]]
    workflow_outputs_val: Mapping[str, Sequence[SrcSink]]
    match workflow.cwlVersion:
        case "v1.0":
            step_inputs_val = cwl_v1_0_utils.check_all_types(
                cast(
                    Mapping[str, cwl_v1_0.InputParameter | cwl_v1_0.WorkflowStepOutput],
                    src_dict,
                ),
                cast(MutableSequence[cwl_v1_0.WorkflowStepInput], step_inputs),
                type_dict,
            )
            workflow_outputs_val = cwl_v1_0_utils.check_all_types(
                cast(
                    Mapping[str, cwl_v1_0.InputParameter | cwl_v1_0.WorkflowStepOutput],
                    src_dict,
                ),
                workflow.outputs,
                type_dict,
            )
        case "v1.1":
            step_inputs_val = cwl_v1_1_utils.check_all_types(
                cast(
                    Mapping[
                        str,
                        cwl_v1_1.WorkflowInputParameter | cwl_v1_1.WorkflowStepOutput,
                    ],
                    src_dict,
                ),
                cast(MutableSequence[cwl_v1_1.WorkflowStepInput], step_inputs),
                type_dict,
            )
            workflow_outputs_val = cwl_v1_1_utils.check_all_types(
                cast(
                    Mapping[
                        str,
                        cwl_v1_1.WorkflowInputParameter | cwl_v1_1.WorkflowStepOutput,
                    ],
                    src_dict,
                ),
                workflow.outputs,
                type_dict,
            )
        case "v1.2":
            step_inputs_val = cwl_v1_2_utils.check_all_types(
                cast(
                    Mapping[
                        str,
                        cwl_v1_2.WorkflowInputParameter | cwl_v1_2.WorkflowStepOutput,
                    ],
                    src_dict,
                ),
                cast(MutableSequence[cwl_v1_2.WorkflowStepInput], step_inputs),
                cast(MutableMapping[str, cwl_v1_2.WorkflowStep], param_to_step),
                type_dict,
            )
            workflow_outputs_val = cwl_v1_2_utils.check_all_types(
                cast(
                    Mapping[
                        str,
                        cwl_v1_2.WorkflowInputParameter | cwl_v1_2.WorkflowStepOutput,
                    ],
                    src_dict,
                ),
                workflow.outputs,
                cast(MutableMapping[str, cwl_v1_2.WorkflowStep], param_to_step),
                type_dict,
            )
        case _ as cwlVersion:
            raise Exception(f"Unsupported CWL version {cwlVersion}")

    warnings = step_inputs_val["warning"] + workflow_outputs_val["warning"]
    exceptions = step_inputs_val["exception"] + workflow_outputs_val["exception"]

    warning_msgs = []
    exception_msgs = []
    for warning in warnings:
        src = warning.src
        sink = warning.sink
        linkMerge = warning.linkMerge

        msg = (
            SourceLine(src, "type").makeError(
                "Source '%s' of type %s may be incompatible"
                % (
                    shortname(src.id),
                    save(type_dict[src.id]),
                )
            )
            + "\n"
            + SourceLine(sink, "type").makeError(
                "  with sink '%s' of type %s"
                % (
                    shortname(sink.id),
                    save(type_dict[sink.id]),
                )
            )
        )
        if linkMerge is not None:
            msg += "\n" + SourceLine(sink).makeError(
                "  source has linkMerge method %s" % linkMerge
            )

        if warning.message is not None:
            msg += "\n" + SourceLine(sink).makeError("  " + warning.message)

        if msg:
            warning_msgs.append(msg)

    for exception in exceptions:
        src = exception.src
        sink = exception.sink
        linkMerge = exception.linkMerge
        extra_message = exception.message

        msg = (
            SourceLine(src, "type").makeError(
                "Source '%s' of type %s is incompatible"
                % (
                    shortname(src.id),
                    save(type_dict[src.id]),
                )
            )
            + "\n"
            + SourceLine(sink, "type").makeError(
                "  with sink '%s' of type %s"
                % (
                    shortname(sink.id),
                    save(type_dict[sink.id]),
                )
            )
        )
        if extra_message is not None:
            msg += "\n" + SourceLine(sink).makeError("  " + extra_message)

        if linkMerge is not None:
            msg += "\n" + SourceLine(sink).makeError(
                "  source has linkMerge method %s" % linkMerge
            )
        exception_msgs.append(msg)

    for sink in step_inputs:
        sink_type = type_dict[sink.id]
        if (
            "null" != sink_type
            and not (is_sequence(sink_type) and "null" in sink_type)
            and getattr(sink, "source", None) is None
            and getattr(sink, "default", None) is None
            and getattr(sink, "valueFrom", None) is None
        ):
            msg = SourceLine(sink).makeError(
                "Required parameter '%s' does not have source, default, or valueFrom expression"
                % shortname(sink.id),
            )
            exception_msgs.append(msg)

    all_warning_msg = strip_dup_lineno("\n".join(warning_msgs))
    all_exception_msg = strip_dup_lineno("\n" + "\n".join(exception_msgs))

    if all_warning_msg:
        _logger.warning("Workflow checker warning:\n%s", all_warning_msg)
    if exceptions:
        raise ValidationException(all_exception_msg)


@overload
def to_input_array(
    type_: InputTypeSchemas, cwlVersion: Literal["v1.0"]
) -> cwl_v1_0.InputArraySchema: ...


@overload
def to_input_array(
    type_: InputTypeSchemas, cwlVersion: Literal["v1.1"]
) -> cwl_v1_1.InputArraySchema: ...


@overload
def to_input_array(
    type_: InputTypeSchemas, cwlVersion: Literal["v1.2"]
) -> cwl_v1_2.InputArraySchema: ...


def to_input_array(
    type_: InputTypeSchemas, cwlVersion: Literal["v1.0", "v1.1", "v1.2"]
) -> InputArraySchema:
    match cwlVersion:
        case "v1.0":
            return cwl_v1_0_utils.to_input_array(
                cast(cwl_v1_0_utils.InputTypeSchemas, type_)
            )
        case "v1.1":
            return cwl_v1_1_utils.to_input_array(
                cast(cwl_v1_1_utils.InputTypeSchemas, type_)
            )
        case "v1.2":
            return cwl_v1_2_utils.to_input_array(
                cast(cwl_v1_2_utils.InputTypeSchemas, type_)
            )


@overload
def to_output_array(
    type_: OutputTypeSchemas, cwlVersion: Literal["v1.0"]
) -> cwl_v1_0.OutputArraySchema: ...


@overload
def to_output_array(
    type_: OutputTypeSchemas, cwlVersion: Literal["v1.1"]
) -> cwl_v1_1.OutputArraySchema: ...


@overload
def to_output_array(
    type_: OutputTypeSchemas, cwlVersion: Literal["v1.2"]
) -> cwl_v1_2.OutputArraySchema: ...


def to_output_array(
    type_: OutputTypeSchemas, cwlVersion: Literal["v1.0", "v1.1", "v1.2"]
) -> OutputArraySchema:
    match cwlVersion:
        case "v1.0":
            return cwl_v1_0_utils.to_output_array(
                cast(cwl_v1_0_utils.OutputTypeSchemas, type_)
            )
        case "v1.1":
            return cwl_v1_1_utils.to_output_array(
                cast(cwl_v1_1_utils.OutputTypeSchemas, type_)
            )
        case "v1.2":
            return cwl_v1_2_utils.to_output_array(
                cast(cwl_v1_2_utils.OutputTypeSchemas, type_)
            )


def type_for_source(
    process: Process,
    sourcenames: str | list[str],
    parent: Workflow | None = None,
    linkMerge: str | None = None,
    pickValue: str | None = None,
) -> Any:
    """Determine the type for the given sourcenames."""
    match process.cwlVersion:
        case "v1.0":
            return cwl_v1_0_utils.type_for_source(
                process,
                sourcenames,
                cast(cwl_v1_0.Workflow | None, parent),
                linkMerge,
            )
        case "v1.1":
            return cwl_v1_1_utils.type_for_source(
                process,
                sourcenames,
                cast(cwl_v1_1.Workflow | None, parent),
                linkMerge,
            )
        case "v1.2":
            return cwl_v1_2_utils.type_for_source(
                process,
                sourcenames,
                cast(cwl_v1_2.Workflow | None, parent),
                linkMerge,
                pickValue,
            )
        case None:
            raise ValidationException("could not get the cwlVersion")
        case _ as cwlVersion:
            raise ValidationException(
                f"Version error. Did not recognise {cwlVersion} as a CWL version"
            )


def type_for_step_input(
    step: WorkflowStep, in_: WorkflowStepInput, cwlVersion: str
) -> InputTypeSchemas | None:
    """Determine the type for the given step output."""
    match cwlVersion:
        case "v1.0":
            return cwl_v1_0_utils.type_for_step_input(
                cast(cwl_v1_0.WorkflowStep, step), cast(cwl_v1_0.WorkflowStepInput, in_)
            )
        case "v1.1":
            return cwl_v1_1_utils.type_for_step_input(
                cast(cwl_v1_1.WorkflowStep, step), cast(cwl_v1_1.WorkflowStepInput, in_)
            )
        case "v1.2":
            return cwl_v1_2_utils.type_for_step_input(
                cast(cwl_v1_2.WorkflowStep, step), cast(cwl_v1_2.WorkflowStepInput, in_)
            )
        case _:
            raise Exception(f"Unsupported CWL version {cwlVersion}")


def type_for_step_output(
    step: WorkflowStep, sourcename: str, cwlVersion: str
) -> OutputTypeSchemas | None:
    """Determine the type for the given step output."""
    match cwlVersion:
        case "v1.0":
            return cwl_v1_0_utils.type_for_step_output(
                cast(cwl_v1_0.WorkflowStep, step), sourcename
            )
        case "v1.1":
            return cwl_v1_1_utils.type_for_step_output(
                cast(cwl_v1_1.WorkflowStep, step), sourcename
            )
        case "v1.2":
            return cwl_v1_2_utils.type_for_step_output(
                cast(cwl_v1_2.WorkflowStep, step), sourcename
            )
        case _:
            raise Exception(f"Unsupported CWL version {cwlVersion}")

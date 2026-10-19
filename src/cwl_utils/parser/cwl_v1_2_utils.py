# SPDX-License-Identifier: Apache-2.0
import hashlib
import logging
from collections import namedtuple
from collections.abc import MutableMapping, MutableSequence
from io import StringIO
from pathlib import Path
from typing import IO, Any, cast
from urllib.parse import urldefrag

from schema_salad.exceptions import ValidationException
from schema_salad.metaschema import ArraySchema, RecordSchema
from schema_salad.runtime import LoadingOptions, shortname, file_uri, save
from schema_salad.sourceline import SourceLine, add_lc_filename
from schema_salad.utils import aslist, json_dumps, yaml_no_ts

import cwl_utils.parser
import cwl_utils.parser.cwl_v1_2 as cwl
import cwl_utils.parser.utils
from cwl_utils.errors import WorkflowException
from cwl_utils.utils import yaml_dumps

CONTENT_LIMIT: int = 64 * 1024

_logger = logging.getLogger("cwl_utils")

SrcSink = namedtuple("SrcSink", ["src", "sink", "linkMerge", "message"])


def _compare_type(type1: Any, type2: Any) -> bool:
    match (type1, type1):
        case ArraySchema() as t1, ArraySchema() as t2:
            return _compare_type(t1.items, t2.items)
        case RecordSchema(), RecordSchema():
            fields1 = {
                shortname(field.name): field.type_ for field in (type1.fields or {})
            }
            fields2 = {
                shortname(field.name): field.type_ for field in (type2.fields or {})
            }
            if fields1.keys() != fields2.keys():
                return False
            return all(_compare_type(fields1[k], fields2[k]) for k in fields1.keys())
        case MutableSequence(), MutableSequence():
            if len(type1) != len(type2):
                return False
            for t3 in type1:
                if not any(_compare_type(t3, t2) for t2 in type2):
                    return False
            return True
    return bool(type1 == type2)


def _is_all_output_method_loop_step(
    param_to_step: dict[str, cwl.WorkflowStep], parm_id: str
) -> bool:
    if (source_step := param_to_step.get(parm_id)) is not None:
        for requirement in source_step.requirements or []:
            if isinstance(requirement, cwl.Loop) and requirement.outputMethod == "all":
                return True
    return False


def _is_conditional_step(
    param_to_step: dict[str, cwl.WorkflowStep], parm_id: str
) -> bool:
    if (source_step := param_to_step.get(parm_id)) is not None:
        if source_step.when is not None:
            return True
    return False


def _inputfile_load(
    doc: str | MutableMapping[str, Any] | MutableSequence[Any],
    baseuri: str,
    loadingOptions: LoadingOptions,
    addl_metadata_fields: MutableSequence[str] | None = None,
) -> tuple[Any, LoadingOptions]:
    loader = cwl.CWLInputFileLoader
    match doc:
        case str():
            url = loadingOptions.fetcher.urljoin(baseuri, doc)
            if url in loadingOptions.idx:
                return loadingOptions.idx[url]
            doc_url, frg = urldefrag(url)
            text = loadingOptions.fetcher.fetch_text(doc_url)
            textIO = StringIO(text)
            textIO.name = doc_url
            yaml = yaml_no_ts()
            result = yaml.load(textIO)
            add_lc_filename(result, doc_url)
            loadingOptions = LoadingOptions(copyfrom=loadingOptions, fileuri=doc_url)
            _inputfile_load(
                result,
                doc_url,
                loadingOptions,
            )
            return loadingOptions.idx[url]
        case MutableMapping():
            addl_metadata = {}
            if addl_metadata_fields is not None:
                for mf in addl_metadata_fields:
                    if mf in doc:
                        addl_metadata[mf] = doc[mf]

            loadingOptions = LoadingOptions(
                copyfrom=loadingOptions,
                baseuri=baseuri,
                addl_metadata=addl_metadata,
            )

            loadingOptions.idx[baseuri] = (
                loader.load(doc, baseuri, loadingOptions, docRoot=baseuri),
                loadingOptions,
            )

            return loadingOptions.idx[baseuri]

        case MutableSequence():
            loadingOptions.idx[baseuri] = (
                loader.load(doc, baseuri, loadingOptions),
                loadingOptions,
            )
            return loadingOptions.idx[baseuri]

        case _:
            raise ValidationException(
                "Expected URI string, MutableMapping or MutableSequence, got %s"
                % type(doc)
            )


def check_all_types(
    src_dict: dict[str, Any],
    sinks: MutableSequence[cwl.WorkflowStepInput | cwl.WorkflowOutputParameter],
    param_to_step: dict[str, cwl.WorkflowStep],
    type_dict: dict[str, Any],
) -> dict[str, list[SrcSink]]:
    """Given a list of sinks, check if their types match with the types of their sources."""
    validation: dict[str, list[SrcSink]] = {"warning": [], "exception": []}
    for sink in sinks:
        extra_message = (
            "pickValue is %s" % sink.pickValue if sink.pickValue is not None else None
        )
        sink_type = type_dict[sink.id]
        match sink:
            case cwl.WorkflowOutputParameter():
                sourceName = "outputSource"
                sourceField = sink.outputSource
            case cwl.WorkflowStepInput():
                sourceName = "source"
                sourceField = sink.source
            case _:
                continue
        if sourceField is not None:
            if isinstance(sourceField, MutableSequence) and len(sourceField) > 1:
                linkMerge: str | None = sink.linkMerge or (
                    "merge_nested" if len(sourceField) > 1 else None
                )
                if sink.pickValue in ("first_non_null", "the_only_non_null"):
                    linkMerge = None
                srcs_of_sink = []
                for parm_id in sourceField:
                    srcs_of_sink += [src_dict[parm_id]]
                    if (
                        _is_conditional_step(param_to_step, parm_id)
                        and sink.pickValue is None
                    ):
                        src_typ = aslist(type_dict[src_dict[parm_id].id])
                        if "null" not in src_typ:
                            src_typ = ["null"] + cast(list[Any], src_typ)
                        if (
                            not isinstance(sink_type, MutableSequence)
                            or "null" not in sink_type
                        ):
                            validation["warning"].append(
                                SrcSink(
                                    src_dict[parm_id],
                                    sink,
                                    linkMerge,
                                    message="Source is from conditional step, but pickValue is not used",
                                )
                            )
                        type_dict[src_dict[parm_id].id] = src_typ
                    if _is_all_output_method_loop_step(param_to_step, parm_id):
                        src_typ = type_dict[src_dict[parm_id].id]
                        type_dict[src_dict[parm_id].id] = ArraySchema(
                            items=src_typ, type_="array"
                        )
            else:
                if isinstance(sourceField, MutableSequence):
                    parm_id = cast(str, sourceField[0])
                else:
                    parm_id = cast(str, sourceField)
                if parm_id not in src_dict:
                    raise SourceLine(sink, sourceName, ValidationException).makeError(
                        f"{sourceName} not found: {parm_id}"
                    )
                srcs_of_sink = [src_dict[parm_id]]
                linkMerge = None
                if sink.pickValue is not None:
                    validation["warning"].append(
                        SrcSink(
                            src_dict[parm_id],
                            sink,
                            linkMerge,
                            message="pickValue is used but only a single input source is declared",
                        )
                    )
                if _is_conditional_step(param_to_step, parm_id):
                    src_typ = aslist(type_dict[src_dict[parm_id].id])
                    snk_typ = type_dict[sink.id]
                    if "null" not in src_typ:
                        src_typ = ["null"] + cast(list[Any], src_typ)
                    if (
                        not isinstance(snk_typ, MutableSequence)
                        or "null" not in snk_typ
                    ):
                        validation["warning"].append(
                            SrcSink(
                                src_dict[parm_id],
                                sink,
                                linkMerge,
                                message="Source is from conditional step and may produce `null`",
                            )
                        )
                    type_dict[src_dict[parm_id].id] = src_typ
                if _is_all_output_method_loop_step(param_to_step, parm_id):
                    src_typ = type_dict[src_dict[parm_id].id]
                    type_dict[src_dict[parm_id].id] = ArraySchema(
                        items=src_typ, type_="array"
                    )
            for src in srcs_of_sink:
                check_result = cwl_utils.parser.utils.check_types(
                    type_dict[cast(str, src.id)],
                    sink_type,
                    linkMerge,
                    getattr(sink, "valueFrom", None),
                )
                if check_result in ("warning", "exception"):
                    validation[check_result].append(
                        SrcSink(src, sink, linkMerge, extra_message)
                    )
    return validation


def content_limit_respected_read_bytes(f: IO[bytes]) -> bytes:
    """
    Read file content up to 64 kB as a byte array.

    Throw exception for larger files (see https://www.commonwl.org/v1.2/Workflow.html#Changelog).
    """
    contents = f.read(CONTENT_LIMIT + 1)
    if len(contents) > CONTENT_LIMIT:
        raise WorkflowException(
            "file is too large, loadContents limited to %d bytes" % CONTENT_LIMIT
        )
    return contents


def content_limit_respected_read(f: IO[bytes]) -> str:
    """
    Read file content up to 64 kB as an utf-8 encoded string.

    Throw exception for larger files (see https://www.commonwl.org/v1.2/Workflow.html#Changelog).
    """
    return content_limit_respected_read_bytes(f).decode("utf-8")


def convert_stdstreams_to_files(clt: cwl.CommandLineTool) -> None:
    """Convert stdin, stdout and stderr type shortcuts to files."""
    for out in clt.outputs:
        if out.type_ == "stdout":
            if out.outputBinding is not None:
                raise ValidationException(
                    "Not allowed to specify outputBinding when using stdout shortcut."
                )
            if clt.stdout is None:
                clt.stdout = hashlib.sha1(  # nosec
                    json_dumps(clt.save(), sort_keys=True).encode("utf-8")
                ).hexdigest()
            out.type_ = "File"
            out.outputBinding = cwl.CommandOutputBinding(glob=clt.stdout)
        elif out.type_ == "stderr":
            if out.outputBinding is not None:
                raise ValidationException(
                    "Not allowed to specify outputBinding when using stderr shortcut."
                )
            if clt.stderr is None:
                clt.stderr = hashlib.sha1(  # nosec
                    json_dumps(clt.save(), sort_keys=True).encode("utf-8")
                ).hexdigest()
            out.type_ = "File"
            out.outputBinding = cwl.CommandOutputBinding(glob=clt.stderr)
    for inp in clt.inputs:
        if inp.type_ == "stdin":
            if inp.inputBinding is not None:
                raise ValidationException(
                    "Not allowed to specify unputBinding when using stdin shortcut."
                )
            if clt.stdin is not None:
                raise ValidationException(
                    "Not allowed to specify stdin path when using stdin type shortcut."
                )
            else:
                clt.stdin = (
                    "$(inputs.%s.path)"
                    % cast(str, inp.id).rpartition("#")[2].split("/")[-1]
                )
                inp.type_ = "File"


def load_inputfile(
    doc: Any,
    baseuri: str | None = None,
    loadingOptions: LoadingOptions | None = None,
) -> Any:
    """Load a CWL v1.2 input file from a serialized YAML string or a YAML object."""
    if baseuri is None:
        baseuri = file_uri(str(Path.cwd())) + "/"
    if loadingOptions is None:
        loadingOptions = LoadingOptions()

    result, metadata = _inputfile_load(
        doc,
        baseuri,
        loadingOptions,
    )
    return result


def load_inputfile_by_string(
    string: Any,
    uri: str,
    loadingOptions: LoadingOptions | None = None,
) -> Any:
    """Load a CWL v1.2 input file from a serialized YAML string."""
    result = yaml_no_ts().load(string)
    add_lc_filename(result, uri)

    if loadingOptions is None:
        loadingOptions = LoadingOptions(fileuri=uri)

    result, metadata = _inputfile_load(
        result,
        uri,
        loadingOptions,
    )
    return result


def load_inputfile_by_yaml(
    yaml: Any,
    uri: str,
    loadingOptions: LoadingOptions | None = None,
) -> Any:
    """Load a CWL v1.2 input file from a YAML object."""
    add_lc_filename(yaml, uri)

    if loadingOptions is None:
        loadingOptions = LoadingOptions(fileuri=uri)

    result, metadata = _inputfile_load(
        yaml,
        uri,
        loadingOptions,
    )
    return result


def type_for_step_input(
    step: cwl.WorkflowStep,
    in_: cwl.WorkflowStepInput,
) -> Any:
    """Determine the type for the given step input."""
    if in_.valueFrom is not None:
        return "Any"
    if step_run := cwl_utils.parser.utils.load_step(step):
        cwl_utils.parser.utils.convert_stdstreams_to_files(step_run)
        for step_input in cast(cwl_utils.parser.Process, step_run).inputs or []:
            if cast(str, step_input.id).split("#")[-1] == in_.id.split("#")[-1]:
                input_type = step_input.type_
                if step.scatter is not None and in_.id in aslist(step.scatter):
                    input_type = ArraySchema(items=input_type, type_="array")
                return input_type
    return "Any"


def type_for_step_output(
    step: cwl.WorkflowStep,
    sourcename: str,
) -> Any:
    """Determine the type for the given step output."""
    if step_run := cwl_utils.parser.utils.load_step(step):
        cwl_utils.parser.utils.convert_stdstreams_to_files(step_run)
        for output in cast(cwl_utils.parser.Process, step_run).outputs or []:
            if (
                output.id.split("#")[-1].split("/")[-1]
                == sourcename.split("#")[-1].split("/")[-1]
            ):
                output_type = output.type_
                if step.scatter is not None:
                    if step.scatterMethod == "nested_crossproduct":
                        for _ in range(len(aslist(step.scatter))):
                            output_type = ArraySchema(items=output_type, type_="array")
                    else:
                        output_type = ArraySchema(items=output_type, type_="array")
                return output_type
    raise ValidationException(
        "param {} not found in {}.".format(
            sourcename,
            yaml_dumps(save(step)),
        )
    )


def type_for_source(
    process: cwl.CommandLineTool | cwl.Workflow | cwl.ExpressionTool,
    sourcenames: str | list[str],
    parent: cwl.Workflow | None = None,
    linkMerge: str | None = None,
    pickValue: str | None = None,
    loaded_steps: dict[str, cwl_utils.parser.AbstractProcess] | None = None,
) -> Any:
    """Determine the type for the given sourcenames."""
    scatter_context: list[tuple[int, str] | None] = []
    params = cwl_utils.parser.utils.param_for_source_id(
        process, sourcenames, parent, scatter_context, loaded_steps
    )
    if not isinstance(params, MutableSequence):
        new_type = params.type_
        if scatter_context[0] is not None:
            if scatter_context[0][1] == "nested_crossproduct":
                for _ in range(scatter_context[0][0]):
                    new_type = ArraySchema(items=new_type, type_="array")
            else:
                new_type = ArraySchema(items=new_type, type_="array")
        if linkMerge == "merge_nested":
            new_type = ArraySchema(items=new_type, type_="array")
        elif linkMerge == "merge_flattened":
            new_type = cwl_utils.parser.utils.merge_flatten_type(new_type)
        if pickValue is not None:
            if isinstance(new_type, ArraySchema):
                if pickValue in ("first_non_null", "the_only_non_null"):
                    new_type = new_type.items
        return new_type
    new_type = []
    for p, sc in zip(params, scatter_context):
        if isinstance(p, str) and not any(_compare_type(t, p) for t in new_type):
            cur_type = p
        elif hasattr(p, "type_") and not any(
            _compare_type(t, p.type_) for t in new_type
        ):
            cur_type = p.type_
        else:
            cur_type = None
        if cur_type is not None:
            if sc is not None:
                if sc[1] == "nested_crossproduct":
                    for _ in range(sc[0]):
                        cur_type = ArraySchema(items=cur_type, type_="array")
                else:
                    cur_type = ArraySchema(items=cur_type, type_="array")
            new_type.append(cur_type)
    if len(new_type) == 1:
        new_type = new_type[0]
    if linkMerge == "merge_nested":
        new_type = ArraySchema(items=new_type, type_="array")
    elif linkMerge == "merge_flattened":
        new_type = cwl_utils.parser.utils.merge_flatten_type(new_type)
    elif isinstance(sourcenames, list) and len(sourcenames) > 1:
        new_type = ArraySchema(items=new_type, type_="array")
    if pickValue is not None:
        if isinstance(new_type, ArraySchema):
            if pickValue in ("first_non_null", "the_only_non_null"):
                new_type = new_type.items
    return new_type

# SPDX-License-Identifier: Apache-2.0
import hashlib
import logging
from typing import Any, IO, List, MutableSequence, Optional, Tuple, Union, cast

from ruamel import yaml
from schema_salad.exceptions import ValidationException
from schema_salad.utils import json_dumps

import cwl_utils.parser
import cwl_utils.parser.cwl_v1_2 as cwl
from cwl_utils.errors import WorkflowException

CONTENT_LIMIT: int = 64 * 1024

_logger = logging.getLogger("cwl_utils")


def _compare_records(
    src: cwl.RecordSchema,
    sink: cwl.RecordSchema,
    strict: bool = False
) -> bool:
    """
    Compare two records, ensuring they have compatible fields.

    This handles normalizing record names, which will be relative to workflow
    step, so that they can be compared.
    """

    srcfields = {cwl.shortname(field.name): field.type for field in (src.fields or {})}
    sinkfields = {cwl.shortname(field.name): field.type for field in (sink.fields or {})}
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
                cast(Union[cwl.InputRecordSchema, cwl.CommandOutputRecordSchema], src).name,
                cast(Union[cwl.InputRecordSchema, cwl.CommandOutputRecordSchema], sink).name,
                key,
                srcfields.get(key),
                sinkfields.get(key),
            )
            return False
    return True


def can_assign_src_to_sink(
    src: Any,
    sink: Any,
    strict: bool = False
) -> bool:
    """
    Check for identical type specifications, ignoring extra keys like inputBinding.

    src: admissible source types
    sink: admissible sink types

    In non-strict comparison, at least one source type must match one sink type,
       except for 'null'.
    In strict comparison, all source types must match at least one sink type.
    """
    if src == "Any" or sink == "Any":
        return True
    if isinstance(src, cwl.ArraySchema) and isinstance(sink, cwl.ArraySchema):
        return can_assign_src_to_sink(src.items, sink.items, strict)
    if isinstance(src, cwl.RecordSchema) and isinstance(sink, cwl.RecordSchema):
        return _compare_records(src, sink, strict)
    if hasattr(src, "type") and hasattr(sink, "type"):
        if src.type == "File" and sink.type == "File":
            for sinksf in getattr(sink, 'secondaryFiles', []):
                if not [
                    1
                    for srcsf in getattr(src, 'secondaryFiles', [])
                        if sinksf == srcsf
                ]:
                    if strict:
                        return False
            return True
        return can_assign_src_to_sink(src.type, sink.type, strict)
    if isinstance(src, MutableSequence):
        if strict:
            for this_src in src:
                if not can_assign_src_to_sink(this_src, sink):
                    return False
            return True
        for this_src in src:
            if this_src != "null" and can_assign_src_to_sink(
                this_src, sink
            ):
                return True
        return False
    if isinstance(sink, MutableSequence):
        for this_sink in sink:
            if can_assign_src_to_sink(src, this_sink):
                return True
        return False
    return bool(src == sink)


def check_types(
    srctype: Any,
    sinktype: Any,
    valueFrom: Optional[str] = None,
) -> str:
    """
    Check if the source and sink types are correct.

    Acceptable types are "pass", "warning", or "exception".
    """
    if valueFrom is not None:
        return "pass"
    if can_assign_src_to_sink(srctype, sinktype, strict=True):
        return "pass"
    if can_assign_src_to_sink(srctype, sinktype, strict=False):
        return "warning"
    return "exception"


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
    for out in clt.outputs:
        if out.type == 'stdout':
            if out.outputBinding is not None:
                raise ValidationException(
                    "Not allowed to specify outputBinding when using stdout shortcut.")
            if clt.stdout is None:
                clt.stdout = str(hashlib.sha1(json_dumps(  # nosec
                    clt.save(), sort_keys=True).encode('utf-8')).hexdigest())
            out.type = 'File'
            out.outputBinding = cwl.CommandOutputBinding(glob=clt.stdout)
        elif out.type == 'stderr':
            if out.outputBinding is not None:
                raise ValidationException(
                    "Not allowed to specify outputBinding when using stderr shortcut.")
            if clt.stderr is None:
                clt.stderr = str(hashlib.sha1(json_dumps(  # nosec
                    clt.save(), sort_keys=True).encode('utf-8')).hexdigest())
            out.type = 'File'
            out.outputBinding = cwl.CommandOutputBinding(glob=clt.stderr)
    for inp in clt.inputs:
        if inp.type == 'stdin':
            if inp.inputBinding is not None:
                raise ValidationException(
                    "Not allowed to specify unputBinding when using stdin shortcut.")
            if clt.stdin is not None:
                raise ValidationException(
                    "Not allowed to specify stdin path when using stdin type shortcut.")
            else:
                clt.stdin = '$(inputs.%s.path)' % cast(str, inp.id).rpartition('#')[2].split('/')[-1]
                inp.type = 'File'


def merge_flatten_type(src: Any) -> Any:
    """Return the merge flattened type of the source type."""
    if isinstance(src, MutableSequence):
        return [merge_flatten_type(t) for t in src]
    if isinstance(src, cwl.ArraySchema):
        return src
    return cwl.ArraySchema(type="array", items=src)


def type_for_source(
    process: Union[cwl.CommandLineTool, cwl.Workflow, cwl.ExpressionTool],
    sourcenames: Union[str, List[str]],
    parent: Optional[cwl.Workflow] = None,
    linkMerge: Optional[str] = None,
    pickValue: Optional[str] = None,
) -> Any:
    """Determine the type for the given sourcenames."""
    scatter_context: List[Optional[Tuple[int, str]]] = []
    params = param_for_source_id(process, sourcenames, parent, scatter_context)
    if not isinstance(params, list):
        new_type = params.type
        if scatter_context[0] is not None:
            if scatter_context[0][1] == 'nested_crossproduct':
                for _ in range(scatter_context[0][0]):
                    new_type = cwl.ArraySchema(items=new_type, type='array')
            else:
                new_type = cwl.ArraySchema(items=new_type, type='array')
        if linkMerge == 'merge_nested':
            new_type = cwl.ArraySchema(items=new_type, type='array')
        elif linkMerge == 'merge_flattened':
            new_type = merge_flatten_type(new_type)
        if pickValue is not None:
            if isinstance(new_type, cwl.ArraySchema):
                if pickValue in ['first_non_null', 'the_only_non_null']:
                    new_type = new_type.items
        return new_type
    new_type = []
    for p, sc in zip(params, scatter_context):
        if isinstance(p, str) and p not in new_type:
            cur_type = p
        elif hasattr(p, "type") and p.type not in new_type:
            cur_type = p.type
        else:
            cur_type = None
        if cur_type is not None:
            if sc is not None:
                if sc[1] == 'nested_crossproduct':
                    for _ in range(sc[0]):
                        cur_type = cwl.ArraySchema(items=cur_type, type='array')
                else:
                    cur_type = cwl.ArraySchema(items=cur_type, type='array')
            new_type.append(cur_type)
    if len(new_type) == 1:
        new_type = new_type[0]
    if linkMerge == 'merge_nested':
        return cwl.ArraySchema(items=new_type, type='array')
    elif linkMerge == 'merge_flattened':
        return merge_flatten_type(new_type)
    elif isinstance(sourcenames, List):
        new_type = cwl.ArraySchema(items=new_type, type='array')
    if pickValue is not None:
        if isinstance(new_type, cwl.ArraySchema):
            if pickValue in ['first_non_null', 'the_only_non_null']:
                new_type = new_type.items
    return new_type


def param_for_source_id(
    process: Union[cwl.CommandLineTool, cwl.Workflow, cwl.ExpressionTool],
    sourcenames: Union[str, List[str]],
    parent: Optional[cwl.Workflow] = None,
    scatter_context: Optional[List[Optional[Tuple[int, str]]]] = None,
) -> Union[List[cwl.WorkflowInputParameter], cwl.WorkflowInputParameter]:
    """Find the process input parameter that matches one of the given sourcenames."""
    if isinstance(sourcenames, str):
        sourcenames = [sourcenames]
    params: List[cwl.WorkflowInputParameter] = []
    for sourcename in sourcenames:
        if not isinstance(process, cwl.Workflow):
            for param in process.inputs:
                if param.id.split("#")[-1] == sourcename.split("#")[-1]:
                    params.append(param)
                    if scatter_context is not None:
                        scatter_context.append(None)
        targets = [process]
        if parent:
            targets.append(parent)
        for target in targets:
            if isinstance(target, cwl.Workflow):
                for inp in target.inputs:
                    if inp.id.split("#")[-1] == sourcename.split("#")[-1]:
                        params.append(inp)
                        if scatter_context is not None:
                            scatter_context.append(None)
                for step in target.steps:
                    if '/'.join(sourcename.split("#")[-1].split("/")[:-1]) == step.id.split("#")[-1] and step.out:
                        for outp in step.out:
                            outp_id = outp if isinstance(outp, str) else outp.id
                            if outp_id.split("#")[-1].split("/")[-1] == sourcename.split("#")[-1].split("/")[-1]:
                                step_run = step.run
                                if isinstance(step.run, str):
                                    step_run = cwl_utils.parser.load_document_by_uri(
                                        path=target.loadingOptions.fetcher.urljoin(
                                            base_url=cast(str, target.loadingOptions.fileuri),
                                            url=step.run),
                                        loadingOptions=target.loadingOptions)
                                if step_run and step_run.outputs:
                                    for output in step_run.outputs:
                                        if (
                                            output.id.split("#")[-1].split("/")[-1]
                                            == sourcename.split('#')[-1].split("/")[-1]
                                        ):
                                            params.append(output)
                                            if scatter_context is not None:
                                                if scatter_context is not None:
                                                    if isinstance(step.scatter, str):
                                                        scatter_context.append((1, step.scatterMethod or 'dotproduct'))
                                                    elif isinstance(step.scatter, MutableSequence):
                                                        scatter_context.append(
                                                            (len(step.scatter), step.scatterMethod or 'dotproduct'))
                                                    else:
                                                        scatter_context.append(None)
    if len(params) == 1:
        return params[0]
    elif len(params) > 1:
        return params
    raise WorkflowException(
        "param {} not found in {}\n{}.".format(
            sourcename,
            yaml.main.round_trip_dump(cwl.save(process)),
            " or\n {}".format(yaml.main.round_trip_dump(cwl.save(parent))) if parent is not None else "",
        )
    )

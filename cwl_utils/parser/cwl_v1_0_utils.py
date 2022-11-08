# SPDX-License-Identifier: Apache-2.0
import hashlib
from typing import IO, Any, List, MutableSequence, Optional, Tuple, Union, cast

from ruamel import yaml
from schema_salad.exceptions import ValidationException
from schema_salad.utils import json_dumps

import cwl_utils.parser
import cwl_utils.parser.cwl_v1_0 as cwl
import cwl_utils.parser.utils
from cwl_utils.errors import WorkflowException

CONTENT_LIMIT: int = 64 * 1024


def _compare_type(type1: Any, type2: Any) -> bool:
    if isinstance(type1, cwl.ArraySchema) and isinstance(type2, cwl.ArraySchema):
        return _compare_type(type1.items, type2.items)
    elif isinstance(type1, cwl.RecordSchema) and isinstance(type2, cwl.RecordSchema):
        fields1 = {
            cwl.shortname(field.name): field.type for field in (type1.fields or {})
        }
        fields2 = {
            cwl.shortname(field.name): field.type for field in (type2.fields or {})
        }
        if fields1.keys() != fields2.keys():
            return False
        return all((_compare_type(fields1[k], fields2[k]) for k in fields1.keys()))
    elif isinstance(type1, MutableSequence) and isinstance(type2, MutableSequence):
        if len(type1) != len(type2):
            return False
        for t1 in type1:
            if not any((_compare_type(t1, t2) for t2 in type2)):
                return False
        return True
    else:
        return bool(type1 == type2)


def content_limit_respected_read_bytes(f: IO[bytes]) -> bytes:
    """
    Read file content up to 64 kB as a byte array.

    Truncate content for larger files.
    """
    return f.read(CONTENT_LIMIT)


def content_limit_respected_read(f: IO[bytes]) -> str:
    """
    Read file content up to 64 kB as an utf-8 encoded string.

    Truncate content for larger files.
    """
    return content_limit_respected_read_bytes(f).decode("utf-8")


def convert_stdstreams_to_files(clt: cwl.CommandLineTool) -> None:
    """Convert stdout and stderr type shortcuts to files."""
    for out in clt.outputs:
        if out.type == "stdout":
            if out.outputBinding is not None:
                raise ValidationException(
                    "Not allowed to specify outputBinding when using stdout shortcut."
                )
            if clt.stdout is None:
                clt.stdout = str(
                    hashlib.sha1(  # nosec
                        json_dumps(clt.save(), sort_keys=True).encode("utf-8")
                    ).hexdigest()
                )
            out.type = "File"
            out.outputBinding = cwl.CommandOutputBinding(glob=clt.stdout)
        elif out.type == "stderr":
            if out.outputBinding is not None:
                raise ValidationException(
                    "Not allowed to specify outputBinding when using stderr shortcut."
                )
            if clt.stderr is None:
                clt.stderr = str(
                    hashlib.sha1(  # nosec
                        json_dumps(clt.save(), sort_keys=True).encode("utf-8")
                    ).hexdigest()
                )
            out.type = "File"
            out.outputBinding = cwl.CommandOutputBinding(glob=clt.stderr)


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
) -> Any:
    """Determine the type for the given sourcenames."""
    scatter_context: List[Optional[Tuple[int, str]]] = []
    params = param_for_source_id(process, sourcenames, parent, scatter_context)
    if not isinstance(params, list):
        new_type = params.type
        if scatter_context[0] is not None:
            if scatter_context[0][1] == "nested_crossproduct":
                for _ in range(scatter_context[0][0]):
                    new_type = cwl.ArraySchema(items=new_type, type="array")
            else:
                new_type = cwl.ArraySchema(items=new_type, type="array")
        if linkMerge == "merge_nested":
            new_type = cwl.ArraySchema(items=new_type, type="array")
        elif linkMerge == "merge_flattened":
            new_type = merge_flatten_type(new_type)
        return new_type
    new_type = []
    for p, sc in zip(params, scatter_context):
        if isinstance(p, str) and not any((_compare_type(t, p) for t in new_type)):
            cur_type = p
        elif hasattr(p, "type") and not any(
            (_compare_type(t, p.type) for t in new_type)
        ):
            cur_type = p.type
        else:
            cur_type = None
        if cur_type is not None:
            if sc is not None:
                if sc[1] == "nested_crossproduct":
                    for _ in range(sc[0]):
                        cur_type = cwl.ArraySchema(items=cur_type, type="array")
                else:
                    cur_type = cwl.ArraySchema(items=cur_type, type="array")
            new_type.append(cur_type)
    if len(new_type) == 1:
        new_type = new_type[0]
    if linkMerge == "merge_nested":
        return cwl.ArraySchema(items=new_type, type="array")
    elif linkMerge == "merge_flattened":
        return merge_flatten_type(new_type)
    elif isinstance(sourcenames, List):
        return cwl.ArraySchema(items=new_type, type="array")
    else:
        return new_type


def param_for_source_id(
    process: Union[cwl.CommandLineTool, cwl.Workflow, cwl.ExpressionTool],
    sourcenames: Union[str, List[str]],
    parent: Optional[cwl.Workflow] = None,
    scatter_context: Optional[List[Optional[Tuple[int, str]]]] = None,
) -> Union[List[cwl.InputParameter], cwl.InputParameter]:
    """Find the process input parameter that matches one of the given sourcenames."""
    if isinstance(sourcenames, str):
        sourcenames = [sourcenames]
    params: List[cwl.InputParameter] = []
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
                    if (
                        "/".join(sourcename.split("#")[-1].split("/")[:-1])
                        == step.id.split("#")[-1]
                        and step.out
                    ):
                        for outp in step.out:
                            outp_id = outp if isinstance(outp, str) else outp.id
                            if (
                                outp_id.split("#")[-1].split("/")[-1]
                                == sourcename.split("#")[-1].split("/")[-1]
                            ):
                                step_run = step.run
                                if isinstance(step.run, str):
                                    step_run = cwl_utils.parser.load_document_by_uri(
                                        path=target.loadingOptions.fetcher.urljoin(
                                            base_url=cast(
                                                str, target.loadingOptions.fileuri
                                            ),
                                            url=step.run,
                                        ),
                                        loadingOptions=target.loadingOptions,
                                    )
                                    cwl_utils.parser.utils.convert_stdstreams_to_files(
                                        step_run
                                    )
                                if step_run and step_run.outputs:
                                    for output in step_run.outputs:
                                        if (
                                            output.id.split("#")[-1].split("/")[-1]
                                            == sourcename.split("#")[-1].split("/")[-1]
                                        ):
                                            params.append(output)
                                            if scatter_context is not None:
                                                if isinstance(step.scatter, str):
                                                    scatter_context.append(
                                                        (
                                                            1,
                                                            step.scatterMethod
                                                            or "dotproduct",
                                                        )
                                                    )
                                                elif isinstance(
                                                    step.scatter, MutableSequence
                                                ):
                                                    scatter_context.append(
                                                        (
                                                            len(step.scatter),
                                                            step.scatterMethod
                                                            or "dotproduct",
                                                        )
                                                    )
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
            " or\n {}".format(yaml.main.round_trip_dump(cwl.save(parent)))
            if parent is not None
            else "",
        )
    )

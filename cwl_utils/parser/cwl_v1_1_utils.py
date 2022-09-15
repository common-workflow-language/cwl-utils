# SPDX-License-Identifier: Apache-2.0
import hashlib
from typing import Any, IO, List, MutableSequence, Optional, Tuple, Union, cast

from ruamel import yaml
from schema_salad.exceptions import ValidationException
from schema_salad.utils import json_dumps

import cwl_utils.parser
import cwl_utils.parser.cwl_v1_1 as cwl
from cwl_utils.errors import WorkflowException


CONTENT_LIMIT: int = 64 * 1024


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

def type_for_source(
    process: Union[cwl.CommandLineTool, cwl.Workflow, cwl.ExpressionTool],
    sourcenames: Union[str, List[str]],
    parent: Optional[cwl.Workflow] = None,
    linkMerge: Optional[str] = None
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
            for _ in range(len(sourcenames)):
                new_type = cwl.ArraySchema(items=new_type, type='array')
        elif isinstance(sourcenames, List):
            new_type = cwl.ArraySchema(items=new_type, type='array')
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
        for _ in range(len(sourcenames)):
            new_type = cwl.ArraySchema(items=new_type, type='array')
        return new_type
    elif isinstance(sourcenames, List):
        return cwl.ArraySchema(items=new_type, type='array')
    else:
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

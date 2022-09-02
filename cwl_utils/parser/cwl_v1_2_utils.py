# SPDX-License-Identifier: Apache-2.0
import hashlib
from typing import Any, List, Optional, Union, cast

from ruamel import yaml
from schema_salad.exceptions import ValidationException
from schema_salad.utils import json_dumps

import cwl_utils.parser.cwl_v1_2 as cwl
from cwl_utils.errors import WorkflowException


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
) -> Union[List[Any], Any]:
    """Determine the type for the given sourcenames."""
    params = param_for_source_id(process, sourcenames, parent)
    if not isinstance(params, list):
        return params.type
    new_type: List[Any] = []
    for p in params:
        if isinstance(p, str) and p not in new_type:
            new_type.append(p)
        elif hasattr(p, "type") and p.type not in new_type:
            new_type.append(p.type)
    return new_type


def param_for_source_id(
    process: Union[cwl.CommandLineTool, cwl.Workflow, cwl.ExpressionTool],
    sourcenames: Union[str, List[str]],
    parent: Optional[cwl.Workflow] = None,
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
        targets = [process]
        if parent:
            targets.append(parent)
        for target in targets:
            if isinstance(target, cwl.Workflow):
                for inp in target.inputs:
                    if inp.id.split("#")[-1] == sourcename.split("#")[-1]:
                        params.append(inp)
                for step in target.steps:
                    if sourcename.split("#")[-1].split("/")[0] == step.id.split("#")[-1] and step.out:
                        for outp in step.out:
                            outp_id = outp if isinstance(outp, str) else outp.id
                            if outp_id.split("#")[-1].split("/")[-1] == sourcename.split("#")[-1].split("/", 1)[1]:
                                if step.run and step.run.outputs:
                                    for output in step.run.outputs:
                                        if (
                                            output.id.split("#")[-1].split('/')[-1]
                                            == sourcename.split('#')[-1].split("/", 1)[1]
                                        ):
                                            params.append(output)
    if len(params) == 1:
        return params[0]
    elif len(params) > 1:
        return params
    raise WorkflowException(
        "param {} not found in {}\n or\n {}.".format(
            sourcename,
            yaml.main.round_trip_dump(cwl.save(process)),
            yaml.main.round_trip_dump(cwl.save(parent)),
        )
    )

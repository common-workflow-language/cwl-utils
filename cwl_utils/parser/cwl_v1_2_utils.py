import hashlib
from typing import cast

from schema_salad.exceptions import ValidationException
from schema_salad.utils import json_dumps

from cwl_utils.parser.cwl_v1_2 import CommandLineTool, CommandOutputBinding


def convert_stdstreams_to_files(clt: CommandLineTool) -> None:
    for out in clt.outputs:
        if out.type == 'stdout':
            if out.outputBinding is not None:
                raise ValidationException(
                    "Not allowed to specify outputBinding when using stdout shortcut.")
            if clt.stdout is None:
                clt.stdout = str(hashlib.sha1(json_dumps(  # nosec
                    clt.save(), sort_keys=True).encode('utf-8')).hexdigest())
            out.type = 'File'
            out.outputBinding = CommandOutputBinding(glob=clt.stdout)
        elif out.type == 'stderr':
            if out.outputBinding is not None:
                raise ValidationException(
                    "Not allowed to specify outputBinding when using stderr shortcut.")
            if clt.stderr is None:
                clt.stderr = str(hashlib.sha1(json_dumps(  # nosec
                    clt.save(), sort_keys=True).encode('utf-8')).hexdigest())
            out.type = 'File'
            out.outputBinding = CommandOutputBinding(glob=clt.stderr)
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

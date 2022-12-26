"""CWL parser utility functions."""

from typing import Any, List, Optional, Union, cast

from schema_salad.exceptions import ValidationException

from . import (
    Process,
    Workflow,
    cwl_v1_0,
    cwl_v1_0_utils,
    cwl_v1_1,
    cwl_v1_1_utils,
    cwl_v1_2,
    cwl_v1_2_utils,
)


def convert_stdstreams_to_files(process: Process) -> None:
    """Convert stdin, stdout and stderr type shortcuts to files."""
    if isinstance(process, cwl_v1_0.CommandLineTool):
        cwl_v1_0_utils.convert_stdstreams_to_files(process)
    elif isinstance(process, cwl_v1_1.CommandLineTool):
        cwl_v1_1_utils.convert_stdstreams_to_files(process)
    elif isinstance(process, cwl_v1_2.CommandLineTool):
        cwl_v1_2_utils.convert_stdstreams_to_files(process)


def type_for_source(
    process: Process,
    sourcenames: Union[str, List[str]],
    parent: Optional[Workflow] = None,
    linkMerge: Optional[str] = None,
    pickValue: Optional[str] = None,
) -> Any:
    """Determine the type for the given sourcenames."""
    if process.cwlVersion == "v1.0":
        cwl_v1_0_utils.type_for_source(
            cast(
                Union[
                    cwl_v1_0.CommandLineTool,
                    cwl_v1_0.Workflow,
                    cwl_v1_0.ExpressionTool,
                ],
                process,
            ),
            sourcenames,
            cast(Optional[cwl_v1_0.Workflow], parent),
            linkMerge,
        )
    elif process.cwlVersion == "v1.1":
        cwl_v1_1_utils.type_for_source(
            cast(
                Union[
                    cwl_v1_1.CommandLineTool,
                    cwl_v1_1.Workflow,
                    cwl_v1_1.ExpressionTool,
                ],
                process,
            ),
            sourcenames,
            cast(Optional[cwl_v1_1.Workflow], parent),
            linkMerge,
        )
    elif process.cwlVersion == "v1.2":
        cwl_v1_2_utils.type_for_source(
            cast(
                Union[
                    cwl_v1_2.CommandLineTool,
                    cwl_v1_2.Workflow,
                    cwl_v1_2.ExpressionTool,
                ],
                process,
            ),
            sourcenames,
            cast(Optional[cwl_v1_2.Workflow], parent),
            linkMerge,
            pickValue,
        )
    elif process.cwlVersion is None:
        raise ValidationException("could not get the cwlVersion")
    else:
        raise ValidationException(
            f"Version error. Did not recognise {process.cwlVersion} as a CWL version"
        )

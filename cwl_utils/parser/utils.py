"""CWL parser utility functions."""

from typing import Union

import cwl_utils.parser
import cwl_utils.parser.cwl_v1_0
import cwl_utils.parser.cwl_v1_0_utils
import cwl_utils.parser.cwl_v1_1
import cwl_utils.parser.cwl_v1_1_utils
import cwl_utils.parser.cwl_v1_2
import cwl_utils.parser.cwl_v1_2_utils


def convert_stdstreams_to_files(
    process: Union[
        cwl_utils.parser.Workflow,
        cwl_utils.parser.CommandLineTool,
        cwl_utils.parser.ExpressionTool,
    ]
) -> None:
    """Convert stdin, stdout and stderr type shortcuts to files."""
    if isinstance(process, cwl_utils.parser.cwl_v1_0.CommandLineTool):
        cwl_utils.parser.cwl_v1_0_utils.convert_stdstreams_to_files(process)
    elif isinstance(process, cwl_utils.parser.cwl_v1_1.CommandLineTool):
        cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(process)
    elif isinstance(process, cwl_utils.parser.cwl_v1_2.CommandLineTool):
        cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(process)

#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from ruamel import yaml

from cwl_utils.parser import cwl_v1_2 as cwl


def main() -> None:
    """Generate a CWL object to match "cat-tool.cwl"."""
    inputs = [cwl.CommandInputParameter(id="file1", type="File")]
    outputs = [
        cwl.CommandOutputParameter(
            id="output",
            type="File",
            outputBinding=cwl.CommandOutputBinding(glob="output"),
        )
    ]
    cat_tool = cwl.CommandLineTool(
        inputs=inputs,
        outputs=outputs,
        cwlVersion="v1.2",
        baseCommand="cat",
        stdin="$(inputs.file1.path)",
        stdout="output",
    )
    print(yaml.main.round_trip_dump(cat_tool.save()))


if __name__ == "__main__":
    main()

# SPDX-License-Identifier: Apache-2.0
"""Tests of example Python scripts."""
import os
import runpy
from importlib.resources import as_file, files
from pathlib import Path


def test_load_example() -> None:
    """Test the load_cwl_by_path.py script."""
    cwd = Path.cwd()
    target = files("cwl_utils").joinpath("tests/load_cwl_by_path.py")
    with as_file(target) as target_path:
        os.chdir(target_path.parent)
        result_raw = runpy.run_path(str(target_path))
        os.chdir(cwd)
    result = result_raw["saved_obj"]
    assert result["class"] == "Workflow"

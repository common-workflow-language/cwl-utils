# SPDX-License-Identifier: Apache-2.0
"""Tests of example Python scripts."""
import os
from pathlib import Path


def test_load_example() -> None:
    """Test the load_cwl_by_path.py script."""
    cwd = Path.cwd()
    parent = Path(__file__).resolve().parent
    os.chdir(parent.parent)
    exec(
        open(parent / "load_cwl_by_path.py").read(),
        globals(),
        locals(),
    )
    os.chdir(cwd)
    result = locals()["saved_obj"]
    assert result["class"] == "Workflow"

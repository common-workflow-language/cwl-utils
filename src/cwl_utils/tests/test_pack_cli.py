# SPDX-License-Identifier: Apache-2.0
"""Test the cwl-pack console script."""

import json
from pathlib import Path

import pytest

from cwl_utils.pack_cli import arg_parser, run

from .util import get_data


def test_pack_cli_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    """Packing to stdout produces the inlined CWL JSON document."""
    input_path = get_data("testdata/remote-cwl/wf1.cwl")
    args = arg_parser().parse_args([input_path])
    assert run(args) == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["class"] == "Workflow"
    assert parsed["cwlVersion"] == "v1.2"
    assert parsed["steps"][0]["run"]["class"] == "CommandLineTool"


def test_pack_cli_outfile(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``--outfile`` writes the packed JSON to disk."""
    input_path = get_data("testdata/remote-cwl/wf1.cwl")
    outfile = tmp_path / "packed.json"
    args = arg_parser().parse_args([input_path, "--outfile", str(outfile)])
    assert run(args) == 0
    captured = capsys.readouterr()
    parsed = json.loads(outfile.read_text(encoding="utf-8"))
    assert captured.out == ""
    assert parsed["class"] == "Workflow"
    assert parsed["cwlVersion"] == "v1.2"
    assert parsed["steps"][0]["run"]["class"] == "CommandLineTool"

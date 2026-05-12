# SPDX-License-Identifier: Apache-2.0
"""Test the cwl-normalizer console script."""

import json
from pathlib import Path

import pytest

from cwl_utils.normalizer import parse_args, run

from .util import get_data


def test_normalizer_v1_1(tmp_path: Path) -> None:
    """Normalize a v1.1 CWL document end-to-end."""
    input_path = get_data("testdata/count-lines6-single-source-wf_v1_1.cwl")
    args = parse_args([str(tmp_path), input_path])
    assert run(args) == 0
    assert (tmp_path / "count-lines6-single-source-wf_v1_1.cwl").is_file()


def test_normalizer_v1_2(tmp_path: Path) -> None:
    """Normalize a v1.2 CWL document end-to-end (no upgrade needed)."""
    input_path = get_data("testdata/count-lines6-single-source-wf_v1_2.cwl")
    args = parse_args([str(tmp_path), input_path])
    assert run(args) == 0
    output_path = tmp_path / "count-lines6-single-source-wf_v1_2.cwl"
    assert output_path.is_file()
    assert json.loads(output_path.read_text(encoding="utf-8"))["cwlVersion"] == "v1.2"


def test_normalizer_unsupported_version(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Unsupported cwlVersion returns non-zero and logs a readable error (no TypeError)."""
    import logging

    bogus = tmp_path / "bogus.cwl"
    bogus.write_text(
        "cwlVersion: v9.9\n"
        "class: CommandLineTool\n"
        "baseCommand: [echo]\n"
        "inputs: []\n"
        "outputs: []\n"
    )
    args = parse_args([str(tmp_path / "out"), str(bogus)])
    (tmp_path / "out").mkdir()
    with caplog.at_level(logging.ERROR, logger="cwl-normalizer"):
        assert run(args) == -1
    assert any("v9.9" in r.getMessage() for r in caplog.records)

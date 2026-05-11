# SPDX-License-Identifier: Apache-2.0
"""Test the cwl-normalizer console script."""

from pathlib import Path

from cwl_utils.normalizer import parse_args, run

from .util import get_data


def test_normalizer_v1_1(tmp_path: Path) -> None:
    """Normalize a v1.1 CWL document end-to-end."""
    input_path = get_data("testdata/count-lines6-single-source-wf_v1_1.cwl")
    args = parse_args([str(tmp_path), input_path])
    assert run(args) == 0
    assert (tmp_path / "count-lines6-single-source-wf_v1_1.cwl").is_file()

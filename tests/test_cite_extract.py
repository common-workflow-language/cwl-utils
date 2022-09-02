# SPDX-License-Identifier: Apache-2.0
"""Tests for cwl-cite-extract."""
from pathlib import Path

import cwl_utils.parser.cwl_v1_0 as parser
from cwl_utils.cite_extract import traverse_workflow

HERE = Path(__file__).resolve().parent
TEST_CWL = HERE / "../testdata/md5sum.cwl"


def test_traverse_workflow() -> None:
    """Test the citation extraction, simply."""
    loaded = parser.load_document(str(TEST_CWL.resolve()))
    traverse_workflow(loaded)

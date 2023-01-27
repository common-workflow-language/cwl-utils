# SPDX-License-Identifier: Apache-2.0
"""Tests for cwl-cite-extract."""
import cwl_utils.parser.cwl_v1_0 as parser
from cwl_utils.cite_extract import traverse_workflow

from .util import get_data


def test_traverse_workflow() -> None:
    """Test the citation extraction, simply."""
    loaded = parser.load_document(get_data("testdata/md5sum.cwl"))
    traverse_workflow(loaded)

# SPDX-License-Identifier: Apache-2.0
"""Test the CWL $graph document splitter tool."""
from io import StringIO
from pathlib import Path

import requests

from cwl_utils.graph_split import graph_split

from .util import get_data

URI = (
    "https://gist.githubusercontent.com/altairwei/"
    "6a0097db95cad23de36f825ed3b9f4b0/raw/"
    "83f332931c3093ee73554cd7f60054ce17d03239/rhapsody_wta_1.8.packed.cwl"
)


def test_graph_split(tmp_path: Path) -> None:
    """Confirm that a user provided example produces no exception."""
    sourceIO = StringIO(requests.get(URI).text)
    sourceIO.name = URI
    graph_split(sourceIO, tmp_path, "yaml", "main.cwl", True)


def test_graph_split_offline(tmp_path: Path) -> None:
    """Confirm that a local provided example produces no exception."""
    with open(get_data("testdata/js-expr-req-wf.cwl")) as handle:
        graph_split(handle, tmp_path, "yaml", "main.cwl", True)

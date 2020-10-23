import os
from pathlib import Path
from unittest import TestCase

import requests

from cwl_utils.graph_split import run

URI = "https://gist.githubusercontent.com/altairwei/6a0097db95cad23de36f825ed3b9f4b0/raw/83f332931c3093ee73554cd7f60054ce17d03239/rhapsody_wta_1.8.packed.cwl"


def test_graph_split(tmp_path: Path):
    os.chdir(tmp_path)
    run(requests.get(URI).text, URI)

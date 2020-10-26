from pathlib import Path
from unittest import TestCase

import cwl_utils.parser_v1_0 as parser
from cwl_utils.cite_extract import traverse_workflow

HERE = Path(__file__).resolve().parent
TEST_CWL = HERE / "../testdata/md5sum.cwl"


class TestCiteExtract(TestCase):
    def test_traverse_workflow(self):
        loaded = parser.load_document(str(TEST_CWL.resolve()))
        traverse_workflow(loaded)

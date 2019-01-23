from unittest import TestCase
from pathlib import Path
from cwl_utils.cite_extract import traverse_workflow
import cwl_utils.parser_v1_0 as parser

HERE = Path(__file__).resolve().parent
TEST_CWL = HERE / "../testdata/md5sum.cwl"


class TestCiteExtract(TestCase):
    def test_traverse_workflow(self):
        loaded = parser.load_document(str(TEST_CWL.resolve()))
        traverse_workflow(loaded)

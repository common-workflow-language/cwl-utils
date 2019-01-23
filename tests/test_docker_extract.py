from unittest import TestCase
from pathlib import Path
from tempfile import TemporaryDirectory
from cwl_utils.docker_extract import traverse, get_image_name, save_docker_image, load_docker_image
import cwl_utils.parser_v1_0 as parser

HERE = Path(__file__).resolve().parent
TEST_CWL = HERE / "../testdata/md5sum.cwl"


class TestDockerExtract(TestCase):
    def test_traverse_workflow(self):
        loaded = parser.load_document(str(TEST_CWL.resolve()))

        with TemporaryDirectory() as tmpdir:
            for req in set(traverse(loaded)):
                image_name = get_image_name(req)
                save_docker_image(req, image_name, tmpdir)
                _ = load_docker_image(image_name)

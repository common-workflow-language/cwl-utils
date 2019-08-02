from unittest import TestCase, skipIf
from pathlib import Path
from os import environ
from tempfile import TemporaryDirectory
from cwl_utils.docker_extract import traverse
from cwl_utils.image_puller import DockerImagePuller, SingularityImagePuller
import cwl_utils.parser_v1_0 as parser

HERE = Path(__file__).resolve().parent
TEST_CWL = HERE / "../testdata/md5sum.cwl"
TRAVIS = environ.get('TRAVIS', 'false') == 'true'


class TestDockerExtract(TestCase):
    @skipIf(TRAVIS, reason="travis cannot run docker in docker")
    def test_traverse_workflow(self):
        loaded = parser.load_document(str(TEST_CWL.resolve()))

        with TemporaryDirectory() as tmpdir:
            for req in set(traverse(loaded)):
                image_puller = DockerImagePuller(req, tmpdir)
                image_puller.save_docker_image()
                _ = image_puller.generate_udocker_loading_command()

    @skipIf(TRAVIS, reason="travis cannot run singularity in docker")
    def test_traverse_workflow_singularity(self):
        loaded = parser.load_document(str(TEST_CWL.resolve()))

        with TemporaryDirectory() as tmpdir:
            for req in set(traverse(loaded)):
                image_puller = SingularityImagePuller(req, tmpdir)
                image_puller.save_docker_image()

from os import environ
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipIf

import pytest
import cwl_utils.parser_v1_0 as parser
from cwl_utils.docker_extract import traverse
from cwl_utils.image_puller import DockerImagePuller, SingularityImagePuller

HERE = Path(__file__).resolve().parent
TEST_CWL = HERE / "../testdata/md5sum.cwl"
TRAVIS = environ.get("TRAVIS", "false") == "true"


@pytest.mark.skipif(TRAVIS, reason="travis cannot run docker in docker")
def test_traverse_workflow() -> None:
    """Test container extraction tool using Docker."""
    loaded = parser.load_document(str(TEST_CWL.resolve()))

    with TemporaryDirectory() as tmpdir:
        for req in set(traverse(loaded)):
            image_puller = DockerImagePuller(req.dockerPull, tmpdir)
            image_puller.save_docker_image()
            _ = image_puller.generate_udocker_loading_command()

@pytest.mark.skipif(TRAVIS, reason="travis cannot run singularity in docker")
def test_traverse_workflow_singularity() -> None:
    """Test container extraction tool using Singularity."""
    loaded = parser.load_document(str(TEST_CWL.resolve()))

    with TemporaryDirectory() as tmpdir:
        for req in set(traverse(loaded)):
            image_puller = SingularityImagePuller(req.dockerPull, tmpdir)
            image_puller.save_docker_image()

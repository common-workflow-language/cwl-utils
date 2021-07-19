from pathlib import Path

import cwl_utils.parser_v1_0 as parser
from cwl_utils.cwl_v1_0_container_extract import traverse
from cwl_utils.image_puller import DockerImagePuller, SingularityImagePuller

HERE = Path(__file__).resolve().parent
TEST_CWL = HERE / "../testdata/md5sum.cwl"


def test_traverse_workflow(tmp_path: Path) -> None:
    """Test container extraction tool using Docker."""
    loaded = parser.load_document(str(TEST_CWL.resolve()))

    for req in set(traverse(loaded)):
        image_puller = DockerImagePuller(req.dockerPull, tmp_path)
        image_puller.save_docker_image()
        _ = image_puller.generate_udocker_loading_command()


def test_traverse_workflow_singularity(tmp_path: Path) -> None:
    """Test container extraction tool using Singularity."""
    loaded = parser.load_document(str(TEST_CWL.resolve()))

    for req in set(traverse(loaded)):
        image_puller = SingularityImagePuller(req.dockerPull, tmp_path)
        image_puller.save_docker_image()

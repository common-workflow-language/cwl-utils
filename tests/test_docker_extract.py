# SPDX-License-Identifier: Apache-2.0
"""Tests for cwl-docker-extract."""
from shutil import which
from tempfile import TemporaryDirectory

from pytest import mark

import cwl_utils.parser.cwl_v1_0 as parser
from cwl_utils.docker_extract import traverse
from cwl_utils.image_puller import DockerImagePuller, SingularityImagePuller

from .util import get_data

TEST_CWL = get_data("testdata/md5sum.cwl")


@mark.skipif(which("docker") is None, reason="docker is not available")
def test_traverse_workflow() -> None:
    """Test container extraction tool using Docker."""
    loaded = parser.load_document(TEST_CWL)

    with TemporaryDirectory() as tmpdir:
        reqs = set(traverse(loaded))
        assert len(reqs) == 1
        for req in reqs:
            assert req.dockerPull
            image_puller = DockerImagePuller(req.dockerPull, tmpdir)
            image_puller.save_docker_image()
            _ = image_puller.generate_udocker_loading_command()


@mark.skipif(which("singularity") is None, reason="singularity is not available")
def test_traverse_workflow_singularity() -> None:
    """Test container extraction tool using Singularity."""
    loaded = parser.load_document(TEST_CWL)

    with TemporaryDirectory() as tmpdir:
        reqs = set(traverse(loaded))
        assert len(reqs) == 1
        for req in reqs:
            assert req.dockerPull
            image_puller = SingularityImagePuller(req.dockerPull, tmpdir)
            image_puller.save_docker_image()

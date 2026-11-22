import atexit
import os
import shutil
from contextlib import ExitStack
from importlib.resources import as_file, files
from pathlib import Path

import pytest


def get_path(filename: str) -> Path:
    """Get the filepath for a given test file."""
    # normalizing path depending on OS or else it will cause problem when joining path
    filename = os.path.normpath(filename)
    file_manager = ExitStack()
    atexit.register(file_manager.close)
    traversable = files("cwl_utils") / filename
    filepath = file_manager.enter_context(as_file(traversable))
    return filepath.resolve()


def get_data(filename: str) -> str:
    return str(get_path(filename))


SKIP_DOCKER = bool(os.environ.get("SKIP_DOCKER_TESTS")) or not bool(
    shutil.which("docker")
)

needs_docker = pytest.mark.skipif(
    SKIP_DOCKER,
    reason="Requires the docker executable on the system path.",
)

SKIP_SINGULARITY = bool(os.environ.get("SKIP_SINGULARITY_TESTS")) or not bool(
    shutil.which("singularity")
)

needs_singularity = pytest.mark.skipif(
    SKIP_SINGULARITY,
    reason="Requires the singularity executable on the system path.",
)

SKIP_PODMAN = bool(os.environ.get("SKIP_PODMAN_TESTS")) or not bool(
    shutil.which("podman")
)

needs_podman = pytest.mark.skipif(
    SKIP_PODMAN,
    reason="Requires the podman executable on the system path.",
)

SKIP_UDOCKER = bool(os.environ.get("SKIP_UDOCKER_TESTS")) or not bool(
    shutil.which("udocker")
)

needs_udocker = pytest.mark.skipif(
    SKIP_UDOCKER,
    reason="Requires the udocker executable on the system path.",
)

needs_node = pytest.mark.skipif(
    not bool(shutil.which("qjs")),
    reason="Requires node{,js} on the system path.",
)

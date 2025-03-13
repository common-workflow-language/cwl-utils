import os
import shutil
from pathlib import Path

import pytest
from pkg_resources import Requirement, ResolutionError, resource_filename


def get_path(filename: str) -> Path:
    # normalizing path depending on OS or else it will cause problem when joining path
    filename = os.path.normpath(filename)
    filepath = None
    try:
        filepath = resource_filename(Requirement.parse("cwl-utils"), filename)
    except ResolutionError:
        pass
    if not filepath or not os.path.isfile(filepath):
        filepath = os.path.join(os.path.dirname(__file__), os.pardir, filename)
    return Path(filepath).resolve()


def get_data(filename: str) -> str:
    return str(get_path(filename))


needs_docker = pytest.mark.skipif(
    not bool(shutil.which("docker")),
    reason="Requires the docker executable on the system path.",
)

needs_singularity = pytest.mark.skipif(
    not bool(shutil.which("singularity")),
    reason="Requires the singularity executable on the system path.",
)

needs_podman = pytest.mark.skipif(
    not bool(shutil.which("podman")),
    reason="Requires the podman executable on the system path.",
)

needs_udocker = pytest.mark.skipif(
    not bool(shutil.which("udocker")),
    reason="Requires the udocker executable on the system path.",
)

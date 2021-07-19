# SPDX-License-Identifier: GPL-3.0-only
"""Classes for docker-extract."""
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


class ImagePuller(ABC):
    def __init__(self, req: str, save_directory: Path) -> None:
        """Create an ImagePuller."""
        self.req = req
        self.save_directory = save_directory

    @abstractmethod
    def get_image_name(self) -> str:
        """Get the engine-specific image name."""

    @abstractmethod
    def save_docker_image(
        self, skip_existing: bool = False, force_pull: bool = False
    ) -> None:
        """Download and save the image to disk."""

    @staticmethod
    def _run_command_pull(cmd_pull: List[str]) -> None:
        try:
            subprocess.run(
                cmd_pull, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as err:
            if err.output:
                raise subprocess.SubprocessError(err.output)
            raise err


class DockerImagePuller(ImagePuller):
    """
    Pull docker image with Docker
    """

    def get_image_name(self) -> str:
        """Get the name of the tarball."""
        return "".join(self.req.split("/")) + ".tar"

    def generate_udocker_loading_command(self) -> str:
        """Generate the udocker loading command."""
        return f"udocker load -i {self.get_image_name()}"

    def _image_exists(self) -> bool:
        return (
            subprocess.run(["docker", "inspect", "--type=image", self.req]).returncode
            == 0
        )

    def _pull_image(self) -> None:
        cmd_pull = ["docker", "pull", self.req]
        ImagePuller._run_command_pull(cmd_pull)

    def save_docker_image(
        self, skip_existing: bool = False, force_pull: bool = False
    ) -> None:
        """Download and save the software container image to disk as a docker tarball."""
        _LOGGER.info(f"Pulling {self.req} with Docker...")
        image_path = self.save_directory / self.get_image_name()
        if image_path.exists() and not skip_existing:
            _LOGGER.info(
                f"Local image already exists, but skip_existing=False: {image_path}"
            )
            return
        if self._image_exists():
            if force_pull:
                self._pull_image()
            else:
                _LOGGER.info(
                    f"The software container image {self.req} is "
                    "already downloaded, and force_pull=False, so not "
                    "pulling again."
                )
        else:
            self._pull_image()
        cmd_save = [
            "docker",
            "save",
            "-o",
            str(image_path),
            self.req,
        ]
        subprocess.run(cmd_save, check=True)
        _LOGGER.info(f"Image successfully pulled: {image_path}")
        print(self.generate_udocker_loading_command())


class SingularityImagePuller(ImagePuller):
    """
    Pull docker image with Singularity
    """

    CHARS_TO_REPLACE = ["/"]
    NEW_CHAR = "_"

    def __init__(self, req: str, save_directory: Path) -> None:
        """Create a Singularity-based software container image downloader."""
        super(SingularityImagePuller, self).__init__(req, save_directory)
        version = subprocess.check_output(
            ["singularity", "--version"], universal_newlines=True
        )
        if version.startswith("singularity version "):
            version = version[20:]
        self.version = version

    def _is_version_2_6(self) -> bool:
        return self.version.startswith("2.6")

    def _is_version_3_or_newer(self) -> bool:
        return int(self.version[0]) >= 3

    def get_image_name(self) -> str:
        """Determine the file name appropriate to the installed version of Singularity."""
        image_name = self.req
        for char in self.CHARS_TO_REPLACE:
            image_name = image_name.replace(char, self.NEW_CHAR)
        if self._is_version_2_6():
            suffix = ".img"
        elif self._is_version_3_or_newer():
            suffix = ".sif"
        else:
            raise Exception(
                "Don't know how to handle this version of singularity: {}.".format(
                    self.version
                )
            )
        return f"{image_name}{suffix}"

    def save_docker_image(
        self, skip_existing: bool = False, force_pull: bool = False
    ) -> None:
        """Pull down the Docker format software container image and save it in the Singularity image format."""
        _LOGGER.info(f"Pulling {self.req} with Singularity...")
        image_path = self.save_directory / self.get_image_name()
        if image_path.exists and skip_existing:
            _LOGGER.info(
                f"Local image already exists, and skip_existing=True: {image_path}"
            )
            return
        cmd_pull = ["singularity", "pull", "--name", str(image_path)]
        if force_pull or not skip_existing:
            cmd_pull.append("--force")
        cmd_pull.append(f"docker://{self.req}")
        ImagePuller._run_command_pull(cmd_pull)
        _LOGGER.info(f"Image successfully pulled: {image_path}")

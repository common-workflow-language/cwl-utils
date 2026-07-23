# SPDX-License-Identifier: Apache-2.0
"""Classes for docker-extract."""

import logging
import subprocess  # nosec
from abc import ABC, abstractmethod
from pathlib import Path

from .singularity import get_version as get_singularity_version
from .singularity import is_version_2_6 as is_singularity_version_2_6
from .singularity import is_version_3_or_newer as is_singularity_version_3_or_newer

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


class ImagePuller(ABC):
    def __init__(
        self,
        req: str,
        save_directory: str | Path | None,
        cmd: str,
        force_pull: bool,
    ) -> None:
        """
        Create an ImagePuller.

        req already contains any tag that will be used.
        """
        self.req = req
        self.save_directory = save_directory
        self.cmd = cmd
        self.force_pull = force_pull

    @abstractmethod
    def get_image_name(self) -> str:
        """Get the engine-specific image name."""

    @abstractmethod
    def save_docker_image(self) -> None:
        """Download and save the image to disk."""

    @staticmethod
    def _run_command_pull(cmd_pull: list[str]) -> None:
        try:
            subprocess.run(  # nosec
                cmd_pull, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as err:
            if err.output:
                raise subprocess.SubprocessError(err.output) from err
            raise err


class DockerImagePuller(ImagePuller):
    """Pull docker image with Docker."""

    def get_image_name(self) -> str:
        """Get the name of the tarball."""
        # Replace colons with underscores in the name.
        # See https://github.com/containers/podman/issues/489
        return ("".join(self.req.split("/")) + ".tar").replace(":", "_")

    def generate_udocker_loading_command(self) -> str:
        """Generate the udocker loading command."""
        return f"udocker load -i {self.get_image_name()}"

    def save_docker_image(self) -> None:
        """Download and save the software container image to disk as a docker tarball."""
        _LOGGER.info(f"Pulling {self.req} with {self.cmd}...")
        cmd_pull = [self.cmd, "pull", self.req]
        ImagePuller._run_command_pull(cmd_pull)
        _LOGGER.info(f"Image successfully pulled: {self.req}")
        if self.save_directory:
            dest = Path(self.save_directory, self.get_image_name())
            if self.save_directory and self.force_pull:
                dest.unlink()
            cmd_save = [
                self.cmd,
                "save",
                "-o",
                str(dest),
                self.req,
            ]
            subprocess.run(cmd_save, check=True)  # nosec
            _LOGGER.info(f"Image successfully saved: {dest!r}.")
            print(self.generate_udocker_loading_command())


class SingularityImagePuller(ImagePuller):
    """Pull docker image with Singularity."""

    CHARS_TO_REPLACE = ["_", "/"]
    NEW_STRINGS = ["___", "_s_"]
    # This ends up being a directory name that often gets dropped into the user's current directory
    FILENAME_SCHEME_VERSION = "v2"
    
    def _image_to_filename(
        self,
        image_name: str,
        to_replace: list[str],
        replacements: list[str],
        version: str | None = None
    ) -> str:
        """
        Get the filename for an image, using the given replacements to escape it.

        The filename will be appropriate for the current Singularity.

        The filename will include a disambiguating version if version is set.
        No filenames from two different versions, or with and without a
        version, will be equal. 

        The filename may contain leading directory components.
        """
        for char, replacement in zip(self.CHARS_TO_REPLACE, self.NEW_STRINGS):
            image_name = image_name.replace(char, replacement)
        if is_singularity_version_2_6():
            suffix = ".img"
        elif is_singularity_version_3_or_newer():
            suffix = ".sif"
        else:
            raise Exception(
                f"Don't know how to handle this version of singularity: {get_singularity_version()}."
            )
        filename = f"{image_name}{suffix}"
        if version is not None:
            filename = os.path.join(version, filename)
        return filename

    def get_image_name(self) -> str:
        """Determine the file name appropriate to the installed version of Singularity."""
        image_name = self.req
        return self._image_to_filename(image_name, CHARS_TO_REPLACE, NEW_STRINGS, FILENAME_SCHEME_VERSION)

    def get_alternate_image_names(self) -> list[str]:
        """
        Determine filenames used by previous versions of cwltool or cwl-utils.

        These should be checked for the image and used if it exists there,
        instead of pulling it again.

        These cover cwltool 3.2.20260720092025 and cwl-utils 0.42.
        """
        image_name = self.req
        return [
            # Check the path cwl-utils 0.42 uses, with underscores for slashes
            # and colons.
            self._image_to_filename(image_name, ["/", ":"], ["_", "_"]),
            # Check the path cwltool 3.2.20260720092025 uses, with _latest
            # potentially appended and then only slashes replaced.
            self._image_to_filename(
                image_name + "_latest" if ":" not in image_name else image_name,
                ["/"],
                ["_"],
            ),
        ]

    def save_docker_image(self) -> None:
        """Pull down the Docker software container image and save it in the Singularity image format."""
        save_directory: str | Path
        if self.save_directory:
            save_directory = self.save_directory
        target = Path(save_directory, self.get_image_name())
        if not self.force_pull:
            if target.exists():
                _LOGGER.info(f"Already cached {self.req} with Singularity.")
                return
            # Otherwise check other paths old versions may have placed it at.
            alternate_targets = [Path(save_directory, img) for img in self.get_alternate_image_names()]
            for alt_target in alternate_targets:
                if alt_target.exists():
                    _LOGGER.info(f"Already cached {self.req} with Singularity using a previous caching scheme.")
                    return
        
        _LOGGER.info(f"Pulling {self.req} with Singularity...")
        os.makedirs(target.parent, exist_ok=True)
        cmd_pull = [
            self.cmd,
            "pull",
        ]
        if self.force_pull:
            cmd_pull.append("--force")
        cmd_pull.extend(
            [
                "--name",
                str(target),
                f"docker://{self.req}",
            ]
        )
        ImagePuller._run_command_pull(cmd_pull)
        _LOGGER.info(
            f"Image successfully pulled: {save_directory}/{self.get_image_name()}"
        )

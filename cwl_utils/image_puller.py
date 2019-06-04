from abc import ABC, abstractmethod
import logging
import os
import subprocess

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


class ImagePuller(ABC):

    def __init__(self, req, save_directory):
        self.req = req
        self.save_directory = save_directory

    @abstractmethod
    def get_image_name(self):
        pass

    @abstractmethod
    def save_docker_image(self):
        pass

    @staticmethod
    def _run_command_pull(cmd_pull):
        try:
            subprocess.run(cmd_pull, check=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as err:
            if err.output:
                raise subprocess.SubprocessError(err.output)
            raise err


class DockerImagePuller(ImagePuller):
    """
    Pull docker image with Docker
    """

    def get_image_name(self):
        return ''.join(self.req.split('/')) + '.tar'

    def generate_udocker_loading_command(self):
        return f'udocker load -i {self.get_image_name()}'

    def save_docker_image(self):
        _LOGGER.info(f"Pulling {self.req} with Docker...")
        cmd_pull = ['docker', 'pull', self.req]
        ImagePuller._run_command_pull(cmd_pull)
        cmd_save = ['docker', 'save', '-o', os.path.join(self.save_directory,
                                                         self.get_image_name()),
                    self.req]
        subprocess.run(cmd_save, check=True)
        _LOGGER.info(f"Image successfully pulled: {self.save_directory}/{self.get_image_name()}")
        print(self.generate_udocker_loading_command())


class SingularityImagePuller(ImagePuller):
    """
    Pull docker image with Singularity
    """
    CHARS_TO_REPLACE = ['/', ':']
    NEW_CHAR = '-'

    def get_image_name(self):
        image_name = self.req
        for char in self.CHARS_TO_REPLACE:
            image_name = image_name.replace(char, self.NEW_CHAR)
        return f'{image_name}.img'

    def save_docker_image(self):
        _LOGGER.info(f"Pulling {self.req} with Singularity...")
        cmd_pull = ['singularity', 'pull', os.path.join(self.save_directory,
                                                        self.get_image_name()),
                    f'docker:{self.req}']
        ImagePuller._run_command_pull(cmd_pull)
        _LOGGER.info(f"Image successfully pulled: {self.save_directory}/{self.get_image_name()}")

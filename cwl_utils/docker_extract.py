#!/usr/bin/env python3
from abc import ABC, abstractmethod
import argparse
import logging
import os
import subprocess
import sys

import cwl_utils.parser_v1_0 as cwl

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


def parse_args():
    parser = argparse.ArgumentParser(
        description='Tool to save docker images from a cwl workflow.')
    parser.add_argument('dir', help='Directory in which to save images')
    parser.add_argument('input', help='Input CWL workflow')
    parser.add_argument('-s', '--singularity', help='Use singularity to pull the image', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.dir, exist_ok=True)

    top = cwl.load_document(args.input)

    for req in set(traverse(top)):
        if args.singularity:
            image_puller = SingularityImagePuller(req, args.dir)
            # image_name = get_image_name_singularity(req)
            # save_docker_image_singularity(req, image_name, args.dir)
        else:
            image_puller = DockerImagePuller(req, args.dir)
            # image_name = get_image_name(req)
            # save_docker_image(req, image_name, args.dir)
            # print(load_docker_image(image_name))
        image_puller.save_docker_image()


# def get_image_name(req):
#     return ''.join(req.split('/')) + '.tar'
#
#
# def get_image_name_singularity(req):
#     CHARS_TO_REPLACE = ['/', ':']
#     NEW_CHAR = '-'
#     image_name = req
#     for char in CHARS_TO_REPLACE:
#         image_name = image_name.replace(char, NEW_CHAR)
#     return f'{image_name}.img'
#
#
# def load_docker_image(image_name):
#     return f'udocker load -i {image_name}'


# def _run_command_pull(cmd_pull):
#     try:
#         subprocess.run(cmd_pull, check=True, stdout=subprocess.PIPE,
#                        stderr=subprocess.STDOUT)
#     except subprocess.CalledProcessError as err:
#         if err.output:
#             raise subprocess.SubprocessError(err.output)
#         raise err


# def save_docker_image(req, image_name, image_dir):
#     cmd_pull = ['docker', 'pull', req]
#     _run_command_pull(cmd_pull)
#     cmd_save = ['docker', 'save', '-o', os.path.join(image_dir, image_name),
#                 req]
#     subprocess.run(cmd_save, check=True)
#
#
# def save_docker_image_singularity(req, image_name, image_dir):
#     cmd_pull = ['singularity', 'pull', os.path.join(image_dir, image_name), f'docker:{req}']
#     _run_command_pull(cmd_pull)


def extract_docker_requirements(process: cwl.Process):
    for req in extract_docker_reqs(process):
        if ':' not in req.dockerPull:
            req.dockerPull += ':latest'
        yield req.dockerPull


def extract_docker_reqs(process: cwl.Process):
    if process.requirements:
        for req in process.requirements:
            if isinstance(req, cwl.DockerRequirement):
                yield req
    if process.hints:
        for req in process.hints:
            if req['class'] == "DockerRequirement":
                yield cwl.load_field(req, cwl.DockerRequirementLoader,
                                     process.id, process.loadingOptions)


def traverse(process: cwl.Process):
    yield from extract_docker_requirements(process)
    if isinstance(process, cwl.Workflow):
        yield from traverse_workflow(process)


def get_process_from_step(step: cwl.WorkflowStep):
    if isinstance(step.run, str):
        return cwl.load_document(step.run)
    return step.run


def traverse_workflow(workflow: cwl.Workflow):
    for step in workflow.steps:
        for req in extract_docker_reqs(step):
            yield req
        yield from traverse(get_process_from_step(step))


if __name__ == "__main__":
    sys.exit(main())

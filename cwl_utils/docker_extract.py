#!/usr/bin/env python3
import sys
import os
import cwl_utils.parser_v1_0 as cwl
import subprocess
import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description='Tool to save docker images from a cwl workflow \n '
                    'and generate udocker loading commands.')
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
            image_name = get_image_name_singularity(req)
            save_docker_image_singularity(req, image_name, args.dir)
        else:
            image_name = get_image_name(req)
            save_docker_image(req, image_name, args.dir)
            print(load_docker_image(image_name))


def get_image_name(req):
    return ''.join(req.split('/')) + '.tar'


def get_image_name_singularity(req):
    CHARS_TO_REPLACE = ['/', ':']
    NEW_CHAR = '-'
    image_name = req
    for char in CHARS_TO_REPLACE:
        image_name = image_name.replace(char, NEW_CHAR)
    return f'{image_name}.img'


def load_docker_image(image_name):
    return f'udocker load -i {image_name}'


def _run_command_pull(cmd_pull):
    try:
        subprocess.run(cmd_pull, check=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as err:
        if err.output:
            raise subprocess.SubprocessError(err.output)
        raise err


def save_docker_image(req, image_name, image_dir):
    cmd_pull = ['docker', 'pull', req]
    _run_command_pull(cmd_pull)
    cmd_save = ['docker', 'save', '-o', os.path.join(image_dir, image_name),
                req]
    subprocess.run(cmd_save, check=True)


def save_docker_image_singularity(req, image_name, image_dir):
    cmd_pull = ['singularity', 'pull', os.path.join(image_dir, image_name), f'docker:{req}']
    _run_command_pull(cmd_pull)


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

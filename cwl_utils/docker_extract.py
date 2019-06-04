#!/usr/bin/env python3
import argparse
import os
import sys

from cwl_utils.image_puller import DockerImagePuller, SingularityImagePuller
import cwl_utils.parser_v1_0 as cwl


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
        else:
            image_puller = DockerImagePuller(req, args.dir)
        image_puller.save_docker_image()


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

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
import argparse
import os
import sys
from pathlib import Path
from typing import Iterator, Union, cast

import cwl_utils.parser_v1_0 as cwl
from cwl_utils.image_puller import (
    DockerImagePuller,
    ImagePuller,
    SingularityImagePuller,
)

ProcessType = Union[cwl.Workflow, cwl.CommandLineTool, cwl.ExpressionTool]


def parse_args() -> argparse.Namespace:
    """Argument parser."""
    parser = argparse.ArgumentParser(
        description="Tool to save docker images from a cwl workflow."
    )
    parser.add_argument("dir", help="Directory in which to save images")
    parser.add_argument("input", help="Input CWL workflow")
    parser.add_argument(
        "-s",
        "--singularity",
        help="Use singularity to pull the image",
        action="store_true",
    )
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    """Extract the docker reqs and download them using Singularity or docker."""
    os.makedirs(args.dir, exist_ok=True)

    top = cwl.load_document(args.input)

    for req in traverse(top):
        if args.singularity:
            image_puller: ImagePuller = SingularityImagePuller(req.dockerPull, args.dir)
        else:
            image_puller = DockerImagePuller(req.dockerPull, args.dir)
        image_puller.save_docker_image()


def extract_docker_requirements(
    process: ProcessType,
) -> Iterator[cwl.DockerRequirement]:
    """Yield an iterator of the docker reqs, normalizint the pull request."""
    for req in extract_docker_reqs(process):
        if isinstance(req.dockerPull, str) and ":" not in req.dockerPull:
            req.dockerPull += ":latest"
        yield req


def extract_docker_reqs(process: ProcessType) -> Iterator[cwl.DockerRequirement]:
    """For the given process, extract the DockerRequirement(s)."""
    if process.requirements:
        for req in process.requirements:
            if isinstance(req, cwl.DockerRequirement):
                yield req
    if process.hints:
        for req in process.hints:
            if req["class"] == "DockerRequirement":
                yield cwl.load_field(
                    req,
                    cwl.DockerRequirementLoader,
                    Path.cwd().as_uri(),
                    process.loadingOptions,
                )


def traverse(process: ProcessType) -> Iterator[cwl.DockerRequirement]:
    """Yield the iterator for the docker reqs, including an workflow steps."""
    yield from extract_docker_requirements(process)
    if isinstance(process, cwl.Workflow):
        yield from traverse_workflow(process)


def get_process_from_step(step: cwl.WorkflowStep) -> ProcessType:
    """Return the process for this step, loading it if necessary."""
    if isinstance(step.run, str):
        return cast(ProcessType, cwl.load_document(step.run))
    return cast(ProcessType, step.run)


def traverse_workflow(workflow: cwl.Workflow) -> Iterator[cwl.DockerRequirement]:
    """Iterate over the steps of this workflow, yielding the docker reqs."""
    for step in workflow.steps:
        for req in extract_docker_reqs(step):
            yield req
        yield from traverse(get_process_from_step(step))


if __name__ == "__main__":
    main(parse_args())
    sys.exit(0)

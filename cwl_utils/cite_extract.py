#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import argparse
import sys
from typing import Iterator, List, Union, cast

import cwl_utils.parser.cwl_v1_0 as cwl

ProcessType = Union[cwl.Workflow, cwl.CommandLineTool, cwl.ExpressionTool]


def arg_parser() -> argparse.ArgumentParser:
    """Argument parser."""
    parser = argparse.ArgumentParser(
        description="Print information about software used in a CWL document (Workflow or CommandLineTool). "
        "For CWL Workflows, all steps will also be searched (recursively)."
    )
    parser.add_argument(
        "input", help="Input CWL document (CWL Workflow or CWL CommandLineTool)"
    )
    return parser


def parse_args(args: List[str]) -> argparse.Namespace:
    """Parse the command line arguments."""
    return arg_parser().parse_args(args)


def run(args: argparse.Namespace) -> int:
    """Extract the software requirements."""
    top = cwl.load_document(args.input)
    traverse(top)
    return 0


def main() -> None:
    """Console entry point."""
    sys.exit(run(parse_args(sys.argv[1:])))


def extract_software_packages(process: ProcessType) -> None:
    """Print software packages found in the given process."""
    for req in extract_software_reqs(process):
        print(process.id)
        process_software_requirement(req)


def extract_software_reqs(
    process: ProcessType,
) -> Iterator[cwl.SoftwareRequirement]:
    """Return an iterator over any SoftwareRequirements found in the given process."""
    if process.requirements:
        for req in process.requirements:
            if isinstance(req, cwl.SoftwareRequirement):
                yield req
    if process.hints:
        for req in process.hints:
            if req["class"] == "SoftwareRequirement":
                yield cwl.load_field(
                    req,
                    cwl.SoftwareRequirementLoader,
                    process.id if process.id else "",
                    process.loadingOptions,
                )


def process_software_requirement(req: cwl.SoftwareRequirement) -> None:
    """Pretty print the software package information."""
    for package in req.packages:
        print(
            "Package: {}, version: {}, specs: {}".format(
                package.package, package.version, package.specs
            )
        )


def traverse(process: ProcessType) -> None:
    """Extract the software packages for this process, and any steps."""
    extract_software_packages(process)
    if isinstance(process, cwl.Workflow):
        traverse_workflow(process)


def get_process_from_step(step: cwl.WorkflowStep) -> ProcessType:
    """Return the process for this step, loading it if needed."""
    if isinstance(step.run, str):
        return cast(ProcessType, cwl.load_document(step.run))
    return cast(ProcessType, step.run)


def traverse_workflow(workflow: cwl.Workflow) -> None:
    """Iterate over the given workflow, extracting the software packages."""
    for step in workflow.steps:
        extract_software_packages(step)
        traverse(get_process_from_step(step))


if __name__ == "__main__":
    main()

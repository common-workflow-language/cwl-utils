#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 Michael R. Crusoe
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Iterator, Union

from ruamel import yaml

from cwl_utils import (
    cwl_v1_0_container_extract,
    cwl_v1_1_container_extract,
    cwl_v1_2_container_extract,
    parser_v1_0,
    parser_v1_1,
    parser_v1_2,
)
from cwl_utils.image_puller import (
    DockerImagePuller,
    ImagePuller,
    SingularityImagePuller,
)

_logger = logging.getLogger("cwl-container-extractor")  # pylint: disable=invalid-name
defaultStreamHandler = logging.StreamHandler()  # pylint: disable=invalid-name
_logger.addHandler(defaultStreamHandler)
_logger.setLevel(logging.INFO)


def parse_args() -> argparse.Namespace:
    """Argument parser."""
    parser = argparse.ArgumentParser(
        description="Tool to save all the software container "
        "images referenced from one or more CWL workflows/tools. The images can "
        "be saved in either Docker or Singularity format."
    )
    parser.add_argument("dir", help="Directory in which to save container images")
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more CWL documents "
        "(Workflows or CommandLineTools) to search for software container "
        "references ('DockerRequirement's)",
    )
    parser.add_argument(
        "-s",
        "--singularity",
        help="Use singularity to pull the image",
        action="store_true",
    )
    parser.add_argument(
        "--force-pull",
        help="Pull the image from the registry, "
        "even if we have a local copy. (Not applicable for Singularity mode)",
        action="store_true",
    )
    parser.add_argument(
        "--skip-existing",
        help="Don't overwrite existing image files.",
        action="store_true",
    )
    return parser.parse_args()


def main(args: argparse.Namespace) -> int:
    """Extract the docker reqs and download them using Singularity or docker."""
    os.makedirs(args.dir, exist_ok=True)
    for document in args.inputs:
        _logger.info("Processing %s.", document)
        with open(document, "r") as doc_handle:
            result = yaml.main.round_trip_load(doc_handle, preserve_quotes=True)
        version = result["cwlVersion"]
        uri = Path(document).resolve().as_uri()
        if version == "v1.0":
            top = parser_v1_0.load_document_by_yaml(result, uri)
            traverse: Callable[
                [Any],
                Iterator[
                    Union[
                        parser_v1_0.DockerRequirement,
                        parser_v1_1.DockerRequirement,
                        parser_v1_2.DockerRequirement,
                    ]
                ],
            ] = cwl_v1_0_container_extract.traverse
        elif version == "v1.1":
            top = parser_v1_1.load_document_by_yaml(result, uri)
            traverse = cwl_v1_1_container_extract.traverse
        elif version == "v1.2":
            top = parser_v1_2.load_document_by_yaml(result, uri)
            traverse = cwl_v1_2_container_extract.traverse
        else:
            _logger.error(
                "Sorry, %s is not a supported CWL version by this tool.", version
            )
            return -1

    for req in traverse(top):
        if args.singularity:
            image_puller: ImagePuller = SingularityImagePuller(req.dockerPull, Path(args.dir))
        else:
            image_puller = DockerImagePuller(req.dockerPull, Path(args.dir))
        image_puller.save_docker_image(args.skip_existing, args.force_pull)

    return 0


if __name__ == "__main__":
    sys.exit(main(parse_args()))

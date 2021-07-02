#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 Michael R. Crusoe
"""Normalize CWL documents to CWL v1.2, JSON style."""
import argparse
import logging
import sys
import tempfile
from pathlib import Path
from typing import (
    List,
    MutableSequence,
    Optional,
    Set,
)

from cwltool.context import LoadingContext, RuntimeContext
from cwltool.load_tool import (
    fetch_document,
    resolve_and_validate_document,
    resolve_tool_uri,
)
from cwltool.loghandler import _logger as _cwltoollogger
from cwltool.main import print_pack
from cwltool.process import use_standard_schema
from cwlupgrader import main as cwlupgrader
from ruamel import yaml
from schema_salad.sourceline import add_lc_filename

_logger = logging.getLogger("cwl-normalizer")  # pylint: disable=invalid-name
defaultStreamHandler = logging.StreamHandler()  # pylint: disable=invalid-name
_logger.addHandler(defaultStreamHandler)
_logger.setLevel(logging.INFO)
_cwltoollogger.setLevel(100)

from cwl_utils import cwl_v1_2_expression_refactor
from cwl_utils.parser_v1_2 import load_document_by_yaml, save


def parse_args(args: List[str]) -> argparse.Namespace:
    """Argument parser."""
    parser = argparse.ArgumentParser(
        description="Tool to normalize CWL documents. Will upgrade to CWL v1.2, "
        "and pack the result. Can optionally refactor out CWL expressions."
    )
    parser.add_argument(
        "--etools",
        help="Output ExpressionTools, don't go all the way to CommandLineTools.",
        action="store_true",
    )
    parser.add_argument(
        "--skip-some1",
        help="Don't process CommandLineTool.inputs.inputBinding and CommandLineTool.arguments sections.",
        action="store_true",
    )
    parser.add_argument(
        "--skip-some2",
        help="Don't process CommandLineTool.outputEval or CommandLineTool.requirements.InitialWorkDirRequirement.",
        action="store_true",
    )
    parser.add_argument(
        "--no-expression-refactoring",
        help="Don't do any CWL expression refactoring.",
        action="store_true",
    )
    parser.add_argument("dir", help="Directory in which to save converted files")
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more CWL documents.",
    )
    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> int:
    """Collect the arguments and run."""
    if not args:
        args = sys.argv[1:]
    return run(parse_args(args))


def run(args: argparse.Namespace) -> int:
    """Primary processing loop."""
    imports: Set[str] = set()
    for document in args.inputs:
        _logger.info("Processing %s.", document)
        with open(document, "r") as doc_handle:
            result = yaml.main.round_trip_load(doc_handle, preserve_quotes=True)
        add_lc_filename(result, document)
        version = result.get("cwlVersion", None)
        if version in ("draft-3", "cwl:draft-3", "v1.0", "v1.1"):
            result = cwlupgrader.upgrade_document(
                result, False, False, args.dir, imports
            )
        else:
            _logger.error(
                "Sorry, %s in %s is not a supported CWL version by this tool.",
                (version, document),
            )
            return -1
        uri = Path(document).resolve().as_uri()
        if not args.no_expression_refactoring:
            refactored, _ = cwl_v1_2_expression_refactor.traverse(
                load_document_by_yaml(result, uri),
                not args.etools,
                False,
                args.skip_some1,
                args.skip_some2,
            )
            if not isinstance(refactored, MutableSequence):
                result = save(
                    refactored,
                    base_url=refactored.loadingOptions.fileuri
                    if refactored.loadingOptions.fileuri
                    else "",
                )
            #   ^^ Setting the base_url and keeping the default value
            #      for relative_uris=True means that the IDs in the generated
            #      JSON/YAML are kept clean of the path to the input document
            else:
                result = [
                    save(result_item, base_url=result_item.loadingOptions.fileuri)
                    for result_item in refactored
                ]
        if "$graph" in result:
            packed = result
        else:
            with tempfile.TemporaryDirectory() as tmpdirname:
                path = Path(tmpdirname) / Path(document).name
                with open(path, "w") as handle:
                    yaml.main.round_trip_dump(result, handle)
                # TODO replace the cwltool based packing with a parser_v1_2 based packer
                runtimeContext = RuntimeContext()
                loadingContext = LoadingContext()
                use_standard_schema("v1.2")
                # loadingContext.construct_tool_object = workflow.default_make_tool
                # loadingContext.resolver = tool_resolver
                loadingContext.do_update = False
                uri, tool_file_uri = resolve_tool_uri(
                    str(path),
                    resolver=loadingContext.resolver,
                    fetcher_constructor=loadingContext.fetcher_constructor,
                )
                loadingContext, workflowobj, uri = fetch_document(uri, loadingContext)
                loadingContext, uri = resolve_and_validate_document(
                    loadingContext,
                    workflowobj,
                    uri,
                    preprocess_only=True,
                    skip_schemas=True,
                )
                packed = print_pack(loadingContext, uri)
        output = Path(args.dir) / Path(document).name
        with open(output, "w", encoding="utf-8") as output_filehandle:
            output_filehandle.write(packed)
    return 0


if __name__ == "__main__":
    main()
    sys.exit(0)

#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2018-2021 Michael R. Crusoe
"""CWL Expression refactoring tool for CWL."""
import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, MutableSequence, Optional, Tuple, Union

from cwltool.loghandler import _logger as _cwltoollogger
from ruamel import yaml
from typing_extensions import Protocol

_logger = logging.getLogger("cwl-expression-refactor")  # pylint: disable=invalid-name
defaultStreamHandler = logging.StreamHandler()  # pylint: disable=invalid-name
_logger.addHandler(defaultStreamHandler)
_logger.setLevel(logging.INFO)
_cwltoollogger.setLevel(100)

from cwl_utils import (
    cwl_v1_0_expression_refactor,
    cwl_v1_1_expression_refactor,
    cwl_v1_2_expression_refactor,
    parser_v1_0,
    parser_v1_1,
    parser_v1_2,
)

save_type = Union[Dict[str, str], List[Union[Dict[str, str], List[Any], None]], None]


class saveCWL(Protocol):
    """Shortcut type for CWL v1.x parse.save()."""

    def __call__(
        self,
        val: Optional[Union[Any, MutableSequence[Any]]],
        top: bool = True,
        base_url: str = "",
        relative_uris: bool = True,
    ) -> save_type:
        """Must use this instead of a Callable due to the keyword args."""
        ...


def parse_args(args: List[str]) -> argparse.Namespace:
    """Argument parser."""
    parser = argparse.ArgumentParser(
        description="Tool to refactor CWL documents so that any CWL expression "
        "are separate steps as either ExpressionTools or CommandLineTools. Exit code 7 "
        "means a single CWL document was provided but it did not need modification."
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
    for document in args.inputs:
        _logger.info("Processing %s.", document)
        with open(document, "r") as doc_handle:
            result = yaml.main.round_trip_load(doc_handle, preserve_quotes=True)
        version = result["cwlVersion"]
        uri = Path(document).resolve().as_uri()
        if version == "v1.0":
            top = parser_v1_0.load_document_by_yaml(result, uri)
            traverse: Callable[
                [Any, bool, bool, bool, bool], Tuple[Any, bool]
            ] = cwl_v1_0_expression_refactor.traverse
            save: saveCWL = parser_v1_0.save
        elif version == "v1.1":
            top = parser_v1_1.load_document_by_yaml(result, uri)
            traverse = cwl_v1_1_expression_refactor.traverse
            save = parser_v1_1.save
        elif version == "v1.2":
            top = parser_v1_2.load_document_by_yaml(result, uri)
            traverse = cwl_v1_2_expression_refactor.traverse
            save = parser_v1_2.save
        else:
            _logger.error(
                "Sorry, %s is not a supported CWL version by this tool.", version
            )
            return -1
        result, modified = traverse(
            top, not args.etools, False, args.skip_some1, args.skip_some2
        )
        output = Path(args.dir) / Path(document).name
        if not modified:
            if len(args.inputs) > 1:
                shutil.copyfile(document, output)
                continue
            else:
                return 7
        if not isinstance(result, MutableSequence):
            result_json = save(
                result,
                base_url=result.loadingOptions.fileuri
                if result.loadingOptions.fileuri
                else "",
            )
        #   ^^ Setting the base_url and keeping the default value
        #      for relative_uris=True means that the IDs in the generated
        #      JSON/YAML are kept clean of the path to the input document
        else:
            result_json = [
                save(result_item, base_url=result_item.loadingOptions.fileuri)
                for result_item in result
            ]
        yaml.scalarstring.walk_tree(result_json)
        # ^ converts multine line strings to nice multiline YAML
        with open(output, "w", encoding="utf-8") as output_filehandle:
            output_filehandle.write(
                "#!/usr/bin/env cwl-runner\n"
            )  # TODO: teach the codegen to do this?
            yaml.main.round_trip_dump(result_json, output_filehandle)
    return 0


if __name__ == "__main__":
    main()
    sys.exit(0)

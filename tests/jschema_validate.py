#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path

from jsonschema.validators import validate
from ruamel.yaml import YAML

from cwl_utils.inputs_schema_gen import cwl_to_jsonschema
from cwl_utils.parser import load_document_by_uri


def main() -> None:
    parser = argparse.ArgumentParser(description="test cwl-inputs-schema-gen.")
    parser.add_argument(
        "--outdir",
        type=str,
        default=os.path.abspath("."),
        help="Output directory. This is present only for cwltest's usage, and it is ignored.",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Only print warnings and errors."
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument(
        "workflow",
        type=str,
        nargs="?",
        default=None,
        metavar="cwl_document",
        help="path or URL to a CWL Workflow, " "CommandLineTool, or ExpressionTool.",
    )
    parser.add_argument(
        "job_order",
        nargs=argparse.REMAINDER,
        metavar="inputs_object",
        help="path or URL to a YAML or JSON "
        "formatted description of the required input values for the given "
        "`cwl_document`.",
    )

    args = parser.parse_args(sys.argv[1:])

    if args.version:
        print(f"{sys.argv[1]} 0.0.1")
        return

    if len(args.job_order) < 1:
        job_order = {}
        job_order_name = "empty inputs"
    else:
        yaml = YAML()
        job_order_name = args.job_order[0]
        job_order = yaml.load(Path(job_order_name))

    validate(
        job_order,
        cwl_to_jsonschema(load_document_by_uri(args.workflow)),
    )

    if not args.quiet:
        print(
            f"Validation of the JSON schema generated from {args.workflow} "
            "using {job_order_name} suceeded."
        )


if __name__ == "__main__":
    main()

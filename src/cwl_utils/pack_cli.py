#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pack a CWL document into a single JSON document."""

import argparse
import json
import sys

from cwl_utils.pack import pack


def arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Pack a CWL document and its referenced documents into a "
        "single JSON document. Does not upgrade the CWL version and does not "
        "refactor expressions."
    )
    parser.add_argument("cwlfile", help="Input CWL document.")
    parser.add_argument(
        "-o",
        "--outfile",
        default=None,
        help="Write packed JSON to this path instead of stdout.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=4,
        help="JSON indent width (default: 4).",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    """Pack the input CWL document and write the result."""
    packed = pack(args.cwlfile)
    serialized = json.dumps(packed, indent=args.indent)
    if args.outfile is None:
        sys.stdout.write(serialized)
        sys.stdout.write("\n")
    else:
        with open(args.outfile, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.write("\n")
    return 0


def main() -> int:
    """Console entry point."""
    return run(arg_parser().parse_args(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())

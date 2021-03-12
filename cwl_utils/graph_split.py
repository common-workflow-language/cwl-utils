#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2019-2020 Michael R. Crusoe
# Copyright 2020 Altair Wei
"""
Unpacks the result of `cwltool --unpack`.

Only tested with a single v1.0 workflow.
"""

import argparse
import json
import os
from typing import IO, Any, MutableMapping, Set, Text, Union, cast

from cwlformat.formatter import stringify_dict
from ruamel import yaml
from schema_salad.sourceline import SourceLine, add_lc_filename


def main() -> None:
    """Split the packed CWL at the path of the first argument."""
    parser = argparse.ArgumentParser(description="Split the packed CWL.")
    parser.add_argument("cwlfile")
    parser.add_argument(
        "-m",
        "--mainfile",
        default=None,
        type=str,
        help="Specify the name of the main document.",
    )
    parser.add_argument(
        "-f",
        "--output-format",
        choices=["json", "yaml"],
        type=str,
        default="json",
        help="Specify the format of the output CWL files.",
    )
    parser.add_argument(
        "-p",
        "--pretty",
        action="store_true",
        default=False,
        help="Beautify the output CWL document, only works with yaml format.",
    )
    parser.add_argument(
        "-C",
        "--outdir",
        type=str,
        default=os.getcwd(),
        help="Output folder for the unpacked CWL files.",
    )
    options = parser.parse_args()

    with open(options.cwlfile, "r") as source_handle:
        run(
            source_handle,
            options.outdir,
            options.output_format,
            options.mainfile,
            options.pretty,
        )


def run(
    sourceIO: IO[str], output_dir: str, output_format: str, mainfile: str, pretty: bool
) -> None:
    """Loop over the provided packed CWL document and split it up."""
    source = yaml.main.round_trip_load(sourceIO, preserve_quotes=True)
    add_lc_filename(source, sourceIO.name)

    if "$graph" not in source:
        print("No $graph, so not for us.")
        return

    version = source.pop("cwlVersion")

    def my_represent_none(
        self: Any, data: Any
    ) -> Any:  # pylint: disable=unused-argument
        """Force clean representation of 'null'."""
        return self.represent_scalar("tag:yaml.org,2002:null", "null")

    yaml.representer.RoundTripRepresenter.add_representer(type(None), my_represent_none)

    for entry in source["$graph"]:
        entry_id = entry.pop("id")[1:]
        entry["cwlVersion"] = version
        imports = rewrite(entry, entry_id)
        if imports:
            for import_name in imports:
                rewrite_types(entry, "#{}".format(import_name), False)
        if entry_id == "main":
            if mainfile is None:
                entry_id = "unpacked_{}".format(os.path.basename(sourceIO.name))
            else:
                entry_id = mainfile

        output_file = os.path.join(output_dir, entry_id)
        if output_format == "json":
            json_dump(entry, output_file)
        elif output_format == "yaml":
            yaml_dump(entry, output_file, pretty)


def rewrite(document: Any, doc_id: str) -> Set[str]:
    """Rewrite the given element from the CWL $graph."""
    imports = set()
    if isinstance(document, list) and not isinstance(document, Text):
        for entry in document:
            imports.update(rewrite(entry, doc_id))
    elif isinstance(document, dict):
        this_id = document["id"] if "id" in document else None
        for key, value in document.items():
            with SourceLine(document, key, Exception):
                if key == "run" and isinstance(value, str) and value[0] == "#":
                    document[key] = value[1:]
                elif key in ("id", "outputSource") and value.startswith("#" + doc_id):
                    document[key] = value[len(doc_id) + 2 :]
                elif key == "out":

                    def rewrite_id(entry: Any) -> Union[MutableMapping[Any, Any], str]:
                        if isinstance(entry, MutableMapping):
                            if entry["id"].startswith(this_id):
                                entry["id"] = cast(str, entry["id"])[len(this_id) + 1 :]
                            return entry
                        elif isinstance(entry, str):
                            if entry.startswith(this_id):
                                return entry[len(this_id) + 1 :]
                        raise Exception(
                            "{} is neither a dictionary nor string.".format(entry)
                        )

                    document[key][:] = [rewrite_id(entry) for entry in value]
                elif key in ("source", "scatter", "items", "format"):
                    if (
                        isinstance(value, Text)
                        and value.startswith("#")
                        and "/" in value
                    ):
                        referrant_file, sub = value[1:].split("/", 1)
                        if referrant_file == doc_id:
                            document[key] = sub
                        else:
                            document[key] = "{}#{}".format(referrant_file, sub)
                    elif isinstance(value, list):
                        new_sources = list()
                        for entry in value:
                            if entry.startswith("#" + doc_id):
                                new_sources.append(entry[len(doc_id) + 2 :])
                            else:
                                new_sources.append(entry)
                        document[key] = new_sources
                elif key == "$import":
                    rewrite_import(document)
                elif key == "class" and value == "SchemaDefRequirement":
                    return rewrite_schemadef(document)
                else:
                    imports.update(rewrite(value, doc_id))
    return imports


def rewrite_import(document: MutableMapping[str, Any]) -> None:
    """Adjust the $import directive."""
    external_file = document["$import"].split("/")[0][1:]
    document["$import"] = external_file


def rewrite_types(field: Any, entry_file: str, sameself: bool) -> None:
    """Clean up the names of the types."""
    if isinstance(field, list) and not isinstance(field, Text):
        for entry in field:
            rewrite_types(entry, entry_file, sameself)
        return
    if isinstance(field, dict):
        for key, value in field.items():
            for name in ("type", "items"):
                if key == name:
                    if isinstance(value, Text) and value.startswith(entry_file):
                        if sameself:
                            field[key] = value[len(entry_file) + 1 :]
                        else:
                            field[key] = "{d[0]}#{d[1]}".format(
                                d=value[1:].split("/", 1)
                            )
            if isinstance(value, dict):
                rewrite_types(value, entry_file, sameself)
            if isinstance(value, list) and not isinstance(value, Text):
                for entry in value:
                    rewrite_types(entry, entry_file, sameself)


def rewrite_schemadef(document: MutableMapping[str, Any]) -> Set[str]:
    """Dump the schemadefs to their own file."""
    for entry in document["types"]:
        if "$import" in entry:
            rewrite_import(entry)
        elif "name" in entry and "/" in entry["name"]:
            entry_file, entry["name"] = entry["name"].split("/")
            for field in entry["fields"]:
                field["name"] = field["name"].split("/")[2]
                rewrite_types(field, entry_file, True)
            with open(entry_file[1:], "a", encoding="utf-8") as entry_handle:
                yaml.main.dump(
                    [entry], entry_handle, Dumper=yaml.dumper.RoundTripDumper
                )
            entry["$import"] = entry_file[1:]
            del entry["name"]
            del entry["type"]
            del entry["fields"]
    seen_imports = set()

    def seen_import(entry: MutableMapping[str, Any]) -> bool:
        if "$import" in entry:
            external_file = entry["$import"]
            if external_file not in seen_imports:
                seen_imports.add(external_file)
                return True
            return False
        return True

    types = document["types"]
    document["types"][:] = [entry for entry in types if seen_import(entry)]
    return seen_imports


def json_dump(entry: Any, output_file: str) -> None:
    """Output object as JSON."""
    with open(output_file, "w", encoding="utf-8") as result_handle:
        json.dump(entry, result_handle, indent=4)


def yaml_dump(entry: Any, output_file: str, pretty: bool) -> None:
    """Output object as YAML."""
    with open(output_file, "w", encoding="utf-8") as result_handle:
        if pretty:
            result_handle.write(stringify_dict(entry))
        else:
            yaml.main.round_trip_dump(
                entry,
                result_handle,
                default_flow_style=False,
                indent=4,
                block_seq_indent=2,
            )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate JSON Schema from CWL inputs object."""
import argparse
import logging
import sys
from json import dumps
from typing import Any, List

from cwl_utils.loghandler import _logger as _cwlutilslogger
from cwl_utils.parser import load_document_by_uri, save

_logger = logging.getLogger("cwl-inputs_schema_gen")  # pylint: disable=invalid-name
defaultStreamHandler = logging.StreamHandler()  # pylint: disable=invalid-name
_logger.addHandler(defaultStreamHandler)
_logger.setLevel(logging.INFO)
_cwlutilslogger.setLevel(100)


def cwl_inputs_to_jsonschema(cwl_inputs: Any) -> Any:
    """
    Converts a JSON-serialized CWL inputs object into a JSONSchema object.

    Args:
        cwl_inputs: JSON-serialized CWL inputs object.

    Returns:
        A JSONSchema object.

    Example:
        cwl_obj = load_document_by_uri(<CWL_URL>)
        saved_obj = save(cwl_obj)
        cwl_inputs = saved_obj["inputs"]
        jsonschema = cwl_inputs_to_jsonschema(cwl_inputs)
    """
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    # Refer to https://www.commonwl.org/v1.2/Workflow.html#WorkflowInputParameter for more details
    for input_item in cwl_inputs:
        input_id = input_item.get("id")
        input_type = input_item.get("type")
        if input_id is None or input_type is None:
            raise ValueError("Each item in the 'inputs' object must include 'id' and 'type' fields.")

        prop_schema = _cwl_type_to_prop_schema(input_type)

        if "secondaryFiles" in input_item:
            # TODO: do nothing?
            # secondaryFiles does not seem to affect the --make-template
            # For example, refer to $ cwltool --make-template https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/stage-array.cwl
            pass

        if "default" in input_item:
            prop_schema["default"] = input_item["default"]

        schema["properties"][input_id] = prop_schema  # type: ignore
        if "default" not in input_item and "null" not in input_type:
            schema["required"].append(input_id)

    return schema


def _cwl_type_to_prop_schema(input_type: Any) -> Any:
    """
    This function converts the type of each item in a JSON-serialized CWL inputs object into a value in a JSONSchema property.
    The input type may not only be a string, but also a nested type information as a dict or list.
    Therefore, this function may be called recursively.
    """

    if isinstance(input_type, dict):
        nested_type = input_type.get("type")
        if nested_type is None:
            raise ValueError("The 'type' field is missing in the 'inputs.[].type' nested type object.")

        if nested_type == "enum":
            enum = input_type.get("symbols")
            if enum is None:
                raise ValueError("The 'symbols' field is missing in the 'inputs.[].type' nested type object for enum.")
            return {
                "type": "string",
                "enum": enum,
            }

        elif nested_type == "record":
            schema = {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            }

            fields = input_type.get("fields")
            if fields is None:
                raise ValueError("The 'fields' field is missing in the 'inputs.[].type' nested type object for record.")
            for field in fields:
                field_name = field.get("name")
                field_type = field.get("type")
                if field_name is None or field_type is None:
                    raise ValueError("Both 'name' and 'type' fields are required in the 'inputs.[].type.[].fields' object for record.")
                field_id = field_name.split("#")[-1].split("/")[-1]
                schema["properties"][field_id] = _cwl_type_to_prop_schema(field_type)  # type: ignore
                if "default" not in field:
                    schema["required"].append(field_id)
            return schema

        elif nested_type == "array":
            item_type = input_type.get("items")
            if item_type is None:
                raise ValueError("The 'items' field is missing in the 'inputs.[].type' nested type object for array.")
            return {
                "type": "array",
                "items": _cwl_type_to_prop_schema(item_type),
                "additionalItems": False
            }

        else:
            raise ValueError(f"Unexpected value '{input_type}' encountered in 'inputs.[].type'.")

    elif isinstance(input_type, list):
        if len(input_type) != 2 or "null" not in input_type:
            raise ValueError(f"Unexpected value '{input_type}' encountered in 'inputs.[].type'. 'null' is required when 'inputs.[].type' is a list.")
        original_type = [t for t in input_type if t != "null"][0]
        schema = _cwl_type_to_prop_schema(original_type)
        schema["nullable"] = True
        return schema

    else:
        if input_type == "File":
            return {
                "type": "object",
                "properties": {
                    "class": {"type": "string", "const": "File"},
                    "path": {"type": "string"},
                    "location": {"type": "string"}
                },
                "required": ["class"],
                "oneOf": [
                    {"required": ["path"]},
                    {"required": ["location"]}
                ],
                "additionalProperties": False,
            }
        elif input_type == "Directory":
            return {
                "type": "object",
                "properties": {
                    "class": {"type": "string", "const": "Directory"},
                    "path": {"type": "string"},
                    "location": {"type": "string"}
                },
                "required": ["class"],
                "oneOf": [
                    {"required": ["path"]},
                    {"required": ["location"]}
                ],
                "additionalProperties": False,
            }
        elif input_type == "Any":
            return {
                "anyOf": [
                    {"type": "boolean"},
                    {"type": "integer"},
                    {"type": "number"},
                    {"type": "string"},
                    {"type": "array"},
                    {"type": "object"}
                ]
            }
        elif input_type == "null":
            return {"type": "null"}
        else:
            if input_type in ["long", "float", "double"]:
                return {"type": "number"}
            elif input_type == "int":
                return {"type": "integer"}
            else:
                return {"type": input_type}


def arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate JSON Schema from CWL inputs object."
    )
    parser.add_argument("cwl_url", help="URL of the CWL document.")
    parser.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="Output file. Default is stdout.",
    )
    return parser


def parse_args(args: List[str]) -> argparse.Namespace:
    """Parse the command line arguments."""
    return arg_parser().parse_args(args)


def main() -> None:
    """Console entry point."""
    sys.exit(run(parse_args(sys.argv[1:])))


def run(args: argparse.Namespace) -> int:
    """Primary processing loop."""
    cwl_obj = load_document_by_uri(args.cwl_url)
    saved_obj = save(cwl_obj)  # TODO: Use "typed CWL object" OR "saved object"?
    if "inputs" not in saved_obj:
        _logger.exception("Inputs object not found in the CWL document.")
        return 1
    json_serialized_inputs_obj = saved_obj["inputs"]
    try:
        jsonschema = cwl_inputs_to_jsonschema(json_serialized_inputs_obj)
    except Exception as e:
        _logger.exception("Failed to generate JSON Schema from CWL inputs object. Error: %s", e)
        return 1
    args.output.write(dumps(jsonschema, indent=2))

    return 0


if __name__ == "__main__":
    main()

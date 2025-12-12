# SPDX-License-Identifier: Apache-2.0
"""Tests for cwl-inputs-schema-gen."""
import logging
from pathlib import Path

import pytest
from jsonschema.exceptions import SchemaError, ValidationError
from jsonschema.validators import validate
from ruamel.yaml import YAML

from cwl_utils.inputs_schema_gen import cwl_to_jsonschema
from cwl_utils.parser import load_document_by_uri

from .util import get_path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

TEST_PARAMS = [
    # Packed Case
    (
        get_path("testdata/revsort-packed.cwl"),
        get_path("testdata/revsort-job.json"),
    ),
    # The number of parameters is a little large, and the definition itself is a straightforward case.
    (
        get_path("testdata/bwa-mem-tool.cwl"),
        get_path("testdata/bwa-mem-job.json"),
    ),
    # The case where CommandInputParameter is shortened (e.g., param: string)
    (
        get_path("testdata/env-tool1.cwl"),
        get_path("testdata/env-job.json"),
    ),
    # Dir
    (
        get_path("testdata/dir.cwl"),
        get_path("testdata/dir-job.yml"),
    ),
    # SecondaryFiles
    (
        get_path("testdata/rename-inputs.cwl"),
        get_path("testdata/rename-inputs.yml"),
    ),
    # Stage array
    (
        get_path("testdata/stage-array.cwl"),
        get_path("testdata/stage-array-job.json"),
    ),
]


@pytest.mark.parametrize("tool_path,inputs_path", TEST_PARAMS)
def test_cwl_inputs_to_jsonschema(tool_path: Path, inputs_path: Path) -> None:
    cwl_obj = load_document_by_uri(tool_path.as_uri())

    logger.info(f"Generating schema for {tool_path.name}")
    json_schema = cwl_to_jsonschema(cwl_obj)

    logger.info(
        f"Testing {inputs_path.name} against schema generated for input {tool_path.name}"
    )

    input_obj = YAML().load(inputs_path)

    try:
        validate(input_obj, json_schema)
    except (ValidationError, SchemaError) as err:
        logger.error(
            f"Validation failed for {inputs_path.name} "
            f"against schema generated for input {tool_path.name}"
        )
        raise SchemaError(f"{inputs_path.name} failed schema validation") from err


def test_cwl_inputs_to_jsonschema_single_fail() -> None:
    """Compare tool schema of param 1 against input schema of param 2."""
    tool_path: Path = TEST_PARAMS[0][0]
    inputs_path: Path = TEST_PARAMS[3][1]

    cwl_obj = load_document_by_uri(tool_path.as_uri())

    logger.info(f"Generating schema for {tool_path.name}")
    json_schema = cwl_to_jsonschema(cwl_obj)

    logger.info(
        f"Testing {inputs_path.name} against schema generated for input {tool_path.name}"
    )

    input_obj = YAML().load(inputs_path)

    # We expect this to fail
    with pytest.raises(ValidationError):
        validate(input_obj, json_schema)


BAD_TEST_PARAMS = [
    # Any without defaults cannot be unspecified
    (
        get_path("testdata/null-expression2-tool.cwl"),
        get_path("testdata/empty.json"),
        "'i1' is a required property",
    ),
    # null to Any type without a default value.
    (
        get_path("testdata/null-expression2-tool.cwl"),
        get_path("testdata/null-expression1-job.json"),
        "None is not valid under any of the given schemas",
    ),
    # Any without defaults, unspecified
    (
        get_path("testdata/echo-tool.cwl"),
        get_path("testdata/null-expression-echo-job.json"),
        "None is not valid under any of the given schemas",
    ),
    # JSON null provided for required input
    (
        get_path("testdata/echo-tool.cwl"),
        get_path("testdata/null-expression1-job.json"),
        "'in' is a required property",
    ),
]


@pytest.mark.parametrize("tool_path,inputs_path,exception_message", BAD_TEST_PARAMS)
def test_cwl_inputs_to_jsonschema_fails(
    tool_path: Path,
    inputs_path: Path,
    exception_message: str,
) -> None:
    cwl_obj = load_document_by_uri(tool_path.as_uri())

    logger.info(f"Generating schema for {tool_path.name}")
    json_schema = cwl_to_jsonschema(cwl_obj)

    logger.info(
        f"Testing {inputs_path.name} against schema generated for input {tool_path.name}"
    )

    yaml = YAML()

    input_obj = yaml.load(inputs_path)

    with pytest.raises(ValidationError, match=exception_message):
        validate(input_obj, json_schema)

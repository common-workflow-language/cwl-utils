# SPDX-License-Identifier: Apache-2.0
"""Tests for cwl-inputs-schema-gen."""
from pathlib import Path
from typing import Dict

import pytest
import requests
from jsonschema.exceptions import SchemaError, ValidationError
from jsonschema.validators import validate
from ruamel.yaml import YAML

from cwl_utils.inputs_schema_gen import cwl_to_jsonschema
from cwl_utils.loghandler import _logger as _cwlutilslogger
from cwl_utils.parser import load_document_by_uri

TEST_ROOT_URL = (
    "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests"
)

TEST_PARAMS = [
    # Packed Case
    {
        "tool_url": f"{TEST_ROOT_URL}/revsort-packed.cwl",
        "input_url": f"{TEST_ROOT_URL}/revsort-job.json",
    },
    # The number of parameters is a little large, and the definition itself is a straightforward case.
    {
        "tool_url": f"{TEST_ROOT_URL}/bwa-mem-tool.cwl",
        "input_url": f"{TEST_ROOT_URL}/bwa-mem-job.json",
    },
    # The case where CommandInputParameter is shortened (e.g., param: string)
    {
        "tool_url": f"{TEST_ROOT_URL}/env-tool1.cwl",
        "input_url": f"{TEST_ROOT_URL}/env-job.json",
    },
    # Dir
    {
        "tool_url": f"{TEST_ROOT_URL}/dir.cwl",
        "input_url": f"{TEST_ROOT_URL}/dir-job.yml",
    },
    # SecondaryFiles
    {
        "tool_url": f"{TEST_ROOT_URL}/secondaryfiles/rename-inputs.cwl",
        "input_url": f"{TEST_ROOT_URL}/secondaryfiles/rename-inputs.yml",
    },
    # Stage array
    {
        "tool_url": f"{TEST_ROOT_URL}/stage-array.cwl",
        "input_url": f"{TEST_ROOT_URL}/stage-array-job.json",
    },
]


@pytest.mark.parametrize("test_param", TEST_PARAMS)
def test_cwl_inputs_to_jsonschema(test_param: Dict[str, str]) -> None:
    tool_url = test_param["tool_url"]
    input_url = test_param["input_url"]

    cwl_obj = load_document_by_uri(tool_url)

    _cwlutilslogger.info(f"Generating schema for {Path(tool_url).name}")
    json_schema = cwl_to_jsonschema(cwl_obj)

    _cwlutilslogger.info(
        f"Testing {Path(input_url).name} against schema generated for input {Path(tool_url).name}"
    )

    yaml = YAML()

    input_obj = yaml.load(requests.get(input_url).text)

    try:
        validate(input_obj, json_schema)
    except (ValidationError, SchemaError) as err:
        _cwlutilslogger.error(
            f"Validation failed for {Path(input_url).name} "
            f"against schema generated for input {Path(tool_url).name}"
        )
        raise SchemaError(f"{Path(input_url).name} failed schema validation") from err


def test_cwl_inputs_to_jsonschema_fails() -> None:
    """Compare tool schema of param 1 against input schema of param 2."""
    tool_url = TEST_PARAMS[0]["tool_url"]
    input_url = TEST_PARAMS[3]["input_url"]

    cwl_obj = load_document_by_uri(tool_url)

    _cwlutilslogger.info(f"Generating schema for {Path(tool_url).name}")
    json_schema = cwl_to_jsonschema(cwl_obj)

    _cwlutilslogger.info(
        f"Testing {Path(input_url).name} against schema generated for input {Path(tool_url).name}"
    )

    yaml = YAML()

    input_obj = yaml.load(requests.get(input_url).text)

    # We expect this to fail
    with pytest.raises(ValidationError):
        validate(input_obj, json_schema)

# SPDX-License-Identifier: Apache-2.0
"""Tests for cwl-inputs-schema-gen."""
from pathlib import Path

import pytest
from jsonschema.exceptions import SchemaError, ValidationError
from jsonschema.validators import validate
from ruamel.yaml import YAML

from cwl_utils.inputs_schema_gen import cwl_to_jsonschema
from cwl_utils.loghandler import _logger as _cwlutilslogger
from cwl_utils.parser import load_document_by_uri

from .util import get_data

TEST_PARAMS = [
    # Packed Case
    (
        Path(get_data("testdata/revsort-packed.cwl")).as_uri(),
        get_data("testdata/revsort-job.json"),
    ),
    # The number of parameters is a little large, and the definition itself is a straightforward case.
    (
        Path(get_data("testdata/bwa-mem-tool.cwl")).as_uri(),
        get_data("testdata/bwa-mem-job.json"),
    ),
    # The case where CommandInputParameter is shortened (e.g., param: string)
    (
        Path(get_data("testdata/env-tool1.cwl")).as_uri(),
        get_data("testdata/env-job.json"),
    ),
    # Dir
    (
        Path(get_data("testdata/dir.cwl")).as_uri(),
        get_data("testdata/dir-job.yml"),
    ),
    # SecondaryFiles
    (
        Path(get_data("testdata/rename-inputs.cwl")).as_uri(),
        get_data("testdata/rename-inputs.yml"),
    ),
    # Stage array
    (
        Path(get_data("testdata/stage-array.cwl")).as_uri(),
        get_data("testdata/stage-array-job.json"),
    ),
]


@pytest.mark.parametrize("tool_url,input_loc", TEST_PARAMS)
def test_cwl_inputs_to_jsonschema(tool_url: str, input_loc: str) -> None:
    cwl_obj = load_document_by_uri(tool_url)

    _cwlutilslogger.info(f"Generating schema for {Path(tool_url).name}")
    json_schema = cwl_to_jsonschema(cwl_obj)

    _cwlutilslogger.info(
        f"Testing {Path(input_loc).name} against schema generated for input {Path(tool_url).name}"
    )

    yaml = YAML()

    input_obj = yaml.load(Path(input_loc))

    try:
        validate(input_obj, json_schema)
    except (ValidationError, SchemaError) as err:
        _cwlutilslogger.error(
            f"Validation failed for {Path(input_loc).name} "
            f"against schema generated for input {Path(tool_url).name}"
        )
        raise SchemaError(f"{Path(input_loc).name} failed schema validation") from err


def test_cwl_inputs_to_jsonschema_fails() -> None:
    """Compare tool schema of param 1 against input schema of param 2."""
    tool_url = TEST_PARAMS[0][0]
    input_loc = TEST_PARAMS[3][1]

    cwl_obj = load_document_by_uri(tool_url)

    _cwlutilslogger.info(f"Generating schema for {Path(tool_url).name}")
    json_schema = cwl_to_jsonschema(cwl_obj)

    _cwlutilslogger.info(
        f"Testing {Path(input_loc).name} against schema generated for input {Path(tool_url).name}"
    )

    yaml = YAML()

    input_obj = yaml.load(Path(input_loc))

    # We expect this to fail
    with pytest.raises(ValidationError):
        validate(input_obj, json_schema)

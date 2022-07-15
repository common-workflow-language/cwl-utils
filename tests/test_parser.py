"""Test the load and save functions for CWL."""
from pathlib import Path

from ruamel import yaml

import cwl_utils.parser.latest as latest
from cwl_utils.parser import (
    cwl_v1_2,
    cwl_version,
    load_document,
    load_document_by_uri,
    save,
)

HERE = Path(__file__).resolve().parent
TEST_v1_0_CWL = HERE / "../testdata/md5sum.cwl"
TEST_v1_0_CWL_REMOTE = "https://raw.githubusercontent.com/common-workflow-language/cwl-utils/main/testdata/md5sum.cwl"
TEST_v1_2_CWL = HERE / "../testdata/workflow_input_format_expr_v1_2.cwl"


def test_cwl_version() -> None:
    """Test cwl_version for a CommandLineTool."""
    with open(TEST_v1_0_CWL) as cwl_h:
        yaml_obj = yaml.main.round_trip_load(cwl_h, preserve_quotes=True)
    ver = cwl_version(yaml_obj)
    assert ver == "v1.0"


def test_load_document() -> None:
    """Test load_document for a CommandLineTool."""
    with open(TEST_v1_0_CWL) as cwl_h:
        yaml_obj = yaml.main.round_trip_load(cwl_h, preserve_quotes=True)
    cwl_obj = load_document(yaml_obj)
    assert cwl_obj.cwlVersion == "v1.0"
    assert cwl_obj.inputs[0].id.endswith("input_file")


def test_load_document_with_local_uri() -> None:
    """Test load_document for a CommandLineTool in a local URI."""
    uri = Path(TEST_v1_0_CWL).resolve().as_uri()
    assert uri.startswith("file://")
    cwl_obj = load_document_by_uri(uri)
    assert cwl_obj.cwlVersion == "v1.0"
    assert cwl_obj.inputs[0].id.endswith("input_file")


def test_load_document_with_remote_uri() -> None:
    """Test load_document for a CommandLineTool in a remote URI."""
    cwl_obj = load_document_by_uri(TEST_v1_0_CWL_REMOTE)
    assert cwl_obj.cwlVersion == "v1.0"
    assert cwl_obj.inputs[0].id.endswith("input_file")


def test_save() -> None:
    """Test save for a list of Process objects with different cwlVersions."""
    with open(TEST_v1_0_CWL) as cwl_h:
        yaml_obj10 = yaml.main.round_trip_load(cwl_h, preserve_quotes=True)
    cwl_obj10 = load_document(yaml_obj10)
    assert cwl_obj10.cwlVersion == "v1.0"

    with open(TEST_v1_2_CWL) as cwl_h:
        yaml_obj12 = yaml.main.round_trip_load(cwl_h, preserve_quotes=True)
    cwl_obj12 = load_document(yaml_obj12)
    assert cwl_obj12.cwlVersion == "v1.2"

    saved_obj = save([cwl_obj10, cwl_obj12])
    ver = cwl_version(saved_obj)
    assert ver == "v1.2"


def test_latest_parser() -> None:
    """Test the `latest` parser is same as cwl_v1_2 (current latest) parser."""
    uri = Path(TEST_v1_2_CWL).as_uri()
    with open(TEST_v1_2_CWL) as cwl_h:
        yaml_obj12 = yaml.main.round_trip_load(cwl_h, preserve_quotes=True)
    latest_cwl_obj = latest.load_document_by_yaml(yaml_obj12, uri)  # type: ignore
    assert latest_cwl_obj.cwlVersion == "v1.2"


def test_shortname() -> None:
    assert cwl_v1_2.shortname("http://example.com/foo") == "foo"
    assert cwl_v1_2.shortname("http://example.com/#bar") == "bar"
    assert cwl_v1_2.shortname("http://example.com/foo/bar") == "bar"
    assert cwl_v1_2.shortname("http://example.com/foo#bar") == "bar"
    assert cwl_v1_2.shortname("http://example.com/#foo/bar") == "bar"
    assert cwl_v1_2.shortname("http://example.com/foo#bar/baz") == "baz"

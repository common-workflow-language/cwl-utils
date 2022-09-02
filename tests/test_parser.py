# SPDX-License-Identifier: Apache-2.0
"""Test the load and save functions for CWL."""
from pathlib import Path

from pytest import raises
from ruamel.yaml.main import YAML

import cwl_utils.parser.latest as latest
from cwl_utils.errors import GraphTargetMissingException
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
yaml = YAML(typ="rt")
yaml.preserve_quotes = True  # type: ignore[assignment]


def test_cwl_version() -> None:
    """Test cwl_version for a CommandLineTool."""
    with open(TEST_v1_0_CWL) as cwl_h:
        yaml_obj = yaml.load(cwl_h)
    ver = cwl_version(yaml_obj)
    assert ver == "v1.0"


def test_load_document() -> None:
    """Test load_document for a CommandLineTool."""
    with open(TEST_v1_0_CWL) as cwl_h:
        yaml_obj = yaml.load(cwl_h)
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
        yaml_obj10 = yaml.load(cwl_h)
    cwl_obj10 = load_document(yaml_obj10)
    assert cwl_obj10.cwlVersion == "v1.0"

    with open(TEST_v1_2_CWL) as cwl_h:
        yaml_obj12 = yaml.load(cwl_h)
    cwl_obj12 = load_document(yaml_obj12)
    assert cwl_obj12.cwlVersion == "v1.2"

    saved_obj = save([cwl_obj10, cwl_obj12])
    ver = cwl_version(saved_obj)
    assert ver == "v1.2"


def test_latest_parser() -> None:
    """Test the `latest` parser is same as cwl_v1_2 (current latest) parser."""
    uri = Path(TEST_v1_2_CWL).as_uri()
    with open(TEST_v1_2_CWL) as cwl_h:
        yaml_obj12 = yaml.load(cwl_h)
    latest_cwl_obj = latest.load_document_by_yaml(yaml_obj12, uri)
    assert latest_cwl_obj.cwlVersion == "v1.2"


def test_shortname() -> None:
    assert cwl_v1_2.shortname("http://example.com/foo") == "foo"
    assert cwl_v1_2.shortname("http://example.com/#bar") == "bar"
    assert cwl_v1_2.shortname("http://example.com/foo/bar") == "bar"
    assert cwl_v1_2.shortname("http://example.com/foo#bar") == "bar"
    assert cwl_v1_2.shortname("http://example.com/#foo/bar") == "bar"
    assert cwl_v1_2.shortname("http://example.com/foo#bar/baz") == "baz"


def test_get_id_from_graph() -> None:
    """Test loading an explicit id of a CWL document with $graph property."""
    uri = Path(HERE / "../testdata/echo-tool-packed.cwl").resolve().as_uri()
    cwl_obj = load_document_by_uri(uri + "#main")
    assert cwl_obj.id == uri + "#main"


def test_get_default_id_from_graph() -> None:
    """Test that loading the default id of a CWL document with $graph property returns the `#main` id."""
    uri = Path(HERE / "../testdata/echo-tool-packed.cwl").resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    assert cwl_obj.id == uri + "#main"


def test_get_default_id_from_graph_without_main() -> None:
    """Test that loading the default id of a CWL document with $graph property and no `#main` id throws an error."""
    with raises(GraphTargetMissingException):
        uri = Path(HERE / "../testdata/js-expr-req-wf.cwl").resolve().as_uri()
        load_document_by_uri(uri)

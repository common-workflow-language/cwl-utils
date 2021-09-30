"""Test the load and save functions for CWL."""
from cwl_utils.parser import cwl_version, load_document, save
from pathlib import Path
from ruamel import yaml

HERE = Path(__file__).resolve().parent
TEST_v1_0_CWL = HERE / "../testdata/md5sum.cwl"
TEST_v1_2_CWL = HERE / "../testdata/workflow_input_format_expr_v1_2.cwl"


def test_cwl_version() -> None:
    """Test cwl_version for a CommandLineTool."""
    with open(TEST_v1_0_CWL, "r") as cwl_h:
        yaml_obj = yaml.main.round_trip_load(cwl_h, preserve_quotes=True)
    ver = cwl_version(yaml_obj)
    assert ver == "v1.0"


def test_load_document() -> None:
    """Test load_document for a CommandLineTool."""
    with open(TEST_v1_0_CWL, "r") as cwl_h:
        yaml_obj = yaml.main.round_trip_load(cwl_h, preserve_quotes=True)
    cwl_obj = load_document(yaml_obj)
    assert cwl_obj.cwlVersion == "v1.0"
    assert cwl_obj.inputs[0].id.endswith("input_file")


def test_save() -> None:
    """Test save for a list of Process objects with different cwlVersions."""
    with open(TEST_v1_0_CWL, "r") as cwl_h:
        yaml_obj10 = yaml.main.round_trip_load(cwl_h, preserve_quotes=True)
    cwl_obj10 = load_document(yaml_obj10)
    assert cwl_obj10.cwlVersion == "v1.0"

    with open(TEST_v1_2_CWL, "r") as cwl_h:
        yaml_obj12 = yaml.main.round_trip_load(cwl_h, preserve_quotes=True)
    cwl_obj12 = load_document(yaml_obj12)
    assert cwl_obj12.cwlVersion == "v1.2"

    saved_obj = save([cwl_obj10, cwl_obj12])
    ver = cwl_version(saved_obj)
    assert ver == "v1.2"

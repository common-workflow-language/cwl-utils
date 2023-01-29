from pathlib import Path

import pytest
from ruamel import yaml
from schema_salad.exceptions import ValidationException

from cwl_utils.parser import load_document, load_document_by_uri
from cwl_utils.parser.utils import static_checker
from .util import get_data


def test_static_checker() -> None:
    """Confirm that static type checker raises expected exception."""
    with pytest.raises(ValidationException):
        uri = Path(get_data("testdata/checker_wf/broken-wf.cwl")).resolve().as_uri()
        cwl_obj = load_document_by_uri(uri)
        static_checker(cwl_obj)

    with pytest.raises(ValidationException):
        with open(get_data("testdata/checker_wf/broken-wf2.cwl")) as cwl_h:
            yaml_obj = yaml.load(cwl_h)
        cwl_obj = load_document(yaml_obj)
        static_checker(cwl_obj)

    with pytest.raises(ValidationException):
        with open(get_data("testdata/checker_wf/broken-wf3.cwl")) as cwl_h:
            yaml_obj = yaml.load(cwl_h)
        cwl_obj = load_document(yaml_obj)
        static_checker(cwl_obj)

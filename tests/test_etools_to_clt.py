"""Test the CWL Expression refactoring tool."""
import os
import shutil
import tarfile
from pathlib import Path
from typing import Generator

import pytest
import requests
from _pytest.tmpdir import TempPathFactory
from cwltool.errors import WorkflowException
from pytest import raises

import cwl_utils.parser_v1_0 as parser
import cwl_utils.parser_v1_1 as parser1
import cwl_utils.parser_v1_2 as parser2
from cwl_utils.cwl_v1_0_expression_refactor import traverse as traverse0
from cwl_utils.cwl_v1_1_expression_refactor import traverse as traverse1
from cwl_utils.cwl_v1_2_expression_refactor import traverse as traverse2

HERE = Path(__file__).resolve().parent


def test_v1_0_workflow_top_level_format_expr() -> None:
    """Test for the correct error when converting a format expression in a workflow level input."""
    with raises(WorkflowException, match=r".*format specification.*"):
        result, modified = traverse0(
            parser.load_document(
                str(HERE / "../testdata/workflow_input_format_expr.cwl")
            ),
            False,
            False,
            False,
            False,
        )


def test_v1_0_workflow_top_level_sf_expr() -> None:
    """Test for the correct error when converting a secondaryFiles expression in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse0(
            parser.load_document(str(HERE / "../testdata/workflow_input_sf_expr.cwl")),
            False,
            False,
            False,
            False,
        )


def test_v1_0_workflow_top_level_sf_expr_array() -> None:
    """Test for the correct error when converting a secondaryFiles expression (array form) in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse0(
            parser.load_document(
                str(HERE / "../testdata/workflow_input_sf_expr_array.cwl")
            ),
            False,
            False,
            False,
            False,
        )


def test_v1_1_workflow_top_level_format_expr() -> None:
    """Test for the correct error when converting a format expression in a workflow level input."""
    # import ipdb; ipdb.set_trace()
    with raises(WorkflowException, match=r".*format specification.*"):
        result, modified = traverse1(
            parser1.load_document(
                str(HERE / "../testdata/workflow_input_format_expr_v1_1.cwl")
            ),
            False,
            False,
            False,
            False,
        )


def test_v1_1_workflow_top_level_sf_expr() -> None:
    """Test for the correct error when converting a secondaryFiles expression in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse1(
            parser1.load_document(
                str(HERE / "../testdata/workflow_input_sf_expr_v1_1.cwl")
            ),
            False,
            False,
            False,
            False,
        )


def test_v1_1_workflow_top_level_sf_expr_array() -> None:
    """Test for the correct error when converting a secondaryFiles expression (array form) in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse1(
            parser1.load_document(
                str(HERE / "../testdata/workflow_input_sf_expr_array_v1_1.cwl")
            ),
            False,
            False,
            False,
            False,
        )


def test_v1_2_workflow_top_level_format_expr() -> None:
    """Test for the correct error when converting a format expression in a workflow level input."""
    with raises(WorkflowException, match=r".*format specification.*"):
        result, modified = traverse2(
            parser2.load_document(
                str(HERE / "../testdata/workflow_input_format_expr_v1_2.cwl")
            ),
            False,
            False,
            False,
            False,
        )


def test_v1_2_workflow_top_level_sf_expr() -> None:
    """Test for the correct error when converting a secondaryFiles expression in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse2(
            parser2.load_document(
                str(HERE / "../testdata/workflow_input_sf_expr_v1_2.cwl")
            ),
            False,
            False,
            False,
            False,
        )


def test_v1_2_workflow_top_level_sf_expr_array() -> None:
    """Test for the correct error when converting a secondaryFiles expression (array form) in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse2(
            parser2.load_document(
                str(HERE / "../testdata/workflow_input_sf_expr_array_v1_2.cwl")
            ),
            False,
            False,
            False,
            False,
        )


@pytest.fixture(scope="session")
def cwl_v1_0_dir(
    tmp_path_factory: TempPathFactory,
) -> Generator[str, None, None]:
    """Download the CWL 1.0.2 specs and return a path to the directory."""
    tmp_path = tmp_path_factory.mktemp("cwl_v1_0_dir")
    with requests.get(
        "https://github.com/common-workflow-language/common-workflow-language/archive/v1.0.2.tar.gz",
        stream=True,
    ).raw as specfileobj:
        tf = tarfile.open(fileobj=specfileobj)
        tf.extractall(path=tmp_path)
    yield str(tmp_path / "common-workflow-language-1.0.2")
    shutil.rmtree(os.path.join(tmp_path))

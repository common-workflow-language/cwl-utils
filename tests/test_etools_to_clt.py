"""Test the CWL Expression refactoring tool."""
from pathlib import Path

from cwltool.errors import WorkflowException
from pytest import raises

import cwl_utils.parser_v1_0 as parser
from cwl_utils.cwl_expression_refactor import traverse

HERE = Path(__file__).resolve().parent


def test_workflow_top_level_format_expr(tmp_path: Path) -> None:
    """Test for the correct error when converting a format expression in a workflow level input."""
    with raises(WorkflowException, match=r".*format specification.*"):
        result, modified = traverse(
            parser.load_document(
                str(HERE / "../testdata/workflow_input_format_expr.cwl")
            )
        )


def test_workflow_top_level_sf_expr(tmp_path: Path) -> None:
    """Test for the correct error when converting a secondaryFiles expression in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse(
            parser.load_document(str(HERE / "../testdata/workflow_input_sf_expr.cwl"))
        )


def test_workflow_top_level_sf_expr_array(tmp_path: Path) -> None:
    """Test for the correct error when converting a secondaryFiles expression (array form) in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse(
            parser.load_document(
                str(HERE / "../testdata/workflow_input_sf_expr_array.cwl")
            )
        )

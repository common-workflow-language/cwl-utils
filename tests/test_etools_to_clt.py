"""Test the CWL Expression refactoring tool."""
from cwltool.errors import WorkflowException
from pytest import raises
from pathlib import Path

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
            )
        )


def test_v1_0_workflow_top_level_sf_expr() -> None:
    """Test for the correct error when converting a secondaryFiles expression in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse0(
            parser.load_document(str(HERE / "../testdata/workflow_input_sf_expr.cwl"))
        )


def test_v1_0_workflow_top_level_sf_expr_array() -> None:
    """Test for the correct error when converting a secondaryFiles expression (array form) in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse0(
            parser.load_document(
                str(HERE / "../testdata/workflow_input_sf_expr_array.cwl")
            )
        )


def test_v1_1_workflow_top_level_format_expr() -> None:
    """Test for the correct error when converting a format expression in a workflow level input."""
    # import ipdb; ipdb.set_trace()
    with raises(WorkflowException, match=r".*format specification.*"):
        result, modified = traverse1(
            parser1.load_document(
                str(HERE / "../testdata/workflow_input_format_expr_v1_1.cwl")
            )
        )


def test_v1_1_workflow_top_level_sf_expr() -> None:
    """Test for the correct error when converting a secondaryFiles expression in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse1(
            parser1.load_document(
                str(HERE / "../testdata/workflow_input_sf_expr_v1_1.cwl")
            )
        )


def test_v1_1_workflow_top_level_sf_expr_array() -> None:
    """Test for the correct error when converting a secondaryFiles expression (array form) in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse1(
            parser1.load_document(
                str(HERE / "../testdata/workflow_input_sf_expr_array_v1_1.cwl")
            )
        )


def test_v1_2_workflow_top_level_format_expr() -> None:
    """Test for the correct error when converting a format expression in a workflow level input."""
    with raises(WorkflowException, match=r".*format specification.*"):
        result, modified = traverse2(
            parser2.load_document(
                str(HERE / "../testdata/workflow_input_format_expr_v1_2.cwl")
            )
        )


def test_v1_2_workflow_top_level_sf_expr() -> None:
    """Test for the correct error when converting a secondaryFiles expression in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse2(
            parser2.load_document(
                str(HERE / "../testdata/workflow_input_sf_expr_v1_2.cwl")
            )
        )


def test_v1_2_workflow_top_level_sf_expr_array() -> None:
    """Test for the correct error when converting a secondaryFiles expression (array form) in a workflow level input."""
    with raises(WorkflowException, match=r".*secondaryFiles.*"):
        result, modified = traverse2(
            parser2.load_document(
                str(HERE / "../testdata/workflow_input_sf_expr_array_v1_2.cwl")
            )
        )

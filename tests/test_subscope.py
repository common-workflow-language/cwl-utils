# SPDX-License-Identifier: Apache-2.0
"""Test that scoping of identifiers in Workflow.steps[].run is correct."""

from pathlib import Path

from cwl_utils.parser import Workflow, load_document_by_uri

from .util import get_data


def test_workflow_step_process_scope_v1_0() -> None:
    """CWL v1.0 IDs under Workflow.steps[].run should not be scoped in the "run" scope."""
    uri = Path(get_data("testdata/workflow_input_format_expr.cwl")).resolve().as_uri()
    cwl_obj: Workflow = load_document_by_uri(uri)
    assert cwl_obj.steps[0].run.inputs[0].id.endswith("#format_extract/target")


def test_workflow_step_process_scope_v1_1() -> None:
    """CWL v1.1 IDs under Workflow.steps[].run should be scoped in the "run" scope."""
    uri = (
        Path(get_data("testdata/workflow_input_format_expr_v1_1.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj: Workflow = load_document_by_uri(uri)
    assert cwl_obj.steps[0].run.inputs[0].id.endswith("#format_extract/run/target")


def test_workflow_step_process_scope_v1_2() -> None:
    """CWL v1.2 IDs under Workflow.steps[].run should be scoped in the "run" scope."""
    uri = (
        Path(get_data("testdata/workflow_input_format_expr_v1_2.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj: Workflow = load_document_by_uri(uri)
    assert cwl_obj.steps[0].run.inputs[0].id.endswith("#format_extract/run/target")

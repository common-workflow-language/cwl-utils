# SPDX-License-Identifier: Apache-2.0
"""Test the CWL parsers utility functions."""
import tempfile
from pathlib import Path
from typing import MutableSequence, cast

import pytest
from pytest import raises
from schema_salad.exceptions import ValidationException

import cwl_utils.parser.cwl_v1_0
import cwl_utils.parser.cwl_v1_0_utils
import cwl_utils.parser.cwl_v1_1
import cwl_utils.parser.cwl_v1_1_utils
import cwl_utils.parser.cwl_v1_2
import cwl_utils.parser.cwl_v1_2_utils
import cwl_utils.parser.utils
from cwl_utils.errors import WorkflowException
from cwl_utils.parser import load_document_by_uri

from .util import get_data


@pytest.mark.parametrize("cwlVersion", ["v1_0", "v1_1", "v1_2"])
def test_static_checker_fail(cwlVersion: str) -> None:
    """Confirm that static type checker raises expected exception."""
    if cwlVersion == "v1_0":
        uri = Path(get_data("testdata/checker_wf/broken-wf.cwl")).resolve().as_uri()
        cwl_obj = load_document_by_uri(uri)
        with pytest.raises(
            ValidationException,
            match="\nSource .* of type .* is incompatible\n.*with sink .* of type .*",
        ):
            cwl_utils.parser.utils.static_checker(cwl_obj)

        uri = Path(get_data("testdata/checker_wf/broken-wf2.cwl")).resolve().as_uri()
        cwl_obj = load_document_by_uri(uri)
        with pytest.raises(
            ValidationException, match="param .* not found in class: CommandLineTool"
        ):
            cwl_utils.parser.utils.static_checker(cwl_obj)

        uri = Path(get_data("testdata/checker_wf/broken-wf3.cwl")).resolve().as_uri()
        cwl_obj = load_document_by_uri(uri)
        with pytest.raises(
            ValidationException, match="param .* not found in class: Workflow"
        ):
            cwl_utils.parser.utils.static_checker(cwl_obj)

    uri = (
        Path(get_data(f"testdata/count-lines6-wf_{cwlVersion}.cwl")).resolve().as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    with pytest.raises(
        ValidationException,
        match="\nSource .* of type .* is incompatible\n.*with sink .* of type .*",
    ):
        cwl_utils.parser.utils.static_checker(cwl_obj)

    uri = (
        Path(get_data(f"testdata/count-lines6-single-source-wf_{cwlVersion}.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    with pytest.raises(
        ValidationException,
        match="\nSource .* of type .* is incompatible\n.*with sink .* of type .*",
    ):
        cwl_utils.parser.utils.static_checker(cwl_obj)

    if cwlVersion == "v1_2":
        uri = (
            Path(get_data("testdata/cond-single-source-wf-003.1.cwl"))
            .resolve()
            .as_uri()
        )
        cwl_obj = load_document_by_uri(uri)
        with pytest.raises(ValidationException, match=".* pickValue is first_non_null"):
            cwl_utils.parser.utils.static_checker(cwl_obj)

    uri = Path(get_data("testdata/cond-single-source-wf-004.1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    with pytest.raises(ValidationException, match=".* pickValue is the_only_non_null"):
        cwl_utils.parser.utils.static_checker(cwl_obj)


@pytest.mark.parametrize("cwlVersion", ["v1_0", "v1_1", "v1_2"])
def test_static_checker_success(cwlVersion: str) -> None:
    """Confirm that static type checker correctly validates workflows."""
    test_files = [
        f"testdata/record-output-wf_{cwlVersion}.cwl",
        f"testdata/step_valuefrom5_wf_{cwlVersion}.cwl",
        f"testdata/step_valuefrom5_wf_with_id_{cwlVersion}.cwl",
        f"testdata/stdout-wf_{cwlVersion}.cwl",
        f"testdata/scatter-wf1_{cwlVersion}.cwl",
        f"testdata/scatter-wf2_{cwlVersion}.cwl",
        f"testdata/scatter-wf3_{cwlVersion}.cwl",
        f"testdata/count-lines7-wf_{cwlVersion}.cwl",
        f"testdata/count-lines7-single-source-wf_{cwlVersion}.cwl",
    ]
    if cwlVersion == "v1_2":
        test_files.extend(
            [
                "testdata/cond-wf-003.1.cwl",
                "testdata/cond-wf-004.1.cwl",
                "testdata/cond-wf-005.1.cwl",
                "testdata/cond-single-source-wf-005.1.cwl",
            ]
        )
    for test_file in test_files:
        uri = Path(get_data(test_file)).resolve().as_uri()
        cwl_obj = load_document_by_uri(uri)
        cwl_utils.parser.utils.static_checker(cwl_obj)


def test_v1_0_file_content_64_kB() -> None:
    """Test that reading file content is allowed up to 64kB in CWL v1.0."""
    text = "a" * cwl_utils.parser.cwl_v1_0_utils.CONTENT_LIMIT
    with tempfile.TemporaryFile() as f:
        f.write(text.encode("utf-8"))
        f.seek(0)
        content = cwl_utils.parser.cwl_v1_0_utils.content_limit_respected_read(f)
    assert content == text


def test_v1_0_file_content_larger_than_64_kB() -> None:
    """Test that reading file content is truncated to 64kB for larger files in CWL v1.0."""
    text = "a" * (cwl_utils.parser.cwl_v1_0_utils.CONTENT_LIMIT + 1)
    with tempfile.TemporaryFile() as f:
        f.write(text.encode("utf-8"))
        f.seek(0)
        content = cwl_utils.parser.cwl_v1_0_utils.content_limit_respected_read(f)
    assert content == text[0 : cwl_utils.parser.cwl_v1_0_utils.CONTENT_LIMIT]


def test_v1_0_stdout_to_file() -> None:
    """Test that stdout shortcut is converted to stdout parameter with CWL v1.0."""
    clt = cwl_utils.parser.cwl_v1_0.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_0.CommandOutputParameter(id="test", type_="stdout")
        ],
    )
    cwl_utils.parser.cwl_v1_0_utils.convert_stdstreams_to_files(clt)
    assert clt.stdout is not None
    assert clt.stdout == clt.outputs[0].outputBinding.glob


def test_v1_0_stdout_to_file_with_binding() -> None:
    """Test that outputBinding is not allowed with stdout shortcut with CWL v1.0."""
    clt = cwl_utils.parser.cwl_v1_0.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_0.CommandOutputParameter(
                id="test",
                type_="stdout",
                outputBinding=cwl_utils.parser.cwl_v1_0.CommandOutputBinding(
                    glob="output.txt"
                ),
            )
        ],
    )
    with raises(ValidationException):
        cwl_utils.parser.cwl_v1_0_utils.convert_stdstreams_to_files(clt)


def test_v1_0_stdout_to_file_preserve_original() -> None:
    """Test that stdout parameter prevails on stdout shortcut with CWL v1.0."""
    clt = cwl_utils.parser.cwl_v1_0.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_0.CommandOutputParameter(id="test", type_="stdout")
        ],
        stdout="original.txt",
    )
    cwl_utils.parser.cwl_v1_0_utils.convert_stdstreams_to_files(clt)
    assert clt.stdout == "original.txt"
    assert clt.stdout == clt.outputs[0].outputBinding.glob


def test_v1_0_stderr_to_file() -> None:
    """Test that stderr shortcut is converted to stderr parameter with CWL v1.0."""
    clt = cwl_utils.parser.cwl_v1_0.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_0.CommandOutputParameter(id="test", type_="stderr")
        ],
    )
    cwl_utils.parser.cwl_v1_0_utils.convert_stdstreams_to_files(clt)
    assert clt.stderr is not None
    assert clt.stderr == clt.outputs[0].outputBinding.glob


def test_v1_0_stderr_to_file_with_binding() -> None:
    """Test that outputBinding is not allowed with stderr shortcut with CWL v1.0."""
    clt = cwl_utils.parser.cwl_v1_0.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_0.CommandOutputParameter(
                id="test",
                type_="stderr",
                outputBinding=cwl_utils.parser.cwl_v1_0.CommandOutputBinding(
                    glob="err.txt"
                ),
            )
        ],
    )
    with raises(ValidationException):
        cwl_utils.parser.cwl_v1_0_utils.convert_stdstreams_to_files(clt)


def test_v1_0_stderr_to_file_preserve_original() -> None:
    """Test that stderr parameter prevails on stdout shortcut with CWL v1.0."""
    clt = cwl_utils.parser.cwl_v1_0.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_0.CommandOutputParameter(id="test", type_="stderr")
        ],
        stderr="original.txt",
    )
    cwl_utils.parser.cwl_v1_0_utils.convert_stdstreams_to_files(clt)
    assert clt.stderr == "original.txt"
    assert clt.stderr == clt.outputs[0].outputBinding.glob


def test_v1_0_type_compare_list() -> None:
    """Test that the type comparison works correctly a list type with CWL v1.0."""
    uri = Path(get_data("testdata/echo_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    assert cwl_utils.parser.cwl_v1_0_utils._compare_type(
        cwl_obj.inputs[0].type_, cwl_obj.inputs[0].type_
    )


def test_v1_0_type_compare_record() -> None:
    """Test that the type comparison works correctly a record type with CWL v1.0."""
    uri = Path(get_data("testdata/record-output-wf_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert cwl_utils.parser.cwl_v1_0_utils._compare_type(source_type, source_type)


def test_v1_0_type_for_source() -> None:
    """Test that the type is correctly inferred from a source id with CWL v1.0."""
    uri = Path(get_data("testdata/step_valuefrom5_wf_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        cwl_obj, cwl_obj.loadingOptions.fileuri + "#step1/echo_out_file"
    )
    assert source_type == "File"


def test_v1_0_type_for_source_with_id() -> None:
    """Test that the type is correctly inferred from a source id with CWL v1.0."""
    uri = (
        Path(get_data("testdata/step_valuefrom5_wf_with_id_v1_0.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        cwl_obj, cwl_obj.loadingOptions.fileuri + "#step1/echo_out_file"
    )
    assert source_type == "File"


def test_v1_0_type_for_stdout() -> None:
    """Test that the `stdout` type is correctly matched with the `File` type in CWL v1.0."""
    uri = Path(get_data("testdata/stdout-wf_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        cwl_obj, cwl_obj.outputs[0].outputSource
    )
    assert source_type == "File"


def test_v1_0_type_output_source_record() -> None:
    """Test that the type is correctly inferred from a record output source with CWL v1.0."""
    uri = Path(get_data("testdata/record-output-wf_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_0.RecordSchema)
    fields = cast(
        MutableSequence[cwl_utils.parser.cwl_v1_0.RecordField], source_type.fields
    )
    assert len(fields) == 2
    assert fields[0].type_ == "File"
    assert fields[1].type_ == "File"


def test_v1_0_type_for_output_source_with_single_scatter_step() -> None:
    """Test that the type is correctly inferred from a single scatter step with CWL v1.0."""
    uri = Path(get_data("testdata/scatter-wf1_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert source_type.items == "string"


def test_v1_0_type_for_output_source_with_nested_crossproduct_scatter_step() -> None:
    """Test that the type is correctly inferred from a nested_crossproduct scatter step with CWL v1.0."""
    uri = Path(get_data("testdata/scatter-wf2_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert isinstance(source_type.items, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert source_type.items.items == "string"


def test_v1_0_type_for_output_source_with_flat_crossproduct_scatter_step() -> None:
    """Test that the type is correctly inferred from a flat_crossproduct scatter step with CWL v1.0."""
    uri = Path(get_data("testdata/scatter-wf3_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj, sourcenames=cwl_obj.outputs[0].outputSource
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert source_type.items == "string"


def test_v1_0_type_for_source_with_multiple_entries_merge_nested() -> None:
    """Test that the type is correctly inferred from a list of source ids and merge_nested with CWL v1.0."""
    uri = Path(get_data("testdata/count-lines6-wf_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert isinstance(source_type.items, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert source_type.items.items == "File"


def test_v1_0_type_for_source_with_multiple_entries_merge_flattened() -> None:
    """Test that the type is correctly inferred from a list of source ids and merge_flattened with CWL v1.0."""  # noqa: B950
    uri = Path(get_data("testdata/count-lines7-wf_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert source_type.items == "File"


def test_v1_0_type_for_source_with_single_entry_merge_nested() -> None:
    """Test that the type is correctly inferred from a single source id and merge_nested with CWL v1.0."""
    uri = (
        Path(get_data("testdata/count-lines6-single-source-wf_v1_0.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert isinstance(source_type.items, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert source_type.items.items == "File"


def test_v1_0_type_for_source_with_single_entry_merge_flattened() -> None:
    """Test that the type is correctly inferred from a single source id and merge_flattened with CWL v1.0."""
    uri = (
        Path(get_data("testdata/count-lines7-single-source-wf_v1_0.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert source_type.items == "File"


def test_v1_1_file_content_64_kB() -> None:
    """Test that reading file content is allowed up to 64kB in CWL v1.1."""
    text = "a" * cwl_utils.parser.cwl_v1_1_utils.CONTENT_LIMIT
    with tempfile.TemporaryFile() as f:
        f.write(text.encode("utf-8"))
        f.seek(0)
        content = cwl_utils.parser.cwl_v1_1_utils.content_limit_respected_read(f)
    assert content == text


def test_v1_1_file_content_larger_than_64_kB() -> None:
    """Test that reading file content is truncated to 64kB for larger files in CWL v1.1."""
    text = "a" * (cwl_utils.parser.cwl_v1_1_utils.CONTENT_LIMIT + 1)
    with tempfile.TemporaryFile() as f:
        f.write(text.encode("utf-8"))
        f.seek(0)
        content = cwl_utils.parser.cwl_v1_1_utils.content_limit_respected_read(f)
    assert content == text[0 : cwl_utils.parser.cwl_v1_1_utils.CONTENT_LIMIT]


def test_v1_1_stdout_to_file() -> None:
    """Test that stdout shortcut is converted to stdout parameter with CWL v1.1."""
    clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_1.CommandOutputParameter(id="test", type_="stdout")
        ],
    )
    cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)
    assert clt.stdout is not None
    assert clt.stdout == clt.outputs[0].outputBinding.glob


def test_v1_1_stdout_to_file_with_binding() -> None:
    """Test that outputBinding is not allowed with stdout shortcut with CWL v1.1."""
    clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_1.CommandOutputParameter(
                id="test",
                type_="stdout",
                outputBinding=cwl_utils.parser.cwl_v1_1.CommandOutputBinding(
                    glob="output.txt"
                ),
            )
        ],
    )
    with raises(ValidationException):
        cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)


def test_v1_1_stdout_to_file_preserve_original() -> None:
    """Test that stdout parameter prevails on stdout shortcut with CWL v1.1."""
    clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_1.CommandOutputParameter(id="test", type_="stdout")
        ],
        stdout="original.txt",
    )
    cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)
    assert clt.stdout == "original.txt"
    assert clt.stdout == clt.outputs[0].outputBinding.glob


def test_v1_1_stderr_to_file() -> None:
    """Test that stderr shortcut is converted to stderr parameter with CWL v1.1."""
    clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_1.CommandOutputParameter(id="test", type_="stderr")
        ],
    )
    cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)
    assert clt.stderr is not None
    assert clt.stderr == clt.outputs[0].outputBinding.glob


def test_v1_1_stderr_to_file_with_binding() -> None:
    """Test that outputBinding is not allowed with stderr shortcut with CWL v1.1."""
    clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_1.CommandOutputParameter(
                id="test",
                type_="stderr",
                outputBinding=cwl_utils.parser.cwl_v1_1.CommandOutputBinding(
                    glob="err.txt"
                ),
            )
        ],
    )
    with raises(ValidationException):
        cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)


def test_v1_1_stderr_to_file_preserve_original() -> None:
    """Test that stderr parameter prevails on stdout shortcut with CWL v1.1."""
    clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_1.CommandOutputParameter(id="test", type_="stderr")
        ],
        stderr="original.txt",
    )
    cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)
    assert clt.stderr == "original.txt"
    assert clt.stderr == clt.outputs[0].outputBinding.glob


def test_v1_1_stdin_to_file() -> None:
    """Test that stdin shortcut is converted to stdin parameter with CWL v1.1."""
    clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
        inputs=[
            cwl_utils.parser.cwl_v1_1.CommandInputParameter(id="test", type_="stdin")
        ],
        outputs=[],
    )
    cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)
    assert clt.stdin is not None


def test_v1_1_stdin_to_file_with_binding() -> None:
    """Test that inputBinding is not allowed with stdin shortcut with CWL v1.1."""
    clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
        inputs=[
            cwl_utils.parser.cwl_v1_1.CommandInputParameter(
                id="test",
                type_="stdin",
                inputBinding=cwl_utils.parser.cwl_v1_1.CommandLineBinding(
                    prefix="--test"
                ),
            )
        ],
        outputs=[],
    )
    with raises(ValidationException):
        cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)


def test_v1_1_stdin_to_file_fail_with_original() -> None:
    """Test that stdin shortcut fails when stdin parameter is defined with CWL v1.1."""
    clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
        inputs=[
            cwl_utils.parser.cwl_v1_1.CommandInputParameter(id="test", type_="stdin")
        ],
        outputs=[],
        stdin="original.txt",
    )
    with raises(ValidationException):
        cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)


def test_v1_1_type_compare_list() -> None:
    """Test that the type comparison works correctly a list type with CWL v1.1."""
    uri = Path(get_data("testdata/echo_v1_1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    assert cwl_utils.parser.cwl_v1_1_utils._compare_type(
        cwl_obj.inputs[0].type_, cwl_obj.inputs[0].type_
    )


def test_v1_1_type_compare_record() -> None:
    """Test that the type comparison works correctly a record type with CWL v1.1."""
    uri = Path(get_data("testdata/record-output-wf_v1_1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert cwl_utils.parser.cwl_v1_1_utils._compare_type(source_type, source_type)


def test_v1_1_type_for_source() -> None:
    """Test that the type is correctly inferred from a source id with CWL v1.1."""
    uri = Path(get_data("testdata/step_valuefrom5_wf_v1_1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        cwl_obj, cwl_obj.loadingOptions.fileuri + "#step1/echo_out_file"
    )
    assert source_type == "File"


def test_v1_1_type_for_source_with_id() -> None:
    """Test that the type is correctly inferred from a source id with CWL v1.1."""
    uri = (
        Path(get_data("testdata/step_valuefrom5_wf_with_id_v1_1.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        cwl_obj, cwl_obj.loadingOptions.fileuri + "#step1/echo_out_file"
    )
    assert source_type == "File"


def test_v1_1_type_for_stdout() -> None:
    """Test that the `stdout` type is correctly matched with the `File` type in CWL v1.1."""
    uri = Path(get_data("testdata/stdout-wf_v1_1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        cwl_obj, cwl_obj.outputs[0].outputSource
    )
    assert source_type == "File"


def test_v1_1_type_output_source_record() -> None:
    """Test that the type is correctly inferred from a record output source with CWL v1.1."""
    uri = Path(get_data("testdata/record-output-wf_v1_1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_1.RecordSchema)
    fields = cast(
        MutableSequence[cwl_utils.parser.cwl_v1_1.RecordField], source_type.fields
    )
    assert len(fields) == 2
    assert fields[0].type_ == "File"
    assert fields[1].type_ == "File"


def test_v1_1_type_for_output_source_with_single_scatter_step() -> None:
    """Test that the type is correctly inferred from a single scatter step with CWL v1.1."""
    uri = Path(get_data("testdata/scatter-wf1_v1_1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert source_type.items == "string"


def test_v1_1_type_for_output_source_with_nested_crossproduct_scatter_step() -> None:
    """Test that the type is correctly inferred from a nested_crossproduct scatter step with CWL v1.1."""
    uri = Path(get_data("testdata/scatter-wf2_v1_1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert isinstance(source_type.items, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert source_type.items.items == "string"


def test_v1_1_type_for_output_source_with_flat_crossproduct_scatter_step() -> None:
    """Test that the type is correctly inferred from a flat_crossproduct scatter step with CWL v1.1."""
    uri = Path(get_data("testdata/scatter-wf3_v1_1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert source_type.items == "string"


def test_v1_1_type_for_source_with_multiple_entries_merge_nested() -> None:
    """Test that the type is correctly inferred from a list of source ids and merge_nested with CWL v1.1."""
    uri = Path(get_data("testdata/count-lines6-wf_v1_1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert isinstance(source_type.items, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert source_type.items.items == "File"


def test_v1_1_type_for_source_with_multiple_entries_merge_flattened() -> None:
    """Test that the type is correctly inferred from a list of source ids and merge_flattened with CWL v1.1."""  # noqa: B950
    uri = Path(get_data("testdata/count-lines7-wf_v1_1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert source_type.items == "File"


def test_v1_1_type_for_source_with_single_entry_merge_nested() -> None:
    """Test that the type is correctly inferred from a single source id and merge_nested with CWL v1.1."""
    uri = (
        Path(get_data("testdata/count-lines6-single-source-wf_v1_1.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert isinstance(source_type.items, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert source_type.items.items == "File"


def test_v1_1_type_for_source_with_single_entry_merge_flattened() -> None:
    """Test that the type is correctly inferred from a single source id and merge_flattened with CWL v1.1."""
    uri = (
        Path(get_data("testdata/count-lines7-single-source-wf_v1_1.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert source_type.items == "File"


def test_v1_2_file_content_64_kB() -> None:
    """Test that reading file content is allowed up to 64kB in CWL v1.2."""
    text = "a" * cwl_utils.parser.cwl_v1_2_utils.CONTENT_LIMIT
    with tempfile.TemporaryFile() as f:
        f.write(text.encode("utf-8"))
        f.seek(0)
        content = cwl_utils.parser.cwl_v1_2_utils.content_limit_respected_read(f)
    assert content == text


def test_v1_2_file_content_larger_than_64_kB() -> None:
    """Test that reading file content fails for files larger than 64kB in CWL v1.0."""
    text = "a" * (cwl_utils.parser.cwl_v1_2_utils.CONTENT_LIMIT + 1)
    with tempfile.TemporaryFile() as f:
        f.write(text.encode("utf-8"))
        f.seek(0)
        with raises(WorkflowException):
            cwl_utils.parser.cwl_v1_2_utils.content_limit_respected_read(f)


def test_v1_2_stdout_to_file() -> None:
    """Test that stdout shortcut is converted to stdout parameter with CWL v1.2."""
    clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_2.CommandOutputParameter(id="test", type_="stdout")
        ],
    )
    cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)
    assert clt.stdout is not None
    assert clt.stdout == clt.outputs[0].outputBinding.glob


def test_v1_2_stdout_to_file_with_binding() -> None:
    """Test that outputBinding is not allowed with stdout shortcut with CWL v1.2."""
    clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_2.CommandOutputParameter(
                id="test",
                type_="stdout",
                outputBinding=cwl_utils.parser.cwl_v1_2.CommandOutputBinding(
                    glob="output.txt"
                ),
            )
        ],
    )
    with raises(ValidationException):
        cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)


def test_v1_2_stdout_to_file_preserve_original() -> None:
    """Test that stdout parameter prevails on stdout shortcut with CWL v1.2."""
    clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_2.CommandOutputParameter(id="test", type_="stdout")
        ],
        stdout="original.txt",
    )
    cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)
    assert clt.stdout == "original.txt"
    assert clt.stdout == clt.outputs[0].outputBinding.glob


def test_v1_2_stderr_to_file() -> None:
    """Test that stderr shortcut is converted to stderr parameter with CWL v1.2."""
    clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_2.CommandOutputParameter(id="test", type_="stderr")
        ],
    )
    cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)
    assert clt.stderr is not None
    assert clt.stderr == clt.outputs[0].outputBinding.glob


def test_v1_2_stderr_to_file_with_binding() -> None:
    """Test that outputBinding is not allowed with stderr shortcut with CWL v1.2."""
    clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_2.CommandOutputParameter(
                id="test",
                type_="stderr",
                outputBinding=cwl_utils.parser.cwl_v1_2.CommandOutputBinding(
                    glob="err.txt"
                ),
            )
        ],
    )
    with raises(ValidationException):
        cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)


def test_v1_2_stderr_to_file_preserve_original() -> None:
    """Test that stderr parameter prevails on stdout shortcut with CWL v1.2."""
    clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_2.CommandOutputParameter(id="test", type_="stderr")
        ],
        stderr="original.txt",
    )
    cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)
    assert clt.stderr == "original.txt"
    assert clt.stderr == clt.outputs[0].outputBinding.glob


def test_v1_2_stdin_to_file() -> None:
    """Test that stdin shortcut is converted to stdin parameter with CWL v1.2."""
    clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
        inputs=[
            cwl_utils.parser.cwl_v1_2.CommandInputParameter(id="test", type_="stdin")
        ],
        outputs=[],
    )
    cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)
    assert clt.stdin is not None


def test_v1_2_stdin_to_file_with_binding() -> None:
    """Test that inputBinding is not allowed with stdin shortcut with CWL v1.2."""
    clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
        inputs=[
            cwl_utils.parser.cwl_v1_2.CommandInputParameter(
                id="test",
                type_="stdin",
                inputBinding=cwl_utils.parser.cwl_v1_2.CommandLineBinding(
                    prefix="--test"
                ),
            )
        ],
        outputs=[],
    )
    with raises(ValidationException):
        cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)


def test_v1_2_stdin_to_file_fail_with_original() -> None:
    """Test that stdin shortcut fails when stdin parameter is defined with CWL v1.2."""
    clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
        inputs=[
            cwl_utils.parser.cwl_v1_2.CommandInputParameter(id="test", type_="stdin")
        ],
        outputs=[],
        stdin="original.txt",
    )
    with raises(ValidationException):
        cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)


def test_v1_2_type_compare_list() -> None:
    """Test that the type comparison works correctly a list type with CWL v1.2."""
    uri = Path(get_data("testdata/echo_v1_2.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    assert cwl_utils.parser.cwl_v1_2_utils._compare_type(
        cwl_obj.inputs[0].type_, cwl_obj.inputs[0].type_
    )


def test_v1_2_type_compare_record() -> None:
    """Test that the type comparison works correctly a record type with CWL v1.2."""
    uri = Path(get_data("testdata/record-output-wf_v1_2.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert cwl_utils.parser.cwl_v1_2_utils._compare_type(source_type, source_type)


def test_v1_2_type_for_source() -> None:
    """Test that the type is correctly inferred from a source id with CWL v1.2."""
    uri = Path(get_data("testdata/step_valuefrom5_wf_v1_2.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        cwl_obj, cwl_obj.loadingOptions.fileuri + "#step1/echo_out_file"
    )
    assert source_type == "File"


def test_v1_2_type_for_source_with_id() -> None:
    """Test that the type is correctly inferred from a source id with CWL v1.2."""
    uri = (
        Path(get_data("testdata/step_valuefrom5_wf_with_id_v1_2.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        cwl_obj, cwl_obj.loadingOptions.fileuri + "#step1/echo_out_file"
    )
    assert source_type == "File"


def test_v1_2_type_for_stdout() -> None:
    """Test that the `stdout` type is correctly matched with the `File` type in CWL v1.2."""
    uri = Path(get_data("testdata/stdout-wf_v1_2.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        cwl_obj, cwl_obj.outputs[0].outputSource
    )
    assert source_type == "File"


def test_v1_2_type_output_source_record() -> None:
    """Test that the type is correctly inferred from a record output source with CWL v1.2."""
    uri = Path(get_data("testdata/record-output-wf_v1_2.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_2.RecordSchema)
    fields = cast(
        MutableSequence[cwl_utils.parser.cwl_v1_2.RecordField], source_type.fields
    )
    assert len(fields) == 2
    assert fields[0].type_ == "File"
    assert fields[1].type_ == "File"


def test_v1_2_type_for_output_source_with_single_scatter_step() -> None:
    """Test that the type is correctly inferred from a single scatter step with CWL v1.2."""
    uri = Path(get_data("testdata/scatter-wf1_v1_2.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert source_type.items == "string"


def test_v1_2_type_for_output_source_with_nested_crossproduct_scatter_step() -> None:
    """Test that the type is correctly inferred from a nested_crossproduct scatter step with CWL v1.2."""
    uri = Path(get_data("testdata/scatter-wf2_v1_2.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert isinstance(source_type.items, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert source_type.items.items == "string"


def test_v1_2_type_for_output_source_with_flat_crossproduct_scatter_step() -> None:
    """Test that the type is correctly inferred from a flat_crossproduct scatter step with CWL v1.2."""
    uri = Path(get_data("testdata/scatter-wf3_v1_2.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert source_type.items == "string"


def test_v1_2_type_for_source_with_multiple_entries_merge_nested() -> None:
    """Test that the type is correctly inferred from a list of source ids and merge_nested with CWL v1.2."""
    uri = Path(get_data("testdata/count-lines6-wf_v1_2.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert isinstance(source_type.items, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert source_type.items.items == "File"


def test_v1_2_type_for_source_with_multiple_entries_merge_flattened() -> None:
    """Test that the type is correctly inferred from a list of source ids and merge_flattened with CWL v1.2."""  # noqa: B950
    uri = Path(get_data("testdata/count-lines7-wf_v1_2.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert source_type.items == "File"


def test_v1_2_type_for_source_with_single_entry_merge_nested() -> None:
    """Test that the type is correctly inferred from a single source id and merge_nested with CWL v1.2."""
    uri = (
        Path(get_data("testdata/count-lines6-single-source-wf_v1_2.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert isinstance(source_type.items, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert source_type.items.items == "File"


def test_v1_2_type_for_source_with_single_entry_merge_flattened() -> None:
    """Test that the type is correctly inferred from a single source id and merge_flattened with CWL v1.2."""
    uri = (
        Path(get_data("testdata/count-lines7-single-source-wf_v1_2.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert source_type.items == "File"


def test_v1_2_type_for_source_with_multiple_entries_first_non_null() -> None:
    """Test that the type is correctly inferred from a list of source ids and first_non_null with CWL v1.2."""
    uri = Path(get_data("testdata/cond-wf-003.1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
        pickValue=cwl_obj.outputs[0].pickValue,
    )
    assert source_type == "string"


def test_v1_2_type_for_source_with_multiple_entries_the_only_non_null() -> None:
    """Test that the type is correctly inferred from a list of source ids and the_only_non_null with CWL v1.2."""  # noqa: B950
    uri = Path(get_data("testdata/cond-wf-004.1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
        pickValue=cwl_obj.outputs[0].pickValue,
    )
    assert source_type == "string"


def test_v1_2_type_for_source_with_multiple_entries_all_non_null() -> None:
    """Test that the type is correctly inferred from a list of source ids and all_non_null with CWL v1.2."""
    uri = Path(get_data("testdata/cond-wf-005.1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
        pickValue=cwl_obj.outputs[0].pickValue,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert source_type.items == "string"


def test_v1_2_type_for_source_with_single_entry_first_non_null() -> None:
    """Test that the type is correctly inferred from a single source id and first_non_null with CWL v1.2."""
    uri = Path(get_data("testdata/cond-single-source-wf-003.1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
        pickValue=cwl_obj.outputs[0].pickValue,
    )
    assert source_type == "string"


def test_v1_2_type_for_source_with_single_entry_the_only_non_null() -> None:
    """Test that the type is correctly inferred from a single source id and the_only_non_null with CWL v1.2."""  # noqa: B950
    uri = Path(get_data("testdata/cond-single-source-wf-004.1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
        pickValue=cwl_obj.outputs[0].pickValue,
    )
    assert source_type == "string"


def test_v1_2_type_for_source_with_single_entry_all_non_null() -> None:
    """Test that the type is correctly inferred from a single source id and all_non_null with CWL v1.2."""
    uri = Path(get_data("testdata/cond-single-source-wf-005.1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.outputs[0].outputSource,
        pickValue=cwl_obj.outputs[0].pickValue,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert source_type.items == "string"

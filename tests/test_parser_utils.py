# SPDX-License-Identifier: Apache-2.0
"""Test the CWL parsers utility functions."""
import tempfile
from pathlib import Path

from pytest import raises
from schema_salad.exceptions import ValidationException

import cwl_utils.parser.cwl_v1_0
import cwl_utils.parser.cwl_v1_0_utils
import cwl_utils.parser.cwl_v1_1
import cwl_utils.parser.cwl_v1_1_utils
import cwl_utils.parser.cwl_v1_2
import cwl_utils.parser.cwl_v1_2_utils
from cwl_utils.errors import WorkflowException
from cwl_utils.parser import load_document_by_uri

HERE = Path(__file__).resolve().parent


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
            cwl_utils.parser.cwl_v1_0.CommandOutputParameter(id="test", type="stdout")
        ],
    )
    cwl_utils.parser.cwl_v1_0_utils.convert_stdstreams_to_files(clt)
    assert clt.stdout is not None
    assert clt.stdout == clt.outputs[0].outputBinding.glob


def test_v1_0_stdout_to_file_with_binding() -> None:
    """Test that outputBinding is not allowed with stdout shortcut with CWL v1.0."""
    with raises(ValidationException):
        clt = cwl_utils.parser.cwl_v1_0.CommandLineTool(
            inputs=[],
            outputs=[
                cwl_utils.parser.cwl_v1_0.CommandOutputParameter(
                    id="test",
                    type="stdout",
                    outputBinding=cwl_utils.parser.cwl_v1_0.CommandOutputBinding(
                        glob="output.txt"
                    ),
                )
            ],
        )
        cwl_utils.parser.cwl_v1_0_utils.convert_stdstreams_to_files(clt)


def test_v1_0_stdout_to_file_preserve_original() -> None:
    """Test that stdout parameter prevails on stdout shortcut with CWL v1.0."""
    clt = cwl_utils.parser.cwl_v1_0.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_0.CommandOutputParameter(id="test", type="stdout")
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
            cwl_utils.parser.cwl_v1_0.CommandOutputParameter(id="test", type="stderr")
        ],
    )
    cwl_utils.parser.cwl_v1_0_utils.convert_stdstreams_to_files(clt)
    assert clt.stderr is not None
    assert clt.stderr == clt.outputs[0].outputBinding.glob


def test_v1_0_stderr_to_file_with_binding() -> None:
    """Test that outputBinding is not allowed with stderr shortcut with CWL v1.0."""
    with raises(ValidationException):
        clt = cwl_utils.parser.cwl_v1_0.CommandLineTool(
            inputs=[],
            outputs=[
                cwl_utils.parser.cwl_v1_0.CommandOutputParameter(
                    id="test",
                    type="stderr",
                    outputBinding=cwl_utils.parser.cwl_v1_0.CommandOutputBinding(
                        glob="err.txt"
                    ),
                )
            ],
        )
        cwl_utils.parser.cwl_v1_0_utils.convert_stdstreams_to_files(clt)


def test_v1_0_stderr_to_file_preserve_original() -> None:
    """Test that stderr parameter prevails on stdout shortcut with CWL v1.0."""
    clt = cwl_utils.parser.cwl_v1_0.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_0.CommandOutputParameter(id="test", type="stderr")
        ],
        stderr="original.txt",
    )
    cwl_utils.parser.cwl_v1_0_utils.convert_stdstreams_to_files(clt)
    assert clt.stderr == "original.txt"
    assert clt.stderr == clt.outputs[0].outputBinding.glob


def test_v1_0_type_for_source() -> None:
    """Test that the type is correctly inferred from a source id with CWL v1.0."""
    uri = Path(HERE / "../testdata/step_valuefrom5_wf_v1_0.cwl").resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.cwl_v1_0_utils.type_for_source(
        cwl_obj, cwl_obj.loadingOptions.fileuri + "#step1/echo_out_file"
    )
    assert source_type == "File"


def test_v1_0_type_for_source_with_id() -> None:
    """Test that the type is correctly inferred from a source id with CWL v1.0."""
    uri = (
        Path(HERE / "../testdata/step_valuefrom5_wf_with_id_v1_0.cwl")
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.cwl_v1_0_utils.type_for_source(
        cwl_obj, cwl_obj.loadingOptions.fileuri + "#step1/echo_out_file"
    )
    assert source_type == "File"


def test_v1_0_type_for_source_with_multiple_entries_merge_nested() -> None:
    """Test that the type is correctly inferred from a list of source ids and merge_nested with CWL v1.0."""
    uri = Path(HERE / "../testdata/count-lines6-wf_v10.cwl").resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.cwl_v1_0_utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert isinstance(source_type.items, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert isinstance(source_type.items.items[0], cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert source_type.items.items[0].items == "File"


def test_v1_0_type_for_source_with_multiple_entries_merge_flattened() -> None:
    """Test that the type is correctly inferred from a list of source ids and merge_flattened with CWL v1.0."""
    uri = Path(HERE / "../testdata/count-lines7-wf_v10.cwl").resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.cwl_v1_0_utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert isinstance(source_type.items[0], cwl_utils.parser.cwl_v1_0.ArraySchema)
    assert source_type.items[0].items == "File"


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
            cwl_utils.parser.cwl_v1_1.CommandOutputParameter(id="test", type="stdout")
        ],
    )
    cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)
    assert clt.stdout is not None
    assert clt.stdout == clt.outputs[0].outputBinding.glob


def test_v1_1_stdout_to_file_with_binding() -> None:
    """Test that outputBinding is not allowed with stdout shortcut with CWL v1.1."""
    with raises(ValidationException):
        clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
            inputs=[],
            outputs=[
                cwl_utils.parser.cwl_v1_1.CommandOutputParameter(
                    id="test",
                    type="stdout",
                    outputBinding=cwl_utils.parser.cwl_v1_1.CommandOutputBinding(
                        glob="output.txt"
                    ),
                )
            ],
        )
        cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)


def test_v1_1_stdout_to_file_preserve_original() -> None:
    """Test that stdout parameter prevails on stdout shortcut with CWL v1.1."""
    clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_1.CommandOutputParameter(id="test", type="stdout")
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
            cwl_utils.parser.cwl_v1_1.CommandOutputParameter(id="test", type="stderr")
        ],
    )
    cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)
    assert clt.stderr is not None
    assert clt.stderr == clt.outputs[0].outputBinding.glob


def test_v1_1_stderr_to_file_with_binding() -> None:
    """Test that outputBinding is not allowed with stderr shortcut with CWL v1.1."""
    with raises(ValidationException):
        clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
            inputs=[],
            outputs=[
                cwl_utils.parser.cwl_v1_1.CommandOutputParameter(
                    id="test",
                    type="stderr",
                    outputBinding=cwl_utils.parser.cwl_v1_1.CommandOutputBinding(
                        glob="err.txt"
                    ),
                )
            ],
        )
        cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)


def test_v1_1_stderr_to_file_preserve_original() -> None:
    """Test that stderr parameter prevails on stdout shortcut with CWL v1.1."""
    clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_1.CommandOutputParameter(id="test", type="stderr")
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
            cwl_utils.parser.cwl_v1_1.CommandInputParameter(id="test", type="stdin")
        ],
        outputs=[],
    )
    cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)
    assert clt.stdin is not None


def test_v1_1_stdin_to_file_with_binding() -> None:
    """Test that inputBinding is not allowed with stdin shortcut with CWL v1.1."""
    with raises(ValidationException):
        clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
            inputs=[
                cwl_utils.parser.cwl_v1_1.CommandInputParameter(
                    id="test",
                    type="stdin",
                    inputBinding=cwl_utils.parser.cwl_v1_1.CommandLineBinding(
                        prefix="--test"
                    ),
                )
            ],
            outputs=[],
        )
        cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)


def test_v1_1_stdin_to_file_fail_with_original() -> None:
    """Test that stdin shortcut fails when stdin parameter is defined with CWL v1.1."""
    with raises(ValidationException):
        clt = cwl_utils.parser.cwl_v1_1.CommandLineTool(
            inputs=[
                cwl_utils.parser.cwl_v1_1.CommandInputParameter(id="test", type="stdin")
            ],
            outputs=[],
            stdin="original.txt",
        )
        cwl_utils.parser.cwl_v1_1_utils.convert_stdstreams_to_files(clt)


def test_v1_1_type_for_source() -> None:
    """Test that the type is correctly inferred from a source id with CWL v1.1."""
    uri = Path(HERE / "../testdata/step_valuefrom5_wf_v1_1.cwl").resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.cwl_v1_1_utils.type_for_source(
        cwl_obj, cwl_obj.loadingOptions.fileuri + "#step1/echo_out_file"
    )
    assert source_type == "File"


def test_v1_1_type_for_source_with_id() -> None:
    """Test that the type is correctly inferred from a source id with CWL v1.1."""
    uri = (
        Path(HERE / "../testdata/step_valuefrom5_wf_with_id_v1_1.cwl")
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.cwl_v1_1_utils.type_for_source(
        cwl_obj, cwl_obj.loadingOptions.fileuri + "#step1/echo_out_file"
    )
    assert source_type == "File"


def test_v1_1_type_for_source_with_multiple_entries_merge_nested() -> None:
    """Test that the type is correctly inferred from a list of source ids and merge_nested with CWL v1.1."""
    uri = Path(HERE / "../testdata/count-lines6-wf_v11.cwl").resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.cwl_v1_1_utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert isinstance(source_type.items, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert isinstance(source_type.items.items[0], cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert source_type.items.items[0].items == "File"


def test_v1_1_type_for_source_with_multiple_entries_merge_flattened() -> None:
    """Test that the type is correctly inferred from a list of source ids and merge_flattened with CWL v1.1."""
    uri = Path(HERE / "../testdata/count-lines7-wf_v11.cwl").resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.cwl_v1_1_utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert isinstance(source_type.items[0], cwl_utils.parser.cwl_v1_1.ArraySchema)
    assert source_type.items[0].items == "File"


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
    with raises(WorkflowException):
        text = "a" * (cwl_utils.parser.cwl_v1_2_utils.CONTENT_LIMIT + 1)
        with tempfile.TemporaryFile() as f:
            f.write(text.encode("utf-8"))
            f.seek(0)
            cwl_utils.parser.cwl_v1_2_utils.content_limit_respected_read(f)


def test_v1_2_stdout_to_file() -> None:
    """Test that stdout shortcut is converted to stdout parameter with CWL v1.2."""
    clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_2.CommandOutputParameter(id="test", type="stdout")
        ],
    )
    cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)
    assert clt.stdout is not None
    assert clt.stdout == clt.outputs[0].outputBinding.glob


def test_v1_2_stdout_to_file_with_binding() -> None:
    """Test that outputBinding is not allowed with stdout shortcut with CWL v1.2."""
    with raises(ValidationException):
        clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
            inputs=[],
            outputs=[
                cwl_utils.parser.cwl_v1_2.CommandOutputParameter(
                    id="test",
                    type="stdout",
                    outputBinding=cwl_utils.parser.cwl_v1_2.CommandOutputBinding(
                        glob="output.txt"
                    ),
                )
            ],
        )
        cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)


def test_v1_2_stdout_to_file_preserve_original() -> None:
    """Test that stdout parameter prevails on stdout shortcut with CWL v1.2."""
    clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_2.CommandOutputParameter(id="test", type="stdout")
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
            cwl_utils.parser.cwl_v1_2.CommandOutputParameter(id="test", type="stderr")
        ],
    )
    cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)
    assert clt.stderr is not None
    assert clt.stderr == clt.outputs[0].outputBinding.glob


def test_v1_2_stderr_to_file_with_binding() -> None:
    """Test that outputBinding is not allowed with stderr shortcut with CWL v1.2."""
    with raises(ValidationException):
        clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
            inputs=[],
            outputs=[
                cwl_utils.parser.cwl_v1_2.CommandOutputParameter(
                    id="test",
                    type="stderr",
                    outputBinding=cwl_utils.parser.cwl_v1_2.CommandOutputBinding(
                        glob="err.txt"
                    ),
                )
            ],
        )
        cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)


def test_v1_2_stderr_to_file_preserve_original() -> None:
    """Test that stderr parameter prevails on stdout shortcut with CWL v1.2."""
    clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
        inputs=[],
        outputs=[
            cwl_utils.parser.cwl_v1_2.CommandOutputParameter(id="test", type="stderr")
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
            cwl_utils.parser.cwl_v1_2.CommandInputParameter(id="test", type="stdin")
        ],
        outputs=[],
    )
    cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)
    assert clt.stdin is not None


def test_v1_2_stdin_to_file_with_binding() -> None:
    """Test that inputBinding is not allowed with stdin shortcut with CWL v1.2."""
    with raises(ValidationException):
        clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
            inputs=[
                cwl_utils.parser.cwl_v1_2.CommandInputParameter(
                    id="test",
                    type="stdin",
                    inputBinding=cwl_utils.parser.cwl_v1_2.CommandLineBinding(
                        prefix="--test"
                    ),
                )
            ],
            outputs=[],
        )
        cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)


def test_v1_2_stdin_to_file_fail_with_original() -> None:
    """Test that stdin shortcut fails when stdin parameter is defined with CWL v1.2."""
    with raises(ValidationException):
        clt = cwl_utils.parser.cwl_v1_2.CommandLineTool(
            inputs=[
                cwl_utils.parser.cwl_v1_2.CommandInputParameter(id="test", type="stdin")
            ],
            outputs=[],
            stdin="original.txt",
        )
        cwl_utils.parser.cwl_v1_2_utils.convert_stdstreams_to_files(clt)


def test_v1_2_type_for_source() -> None:
    """Test that the type is correctly inferred from a source id with CWL v1.2."""
    uri = Path(HERE / "../testdata/step_valuefrom5_wf_v1_2.cwl").resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.cwl_v1_2_utils.type_for_source(
        cwl_obj, cwl_obj.loadingOptions.fileuri + "#step1/echo_out_file"
    )
    assert source_type == "File"


def test_v1_2_type_for_source_with_id() -> None:
    """Test that the type is correctly inferred from a source id with CWL v1.2."""
    uri = (
        Path(HERE / "../testdata/step_valuefrom5_wf_with_id_v1_2.cwl")
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.cwl_v1_2_utils.type_for_source(
        cwl_obj, cwl_obj.loadingOptions.fileuri + "#step1/echo_out_file"
    )
    assert source_type == "File"


def test_v1_2_type_for_source_with_multiple_entries_merge_nested() -> None:
    """Test that the type is correctly inferred from a list of source ids and merge_nested with CWL v1.2."""
    uri = Path(HERE / "../testdata/count-lines6-wf_v12.cwl").resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.cwl_v1_2_utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert isinstance(source_type.items, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert isinstance(source_type.items.items[0], cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert source_type.items.items[0].items == "File"


def test_v1_2_type_for_source_with_multiple_entries_merge_flattened() -> None:
    """Test that the type is correctly inferred from a list of source ids and merge_flattened with CWL v1.2."""
    uri = Path(HERE / "../testdata/count-lines7-wf_v12.cwl").resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    source_type = cwl_utils.parser.cwl_v1_2_utils.type_for_source(
        process=cwl_obj,
        sourcenames=cwl_obj.steps[0].in_[0].source,
        linkMerge=cwl_obj.steps[0].in_[0].linkMerge,
    )
    assert isinstance(source_type, cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert isinstance(source_type.items[0], cwl_utils.parser.cwl_v1_2.ArraySchema)
    assert source_type.items[0].items == "File"

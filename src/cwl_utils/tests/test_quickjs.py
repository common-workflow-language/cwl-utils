# SPDX-License-Identifier: Apache-2.0
"""Tests for the QuickJS-based JSEngine and JS engine selection."""

import json
import shutil
import threading

import pytest

from cwl_utils import expression, sandboxjs
from cwl_utils.errors import JavascriptException

needs_qjs = pytest.mark.skipif(
    shutil.which("qjs") is None,
    reason="Requires the qjs executable on the system path.",
)


@pytest.fixture(name="restore_js_engine")
def restore_js_engine_fixture() -> "pytest.fixture":  # type: ignore[valid-type]
    """Restore the process-wide JS engine after a test that replaces it."""
    saved = sandboxjs.get_js_engine()
    yield
    sandboxjs.set_js_engine(saved)


@pytest.fixture(name="fresh_engine_state")
def fresh_engine_state_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear the cached JS engine so get_js_engine() re-reads CWL_JS_ENGINE."""
    monkeypatch.setattr(sandboxjs, "__js_engine", None)


@needs_qjs
def test_quickjs_simple_expression() -> None:
    assert sandboxjs.QuickJSEngine().eval("(1 + 2)") == 3


@needs_qjs
def test_quickjs_string_result() -> None:
    assert sandboxjs.QuickJSEngine().eval('("a" + "b")') == "ab"


@needs_qjs
def test_quickjs_object_result() -> None:
    assert sandboxjs.QuickJSEngine().eval('({"x": [1, 2]})') == {"x": [1, 2]}


@needs_qjs
def test_quickjs_null_and_undefined() -> None:
    engine = sandboxjs.QuickJSEngine()
    assert engine.eval("(null)") is None
    assert engine.eval("(undefined)") is None


@needs_qjs
def test_quickjs_function_body_form() -> None:
    """The ${...} form reaches the engine with the leading $ stripped."""
    assert sandboxjs.QuickJSEngine().eval("{return 6 * 7;}") == 42


@needs_qjs
def test_quickjs_jslib_is_available() -> None:
    assert (
        sandboxjs.QuickJSEngine().eval(
            "(double(21))", jslib="function double(x){return 2*x;}\n"
        )
        == 42
    )


@needs_qjs
def test_quickjs_union_type_idiom() -> None:
    """A realistic string-or-File union-handling expression."""
    jslib = (
        'var inputs = {"input-data": ['
        '"https://example.org/f1", {"class": "File", "path": "/tmp/f2"}]};\n'
    )
    result = sandboxjs.QuickJSEngine().eval(
        '(inputs["input-data"].map(function (f) {'
        ' return typeof f === "string" ? f : f.path; }))',
        jslib=jslib,
    )
    assert result == ["https://example.org/f1", "/tmp/f2"]


@needs_qjs
def test_quickjs_string_escaping() -> None:
    """Quotes, backslashes, backticks, and the U+2028 line separator survive."""
    jslib = r'var s = "a\"b\\c`d" + String.fromCharCode(0x2028);' + "\n"
    assert sandboxjs.QuickJSEngine().eval("(s)", jslib=jslib) == 'a"b\\c`d' + chr(
        0x2028
    )


@needs_qjs
def test_quickjs_syntax_error_raises() -> None:
    with pytest.raises(JavascriptException):
        sandboxjs.QuickJSEngine().eval("(1 +)")


@needs_qjs
def test_quickjs_eval_timeout() -> None:
    with pytest.raises(JavascriptException, match="killed after"):
        sandboxjs.QuickJSEngine().eval("(function(){while(true){}})()", timeout=2)


def test_quickjs_missing_binary_raises() -> None:
    """A missing qjs binary surfaces as JavascriptException, not OSError."""
    engine = sandboxjs.QuickJSEngine(qjs_path="/nonexistent/qjs")
    with pytest.raises(JavascriptException):
        engine.eval("(1)")


@needs_qjs
def test_quickjs_do_eval(restore_js_engine: None) -> None:
    """Two concatenated expressions through the public do_eval entry point."""
    sandboxjs.set_js_engine(sandboxjs.QuickJSEngine())
    assert (
        expression.do_eval(
            '$("a ")$("string")',
            {},
            [{"class": "InlineJavascriptRequirement"}],
            None,
            None,
            {},
            cwlVersion="v1.0",
        )
        == "a string"
    )


@needs_qjs
def test_quickjs_do_eval_parameter_reference(restore_js_engine: None) -> None:
    """Plain parameter references use the regex_eval path."""
    sandboxjs.set_js_engine(sandboxjs.QuickJSEngine())
    assert (
        expression.do_eval(
            "$(inputs.n)",
            {"n": 7},
            [],
            None,
            None,
            {},
            cwlVersion="v1.0",
        )
        == 7
    )


@needs_qjs
def test_quickjs_exec_js_process_no_context() -> None:
    returncode, stdout, _ = sandboxjs.QuickJSEngine().exec_js_process('"a" + "b"')
    assert returncode == 0
    assert json.loads(stdout) == "ab"


@needs_qjs
def test_quickjs_exec_js_process_with_context() -> None:
    """The context script's completion value provides the code's globals."""
    context = "var double = function(x){return 2*x;};\nvar ob = {double: double}; ob"
    returncode, stdout, _ = sandboxjs.QuickJSEngine().exec_js_process(
        "double(21)", context=context
    )
    assert returncode == 0
    assert json.loads(stdout) == 42


@needs_qjs
def test_quickjs_exec_js_process_jshint_shape() -> None:
    """The call shape cwltool's validate_js uses for jshint."""
    context = (
        "function validateJS(input) {"
        " return {errors: [], globals: [input.code.length]}; }\n"
        "var ob = {validateJS: validateJS}; ob"
    )
    code = "validateJS(%s)" % json.dumps({"code": "1 + 1"})
    returncode, stdout, _ = sandboxjs.QuickJSEngine().exec_js_process(
        code, context=context
    )
    assert returncode == 0
    assert json.loads(stdout) == {"errors": [], "globals": [5]}


@needs_qjs
def test_quickjs_exec_js_process_error() -> None:
    returncode, _, stderr = sandboxjs.QuickJSEngine().exec_js_process("nosuchfn()")
    assert returncode != 0
    assert stderr


@needs_qjs
def test_quickjs_exec_js_process_timeout() -> None:
    returncode, _, _ = sandboxjs.QuickJSEngine().exec_js_process(
        "(function(){while(true){}})()", timeout=1
    )
    assert returncode == -1


def test_quickjs_exec_js_process_js_console_unsupported() -> None:
    with pytest.raises(NotImplementedError):
        sandboxjs.QuickJSEngine().exec_js_process("1", js_console=True)


@needs_qjs
def test_quickjs_module_level_exec_js_process(restore_js_engine: None) -> None:
    """The module-level dispatcher works with the QuickJS engine active."""
    sandboxjs.set_js_engine(sandboxjs.QuickJSEngine())
    returncode, stdout, _ = sandboxjs.exec_js_process("6 * 7")
    assert returncode == 0
    assert json.loads(stdout) == 42


@needs_qjs
def test_env_var_selects_quickjs(
    monkeypatch: pytest.MonkeyPatch, fresh_engine_state: None
) -> None:
    monkeypatch.setenv("CWL_JS_ENGINE", "quickjs")
    assert isinstance(sandboxjs.get_js_engine(), sandboxjs.QuickJSEngine)


def test_env_var_unset_defaults_to_node(
    monkeypatch: pytest.MonkeyPatch, fresh_engine_state: None
) -> None:
    monkeypatch.delenv("CWL_JS_ENGINE", raising=False)
    assert isinstance(sandboxjs.get_js_engine(), sandboxjs.NodeJSEngine)


def test_env_var_node(
    monkeypatch: pytest.MonkeyPatch, fresh_engine_state: None
) -> None:
    monkeypatch.setenv("CWL_JS_ENGINE", "node")
    assert isinstance(sandboxjs.get_js_engine(), sandboxjs.NodeJSEngine)


def test_env_var_invalid_value(
    monkeypatch: pytest.MonkeyPatch, fresh_engine_state: None
) -> None:
    monkeypatch.setenv("CWL_JS_ENGINE", "spidermonkey")
    with pytest.raises(ValueError, match="CWL_JS_ENGINE"):
        sandboxjs.get_js_engine()


def test_env_var_quickjs_but_qjs_missing(
    monkeypatch: pytest.MonkeyPatch, fresh_engine_state: None
) -> None:
    monkeypatch.setenv("CWL_JS_ENGINE", "quickjs")
    monkeypatch.setattr("cwl_utils.sandboxjs.shutil.which", lambda _: None)
    with pytest.raises(JavascriptException, match="qjs"):
        sandboxjs.get_js_engine()


def test_engine_is_cached(
    monkeypatch: pytest.MonkeyPatch, fresh_engine_state: None
) -> None:
    monkeypatch.delenv("CWL_JS_ENGINE", raising=False)
    assert sandboxjs.get_js_engine() is sandboxjs.get_js_engine()


def test_set_js_engine_overrides_env_var(
    monkeypatch: pytest.MonkeyPatch, fresh_engine_state: None
) -> None:
    monkeypatch.setenv("CWL_JS_ENGINE", "quickjs")
    mine = sandboxjs.NodeJSEngine()
    sandboxjs.set_js_engine(mine)
    assert sandboxjs.get_js_engine() is mine


@needs_qjs
def test_quickjs_engine_is_threadsafe(restore_js_engine: None) -> None:
    """Concurrent evals do not interfere (each is an isolated subprocess)."""
    engine = sandboxjs.QuickJSEngine()
    results: dict[int, object] = {}

    def work(i: int) -> None:
        results[i] = engine.eval(f"({i} * 2)")

    threads = [threading.Thread(target=work, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results == {i: i * 2 for i in range(8)}

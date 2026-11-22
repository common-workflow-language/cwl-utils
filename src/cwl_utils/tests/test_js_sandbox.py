"""Test sandboxjs.py and related code."""

import logging
import os
import shutil
import threading
from pathlib import Path
from typing import Any

import pytest

from cwl_utils import expression, sandboxjs

from .util import (
    needs_docker,
    needs_node,
    needs_podman,
    needs_singularity,
    needs_udocker,
)

node_versions = [
    ("v0.8.26\n", False),
    ("v0.10.25\n", False),
    ("v0.10.26\n", True),
    ("v4.4.2\n", True),
    ("v7.7.3\n", True),
    ("v0.10.27-alpha.0.0.0\n", True),
    ("v0.10.26-beta.0.0.0\n", False),
    ("v0.10.25-rc1\n", False),
]


@pytest.mark.parametrize("version,supported", node_versions)
def test_node_version(version: str, supported: bool, mocker: Any) -> None:
    mocked_subprocess = mocker.patch("cwl_utils.sandboxjs.subprocess")
    mocked_subprocess.check_output = mocker.Mock(return_value=version)

    assert sandboxjs.NodeJSEngine().check_js_threshold_version("node") == supported


def test_value_from_two_concatenated_expressions() -> None:
    js_engine = sandboxjs.get_js_engine()
    js_engine.have_node_slim = False  # type: ignore[attr-defined]
    js_engine.localdata = threading.local()  # type: ignore[attr-defined]
    assert (
        expression.do_eval(
            '$("a ")$("string")',
            {},
            [{"class": "InlineJavascriptRequirement"}],
            None,
            None,
            {},
            cwlVersion="v1.0",
            js_engine=js_engine,
        )
        == "a string"
    )


def hide_nodejs(temp_dir: Path) -> str:
    """Generate a new PATH that hides node{js,}."""
    paths: list[str] = os.environ.get("PATH", "").split(":")
    names: list[str] = []
    if "/bin" in paths:
        bin_path = Path("/bin")
        if (
            bin_path.is_symlink()
            and os.readlink(bin_path) == "usr/bin"
            and "/usr/bin" in paths
        ):
            paths.remove("/bin")
    for name in ("nodejs", "node"):
        path = shutil.which(name, path=":".join(paths))
        if path:
            names.append(path)
    for name in names:
        dirname = os.path.dirname(name)
        if dirname in paths:
            paths.remove(dirname)
            new_dir = temp_dir / os.path.basename(dirname)
            new_dir.mkdir()
            for entry in os.listdir(dirname):
                if entry not in ("nodejs", "node"):
                    os.symlink(Path(dirname, entry), new_dir / entry)
            paths.append(str(new_dir))
    return ":".join(paths)


@needs_podman
def test_value_from_two_concatenated_expressions_podman(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Javascript test using podman."""
    new_paths = hide_nodejs(tmp_path)
    with monkeypatch.context() as m:
        m.setenv("PATH", new_paths)
        js_engine = sandboxjs.NodeJSEngine()
        js_engine.have_node_slim = False
        js_engine.localdata = threading.local()
        m.setattr(sandboxjs, "__js_engine", js_engine)
        assert (
            expression.do_eval(
                '$("a ")$("string")',
                {},
                [{"class": "InlineJavascriptRequirement"}],
                None,
                None,
                {},
                cwlVersion="v1.0",
                container_engine="podman",
                js_engine=js_engine,
            )
            == "a string"
        )


@needs_udocker
def test_value_from_two_concatenated_expressions_udocker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Javascript test using udocker."""
    new_paths = hide_nodejs(tmp_path)
    with monkeypatch.context() as m:
        m.setenv("PATH", new_paths)
        js_engine = sandboxjs.NodeJSEngine()
        js_engine.have_node_slim = False
        js_engine.localdata = threading.local()
        m.setattr(sandboxjs, "__js_engine", js_engine)
        assert (
            expression.do_eval(
                '$("a ")$("string")',
                {},
                [{"class": "InlineJavascriptRequirement"}],
                None,
                None,
                {},
                cwlVersion="v1.0",
                container_engine="udocker",
                js_engine=js_engine,
            )
            == "a string"
        )


@needs_singularity
def test_value_from_two_concatenated_expressions_singularity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Javascript test using Singularity."""
    new_paths = hide_nodejs(tmp_path)
    with monkeypatch.context() as m:
        m.setenv("PATH", new_paths)
        js_engine = sandboxjs.NodeJSEngine()
        js_engine.have_node_slim = False
        js_engine.localdata = threading.local()
        m.setattr(sandboxjs, "__js_engine", js_engine)
        assert (
            expression.do_eval(
                '$("a ")$("string")',
                {},
                [{"class": "InlineJavascriptRequirement"}],
                None,
                None,
                {},
                cwlVersion="v1.0",
                container_engine="singularity",
                js_engine=js_engine,
            )
            == "a string"
        )


@needs_singularity
def test_singularity_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Affirm that CWL_SINGULARIT_CACHE is respected."""
    bin_path = tmp_path / "no_nodejs"
    bin_path.mkdir()
    new_paths = hide_nodejs(bin_path)
    cache_path = tmp_path / "singularity_cache"
    cache_path.mkdir()
    with monkeypatch.context() as m:
        m.setenv("PATH", new_paths)
        m.setenv("CWL_SINGULARITY_CACHE", str(cache_path))
        js_engine = sandboxjs.NodeJSEngine()
        js_engine.localdata = threading.local()
        js_engine.have_node_slim = False
        m.setattr(sandboxjs, "__js_engine", js_engine)
        assert (
            expression.do_eval(
                "$(42*23)",
                {},
                [{"class": "InlineJavascriptRequirement"}],
                None,
                None,
                {},
                cwlVersion="v1.0",
                container_engine="singularity",
                js_engine=js_engine,
            )
            == 42 * 23
        )
        assert (cache_path / "node_alpine.sif").exists()


def test_caches_js_processes(mocker: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandboxjs, "__js_engine", sandboxjs.NodeJSEngine())
    sandboxjs.exec_js_process("7", context="{}")

    mocked_new_js_proc = mocker.patch("cwl_utils.sandboxjs.new_js_proc")
    sandboxjs.exec_js_process("7", context="{}")

    mocked_new_js_proc.assert_not_called()


def _test_jsconsole(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    container_engine: str,
) -> None:
    caplog.set_level(logging.INFO, logger="cwl_utils")
    js_engine = sandboxjs.NodeJSEngine()
    js_engine.have_node_slim = False
    js_engine.localdata = threading.local()
    assert (
        expression.do_eval(
            '${console.log("Log message 23");console.error("Error message 42");return "a " + "string";}',
            {},
            [{"class": "InlineJavascriptRequirement"}],
            None,
            None,
            {},
            cwlVersion="v1.0",
            js_console=True,
            js_engine=js_engine,
            container_engine=container_engine,
        )
        == "a string"
    )
    assert (
        "Running with support for javascript console in expressions (DO NOT USE IN PRODUCTION)"
        in caplog.text
    )
    assert "Javascript console output" in caplog.text
    assert "[log] Log message 23" in caplog.text
    assert "[err] Error message 42" in caplog.text


@needs_node
def test_jsconsole_node(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the JS console feature with local node{,js}."""
    _test_jsconsole(caplog, monkeypatch, "")


@needs_docker
def test_jsconsole_docker(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test the JS console feature with nodejs via a Docker container engine."""
    new_paths = hide_nodejs(tmp_path)
    with monkeypatch.context() as m:
        m.setenv("PATH", new_paths)
        _test_jsconsole(caplog, monkeypatch, "docker")


@needs_podman
def test_jsconsole_podman(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test the JS console feature with nodejs via a Podman container engine."""
    new_paths = hide_nodejs(tmp_path)
    with monkeypatch.context() as m:
        m.setenv("PATH", new_paths)
        _test_jsconsole(caplog, monkeypatch, "podman")


@needs_singularity
def test_jsconsole_singularity(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test the JS console feature with nodejs via a Apptainer/Singularity container engine."""
    new_paths = hide_nodejs(tmp_path)
    with monkeypatch.context() as m:
        m.setenv("PATH", new_paths)
        _test_jsconsole(caplog, monkeypatch, "singularity")


@needs_udocker
def test_jsconsole_udocker(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test the JS console feature with nodejs via a Docker container engine."""
    new_paths = hide_nodejs(tmp_path)
    with monkeypatch.context() as m:
        m.setenv("PATH", new_paths)
        _test_jsconsole(caplog, monkeypatch, "udocker")

# SPDX-License-Identifier: Apache-2.0
"""Safe execution of CWL Expressions in a NodeJS sandbox."""
import collections
import errno
import json
import os
import re
import select
import subprocess  # nosec
import threading
from abc import ABC, abstractmethod
from io import BytesIO
from typing import (
    Any,
    Awaitable,
    Deque,
    List,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Tuple,
    Union,
    cast,
)

from pkg_resources import resource_stream
from schema_salad.utils import json_dumps

from cwl_utils.errors import JavascriptException, WorkflowException
from cwl_utils.loghandler import _logger
from cwl_utils.types import CWLOutputType
from cwl_utils.utils import singularity_supports_userns

default_timeout = 20

seg_symbol = r"""\w+"""
seg_single = r"""\['([^']|\\')+'\]"""
seg_double = r"""\["([^"]|\\")+"\]"""
seg_index = r"""\[[0-9]+\]"""
segments = rf"(\.{seg_symbol}|{seg_single}|{seg_double}|{seg_index})"
segment_re = re.compile(segments, flags=re.UNICODE)
param_str = rf"\(({seg_symbol}){segments}*\)$"
param_re = re.compile(param_str, flags=re.UNICODE)


def code_fragment_to_js(jscript: str, jslib: str = "") -> str:
    if isinstance(jscript, str) and len(jscript) > 1 and jscript[0] == "{":
        inner_js = jscript
    else:
        inner_js = "{return (%s);}" % jscript

    return f'"use strict";\n{jslib}\n(function(){inner_js})()'


def linenum(fn: str) -> str:
    lines = fn.splitlines()
    ofs = 0
    maxlines = 99
    if len(lines) > maxlines:
        ofs = len(lines) - maxlines
        lines = lines[-maxlines:]
    return "\n".join("%02i %s" % (i + ofs + 1, b) for i, b in enumerate(lines))


def stdfmt(data: str) -> str:
    if "\n" in data:
        return "\n" + data.strip()
    return data


class JSEngine(ABC):
    @abstractmethod
    def eval(
        self, scan: str, jslib: str = "", **kwargs: Any
    ) -> Union[CWLOutputType, Awaitable[CWLOutputType]]:
        ...

    @abstractmethod
    def regex_eval(
        self,
        parsed_string: str,
        remaining_string: str,
        current_value: CWLOutputType,
        **kwargs: Any,
    ) -> Union[CWLOutputType, Awaitable[CWLOutputType]]:
        ...


class NodeJSEngine(JSEngine):
    localdata = threading.local()

    def __init__(
        self,
        have_node_slim: bool = False,
        minimum_node_version_str: str = "0.10.26",
        process_finished_str: str = "r1cepzbhUTxtykz5XTC4\n",
    ):
        self.have_node_slim: bool = have_node_slim
        self.minimum_node_version_str: str = minimum_node_version_str
        self.process_finished_str: str = process_finished_str
        self.processes_to_kill: Deque[subprocess.Popen[str]] = collections.deque()

    def __del__(self) -> None:
        try:
            while self.processes_to_kill:
                process = self.processes_to_kill.popleft()
                if isinstance(process.args, MutableSequence):
                    args = process.args
                else:
                    args = [process.args]
                cidfile = [
                    str(arg).split("=")[1] for arg in args if "--cidfile" in str(arg)
                ]
                if cidfile:  # Try to be nice
                    try:
                        with open(cidfile[0]) as inp_stream:
                            p = subprocess.Popen(  # nosec
                                ["docker", "kill", inp_stream.read()],
                                shell=False,  # nosec
                            )
                            try:
                                p.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                p.kill()
                    except FileNotFoundError:
                        pass
                if process.stdin:
                    process.stdin.close()
                try:
                    process.wait(10)
                except subprocess.TimeoutExpired:
                    pass
                process.kill()
        except TypeError:
            pass

    def check_js_threshold_version(self, working_alias: str) -> bool:
        """
        Check if the nodeJS engine version on the system with the allowed minimum version.

        https://github.com/nodejs/node/blob/master/CHANGELOG.md#nodejs-changelog
        """
        # parse nodejs version into int Tuple: 'v4.2.6\n' -> [4, 2, 6]
        current_version_str = subprocess.check_output(  # nosec
            [working_alias, "-v"], universal_newlines=True
        )
        current_version = [
            int(v) for v in current_version_str.strip().strip("v").split(".")
        ]
        minimum_node_version = [
            int(v) for v in self.minimum_node_version_str.split(".")
        ]

        return current_version >= minimum_node_version

    def exec_js_process(
        self,
        js_text: str,
        timeout: float = default_timeout,
        js_console: bool = False,
        context: Optional[str] = None,
        force_docker_pull: bool = False,
        container_engine: str = "docker",
    ) -> Tuple[int, str, str]:

        if not hasattr(self.localdata, "procs"):
            self.localdata.procs = {}

        if js_console and context is not None:
            raise NotImplementedError("js_console=True and context not implemented")

        if js_console:
            js_engine = "cwlNodeEngineJSConsole.js"
            _logger.warning(
                "Running with support for javascript console in expressions (DO NOT USE IN PRODUCTION)"
            )
        elif context is not None:
            js_engine = "cwlNodeEngineWithContext.js"
        else:
            js_engine = "cwlNodeEngine.js"

        created_new_process = False

        if context is not None:
            nodejs = self.localdata.procs.get((js_engine, context))
        else:
            nodejs = self.localdata.procs.get(js_engine)

        if nodejs is None or nodejs.poll() is not None:
            res = resource_stream(__name__, js_engine)
            js_engine_code = res.read().decode("utf-8")

            created_new_process = True

            new_proc = self.new_js_proc(
                js_engine_code,
                force_docker_pull=force_docker_pull,
                container_engine=container_engine,
            )

            if context is None:
                self.localdata.procs[js_engine] = new_proc
                nodejs = new_proc
            else:
                self.localdata.procs[(js_engine, context)] = new_proc
                nodejs = new_proc

        killed = []

        def terminate() -> None:
            """Kill the node process if it exceeds timeout limit."""
            try:
                killed.append(True)
                nodejs.kill()
            except OSError:
                pass

        timer = threading.Timer(timeout, terminate)
        timer.daemon = True
        timer.start()

        stdin_text = ""
        if created_new_process and context is not None:
            stdin_text = json_dumps(context) + "\n"
        stdin_text += json_dumps(js_text) + "\n"

        stdin_buf = BytesIO(stdin_text.encode("utf-8"))
        stdout_buf = BytesIO()
        stderr_buf = BytesIO()

        rselect = [nodejs.stdout, nodejs.stderr]  # type: List[BytesIO]
        wselect = [nodejs.stdin]  # type: List[BytesIO]

        def process_finished() -> bool:
            return stdout_buf.getvalue().decode("utf-8").endswith(
                self.process_finished_str
            ) and stderr_buf.getvalue().decode("utf-8").endswith(
                self.process_finished_str
            )

        while not process_finished() and timer.is_alive():
            rready, wready, _ = select.select(rselect, wselect, [])
            try:
                if nodejs.stdin in wready:
                    buf = stdin_buf.read(select.PIPE_BUF)
                    if buf:
                        os.write(nodejs.stdin.fileno(), buf)
                for pipes in ((nodejs.stdout, stdout_buf), (nodejs.stderr, stderr_buf)):
                    if pipes[0] in rready:
                        buf = os.read(pipes[0].fileno(), select.PIPE_BUF)
                        if buf:
                            pipes[1].write(buf)
            except OSError:
                break
        timer.cancel()

        stdin_buf.close()
        stdoutdata = stdout_buf.getvalue()[: -len(self.process_finished_str) - 1]
        stderrdata = stderr_buf.getvalue()[: -len(self.process_finished_str) - 1]

        nodejs.poll()

        if nodejs.poll() not in (None, 0):
            if killed:
                returncode = -1
            else:
                returncode = nodejs.returncode
        else:
            returncode = 0

        return returncode, stdoutdata.decode("utf-8"), stderrdata.decode("utf-8")

    def new_js_proc(
        self,
        js_text: str,
        force_docker_pull: bool = False,
        container_engine: str = "docker",
    ) -> "subprocess.Popen[str]":
        """Return a subprocess ready to submit javascript to."""
        required_node_version, docker = (False,) * 2
        nodejs = None  # type: Optional[subprocess.Popen[str]]
        trynodes = ("nodejs", "node")
        for n in trynodes:
            try:
                if (
                    subprocess.check_output(  # nosec
                        [n, "--eval", "process.stdout.write('t')"],
                        universal_newlines=True,
                    )
                    != "t"
                ):
                    continue
                else:
                    nodejs = subprocess.Popen(  # nosec
                        [n, "--eval", js_text],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                    )
                    self.processes_to_kill.append(nodejs)
                    required_node_version = self.check_js_threshold_version(n)
                    break
            except (subprocess.CalledProcessError, OSError):
                pass

        if nodejs is None or nodejs is not None and required_node_version is False:
            try:
                nodeimg = "docker.io/node:slim"
                if container_engine == "singularity":
                    nodeimg = f"docker://{nodeimg}"

                if not self.have_node_slim:
                    if container_engine in ("docker", "podman"):
                        dockerimgs = subprocess.check_output(  # nosec
                            [container_engine, "images", "-q", nodeimg],
                            universal_newlines=True,
                        )
                    elif container_engine != "singularity":
                        raise Exception(
                            f"Unknown container_engine: {container_engine}."
                        )
                    # if output is an empty string
                    if (
                        container_engine == "singularity"
                        or len(dockerimgs.split("\n")) <= 1
                        or force_docker_pull
                    ):
                        # pull node:slim docker container
                        nodejs_pull_commands = [container_engine, "pull"]
                        if container_engine == "singularity":
                            nodejs_pull_commands.append("--force")
                        nodejs_pull_commands.append(nodeimg)
                        nodejsimg = subprocess.check_output(  # nosec
                            nodejs_pull_commands, universal_newlines=True
                        )
                        _logger.debug(
                            "Pulled Docker image %s %s using %s",
                            nodeimg,
                            nodejsimg,
                            container_engine,
                        )
                    self.have_node_slim = True
                nodejs_commands = [container_engine]
                if container_engine != "singularity":
                    nodejs_commands.extend(
                        [
                            "run",
                            "--attach=STDIN",
                            "--attach=STDOUT",
                            "--attach=STDERR",
                            "--sig-proxy=true",
                            "--interactive",
                            "--rm",
                        ]
                    )
                else:
                    nodejs_commands.extend(
                        [
                            "exec",
                            "--contain",
                            "--ipc",
                            "--cleanenv",
                            "--userns" if singularity_supports_userns() else "--pid",
                        ]
                    )
                nodejs_commands.extend(
                    [
                        nodeimg,
                        "node",
                        "--eval",
                        js_text,
                    ],
                )
                _logger.debug("Running nodejs via %s", nodejs_commands[:-1])
                nodejs = subprocess.Popen(  # nosec
                    nodejs_commands,
                    universal_newlines=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.processes_to_kill.append(nodejs)
                docker = True
            except OSError as e:
                if e.errno == errno.ENOENT:
                    pass
                else:
                    raise
            except subprocess.CalledProcessError:
                pass

        # docker failed and nodejs not on system
        if nodejs is None:
            raise JavascriptException(
                "NodeJSEngine requires Node.js engine to evaluate and validate "
                "Javascript expressions, but couldn't find it.  Tried {trynodes}, "
                f"{container_engine} run node:slim".format(
                    trynodes=", ".join(trynodes), container_engine=container_engine
                )
            )

        # docker failed, but nodejs is installed on system but the version is below the required version
        if docker is False and required_node_version is False:
            raise JavascriptException(
                "NodeJSEngine requires minimum v{} version of Node.js engine.".format(
                    self.minimum_node_version_str
                ),
                "Try updating: https://docs.npmjs.com/getting-started/installing-node",
            )

        return nodejs

    def eval(
        self,
        scan: str,
        jslib: str = "",
        timeout: float = default_timeout,
        force_docker_pull: bool = False,
        debug: bool = False,
        js_console: bool = False,
        container_engine: str = "docker",
        **kwargs: Any,
    ) -> CWLOutputType:
        fn = code_fragment_to_js(scan, jslib)
        returncode, stdout, stderr = self.exec_js_process(
            fn,
            timeout,
            js_console=js_console,
            force_docker_pull=force_docker_pull,
            container_engine=container_engine,
        )
        if js_console:
            if stderr is not None:
                _logger.info("Javascript console output:")
                _logger.info("----------------------------------------")
                _logger.info(
                    "\n".join(
                        re.findall(r"^[[](?:log|err)[]].*$", stderr, flags=re.MULTILINE)
                    )
                )
                _logger.info("----------------------------------------")
        if returncode != 0:
            if debug:
                info = (
                    "returncode was: %s\nscript was:\n%s\nstdout was: %s\nstderr was: %s\n"
                    % (returncode, linenum(fn), stdfmt(stdout), stdfmt(stderr))
                )
            else:
                info = "Javascript expression was: {}\nstdout was: {}\nstderr was: {}".format(
                    scan, stdfmt(stdout), stdfmt(stderr)
                )

            if returncode == -1:
                raise JavascriptException(
                    f"Long-running script killed after {timeout} seconds: {info}"
                )
            else:
                raise JavascriptException(info)
        try:
            return cast(CWLOutputType, json.loads(stdout))
        except ValueError as err:
            raise JavascriptException(
                "{}\nscript was:\n{}\nstdout was: '{}'\nstderr was: '{}'\n".format(
                    err, linenum(fn), stdout, stderr
                )
            ) from err

    def regex_eval(
        self,
        parsed_string: str,
        remaining_string: str,
        current_value: CWLOutputType,
        **kwargs: Any,
    ) -> CWLOutputType:
        if remaining_string:
            m = segment_re.match(remaining_string)
            if not m:
                return current_value
            next_segment_str = m.group(1)
            key = None  # type: Optional[Union[str, int]]
            if next_segment_str[0] == ".":
                key = next_segment_str[1:]
            elif next_segment_str[1] in ("'", '"'):
                key = next_segment_str[2:-2].replace("\\'", "'").replace('\\"', '"')
            if key is not None:
                if (
                    isinstance(current_value, MutableSequence)
                    and key == "length"
                    and not remaining_string[m.end(1) :]
                ):
                    return len(current_value)
                if not isinstance(current_value, MutableMapping):
                    raise WorkflowException(
                        "%s is a %s, cannot index on string '%s'"
                        % (parsed_string, type(current_value).__name__, key)
                    )
                if key not in current_value:
                    raise WorkflowException(
                        f"{parsed_string} does not contain key '{key}'"
                    )
            else:
                try:
                    key = int(next_segment_str[1:-1])
                except ValueError as v:
                    raise WorkflowException(str(v)) from v
                if not isinstance(current_value, MutableSequence):
                    raise WorkflowException(
                        "%s is a %s, cannot index on int '%s'"
                        % (parsed_string, type(current_value).__name__, key)
                    )
                if key and key >= len(current_value):
                    raise WorkflowException(
                        "%s list index %i out of range" % (parsed_string, key)
                    )

            if isinstance(current_value, Mapping):
                try:
                    return self.regex_eval(
                        parsed_string + remaining_string,
                        remaining_string[m.end(1) :],
                        cast(CWLOutputType, current_value[cast(str, key)]),
                    )
                except KeyError:
                    raise WorkflowException(
                        f"{parsed_string} doesn't have property {key}"
                    )
            elif isinstance(current_value, list) and isinstance(key, int):
                try:
                    return self.regex_eval(
                        parsed_string + remaining_string,
                        remaining_string[m.end(1) :],
                        current_value[key],
                    )
                except KeyError:
                    raise WorkflowException(
                        f"{parsed_string} doesn't have property {key}"
                    )
            else:
                raise WorkflowException(f"{parsed_string} doesn't have property {key}")
        else:
            return current_value


__js_engine: JSEngine = NodeJSEngine()


def get_js_engine() -> JSEngine:
    return __js_engine


def set_js_engine(js_engine: JSEngine) -> None:
    global __js_engine
    __js_engine = js_engine


# The following functions are maintained for compatibility purposes
def check_js_threshold_version(*args: Any, **kwargs: Any) -> bool:
    _check_js_threshold_version = getattr(
        get_js_engine(), "check_js_threshold_version", None
    )
    if callable(_check_js_threshold_version):
        return cast(bool, _check_js_threshold_version(*args, **kwargs))
    else:
        raise NotImplementedError(
            "Method check_js_threshold_version is not implemented in js engine {}".format(
                get_js_engine().__class__.__name__
            )
        )


def exec_js_process(*args: Any, **kwargs: Any) -> Tuple[int, str, str]:
    _exec_js_process = getattr(get_js_engine(), "exec_js_process", None)
    if callable(_exec_js_process):
        return cast(Tuple[int, str, str], _exec_js_process(*args, **kwargs))
    else:
        raise NotImplementedError(
            "Method exec_js_process is not implemented in js engine {}".format(
                get_js_engine().__class__.__name__
            )
        )


def new_js_proc(*args: Any, **kwargs: Any) -> "subprocess.Popen[str]":
    _new_js_proc = getattr(get_js_engine(), "new_js_proc", None)
    if callable(_new_js_proc):
        return cast("subprocess.Popen[str]", _new_js_proc(*args, **kwargs))
    else:
        raise NotImplementedError(
            "Method new_js_proc is not implemented in js engine {}".format(
                get_js_engine().__class__.__name__
            )
        )

import os
import subprocess
from subprocess import DEVNULL, PIPE, Popen, TimeoutExpired
from typing import Any, MutableMapping, MutableSequence, Union


_USERNS = None


def bytes2str_in_dicts(
    inp: Union[MutableMapping[str, Any], MutableSequence[Any], Any],
):
    # type: (...) -> Union[str, MutableSequence[Any], MutableMapping[str, Any]]
    """
    Convert any present byte string to unicode string, inplace.

    input is a dict of nested dicts and lists
    """
    # if input is dict, recursively call for each value
    if isinstance(inp, MutableMapping):
        for k in inp:
            inp[k] = bytes2str_in_dicts(inp[k])
        return inp

    # if list, iterate through list and fn call
    # for all its elements
    if isinstance(inp, MutableSequence):
        for idx, value in enumerate(inp):
            inp[idx] = bytes2str_in_dicts(value)
            return inp

    # if value is bytes, return decoded string,
    elif isinstance(inp, bytes):
        return inp.decode("utf-8")

    # simply return elements itself
    return inp


def kill_processes(processes_to_kill):
    while processes_to_kill:
        process = processes_to_kill.popleft()
        if isinstance(process.args, MutableSequence):
            args = process.args
        else:
            args = [process.args]
        cidfile = [str(arg).split("=")[1] for arg in args if "--cidfile" in str(arg)]
        if cidfile:  # Try to be nice
            try:
                with open(cidfile[0]) as inp_stream:
                    p = subprocess.Popen(  # nosec
                        ["docker", "kill", inp_stream.read()], shell=False  # nosec
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


def singularity_supports_userns() -> bool:
    """Confirm if the version of Singularity install supports the --userns flag."""
    global _USERNS  # pylint: disable=global-statement
    if _USERNS is None:
        try:
            hello_image = os.path.join(os.path.dirname(__file__), "hello.simg")
            result = Popen(  # nosec
                ["singularity", "exec", "--userns", hello_image, "true"],
                stderr=PIPE,
                stdout=DEVNULL,
                universal_newlines=True,
            ).communicate(timeout=60)[1]
            _USERNS = (
                "No valid /bin/sh" in result
                or "/bin/sh doesn't exist in container" in result
                or "executable file not found in" in result
            )
        except TimeoutExpired:
            _USERNS = False
    return _USERNS

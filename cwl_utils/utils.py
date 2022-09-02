# SPDX-License-Identifier: Apache-2.0
"""Miscellaneous utility functions."""
import os
import pathlib
import subprocess  # nosec
import sys
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from typing import (
    Any,
    Dict,
    List,
    MutableMapping,
    MutableSequence,
    Optional,
    Tuple,
    Union,
)

from ruamel.yaml.main import YAML
from ruamel.yaml.parser import ParserError
from ruamel.yaml.scanner import ScannerError

from cwl_utils.errors import MissingKeyField
from cwl_utils.loghandler import _logger

fast_yaml = YAML(typ="safe")

_USERNS = None


def _is_github_symbolic_link(base_url: urllib.parse.ParseResult, contents: str) -> bool:
    """Look for remote path with contents that is a single line with no new
    line with an extension.

    https://github.com/rabix/sbpack/blob/b8404a0859ffcbe1edae6d8f934e51847b003320/sbpack/lib.py
    """
    if base_url.scheme in ["file://", ""]:
        return False

    idx = contents.find("\n")
    if idx > -1:
        return False

    if "." not in contents:
        return False

    return True


def bytes2str_in_dicts(
    inp: Union[MutableMapping[str, Any], MutableSequence[Any], Any],
) -> Union[str, MutableSequence[Any], MutableMapping[str, Any]]:
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


def load_linked_file(
    base_url: urllib.parse.ParseResult, link: str, is_import: bool = False
) -> Tuple[Any, urllib.parse.ParseResult]:
    """From https://github.com/rabix/sbpack/blob/b8404a0859ffcbe1edae6d8f934e51847b003320/sbpack/lib.py"""
    new_url = resolved_path(base_url, link)

    if new_url.scheme in ["file://", ""]:
        contents = pathlib.Path(new_url.path).open().read()
    else:
        try:
            contents = (
                urllib.request.urlopen(new_url.geturl()).read().decode("utf-8")  # nosec
            )
        except urllib.error.HTTPError as e:
            _logger.error("Could not find linked file: %s", new_url.geturl())
            raise SystemExit(e)

    if _is_github_symbolic_link(new_url, contents):
        # This is an exception for symbolic links on github
        sys.stderr.write(
            f"{new_url.geturl()}: found file-like string in contents.\n"
            f"Treating as github symbolic link to {contents}\n"
        )
        return load_linked_file(new_url, contents, is_import=is_import)

    if is_import:
        try:
            _node = fast_yaml.load(contents)
        except ParserError as e:
            e.context = f"\n===\nMalformed file: {new_url.geturl()}\n===\n" + e.context
            raise SystemExit(e)
        except ScannerError as e:
            e.problem = f"\n===\nMalformed file: {new_url.geturl()}\n===\n" + e.problem
            raise SystemExit(e)

    else:
        _node = contents

    return _node, new_url


def normalize_to_map(
    obj: Union[List[Any], Dict[str, Any]], key_field: str
) -> Dict[str, Any]:
    """From https://github.com/rabix/sbpack/blob/b8404a0859ffcbe1edae6d8f934e51847b003320/sbpack/lib.py"""
    if isinstance(obj, dict):
        return deepcopy(obj)
    elif isinstance(obj, list):
        map_obj = {}
        for v in obj:
            if not isinstance(v, dict):
                raise RuntimeError("Expecting a dict here")
            k = v.get(key_field)
            if k is None:
                raise MissingKeyField(key_field)
            v.pop(key_field, None)
            map_obj[k] = v
        return map_obj
    else:
        raise RuntimeError("Expecting a dictionary or a list here")


def normalize_to_list(
    obj: Union[List[Any], Dict[str, Any]], key_field: str, value_field: Optional[str]
) -> List[Any]:
    """From https://github.com/rabix/sbpack/blob/b8404a0859ffcbe1edae6d8f934e51847b003320/sbpack/lib.py"""
    if isinstance(obj, list):
        return deepcopy(obj)
    elif isinstance(obj, dict):
        map_list = []
        for k, v in obj.items():
            if not isinstance(v, dict):
                if value_field is None:
                    raise RuntimeError(f"Expecting a dict here, got {v}")
                v = {value_field: v}
            v.update({key_field: k})
            map_list += [v]
        return map_list
    else:
        raise RuntimeError("Expecting a dictionary or a list here")


def resolved_path(
    base_url: urllib.parse.ParseResult, link: str
) -> urllib.parse.ParseResult:
    """
    Given a base_url ("this document") and a link ("string in this document")
    return a new url (urllib.parse.ParseResult) that allows us to retrieve the
    linked document. This function will
    1. Resolve the path, which means dot and double dot components are resolved
    2. Use the OS appropriate path resolution for local paths, and network
       appropriate resolution for network paths

    From https://github.com/rabix/sbpack/blob/b8404a0859ffcbe1edae6d8f934e51847b003320/sbpack/lib.py
    """
    link_url = urllib.parse.urlparse(link)
    # The link will always Posix

    if link_url.scheme == "file://":
        # Absolute local path
        return link_url

    elif link_url.scheme == "":
        # Relative path, can be local or remote
        if base_url.scheme in ["file://", ""]:
            # Local relative path
            if link == "":
                return base_url
            else:
                return base_url._replace(
                    path=str(
                        (
                            pathlib.Path(base_url.path).parent / pathlib.Path(link)
                        ).resolve()
                    )
                )

        else:
            # Remote relative path
            return urllib.parse.urlparse(
                urllib.parse.urljoin(base_url.geturl(), link_url.path)
            )
            # We need urljoin because we need to resolve relative links in a
            # platform independent manner

    # Absolute remote path
    return link_url


def singularity_supports_userns() -> bool:
    """Confirm if the version of Singularity install supports the --userns flag."""
    global _USERNS  # pylint: disable=global-statement
    if _USERNS is None:
        try:
            hello_image = os.path.join(os.path.dirname(__file__), "hello.simg")
            result = subprocess.Popen(  # nosec
                ["singularity", "exec", "--userns", hello_image, "true"],
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                universal_newlines=True,
            ).communicate(timeout=60)[1]
            _USERNS = (
                "No valid /bin/sh" in result
                or "/bin/sh doesn't exist in container" in result
                or "executable file not found in" in result
            )
        except subprocess.TimeoutExpired:
            _USERNS = False
    return _USERNS

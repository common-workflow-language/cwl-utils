# SPDX-License-Identifier: Apache-2.0
# From https://github.com/rabix/sbpack/blob/b8404a0859ffcbe1edae6d8f934e51847b003320/sbpack/lib.py
"""Shared Python type definitions for commons JSON like CWL objects."""
import sys
from collections.abc import Mapping, MutableMapping, MutableSequence
from typing import Any, Literal, TypeAlias, TypedDict, TypeGuard

if sys.version_info >= (3, 13):
    from typing import TypeIs
else:
    from typing_extensions import TypeIs

if sys.version_info >= (3, 11):
    from typing import Required
else:
    from typing_extensions import Required


built_in_types: list[str] = [
    "null",
    "boolean",
    "int",
    "long",
    "float",
    "double",
    "string",
    "File",
    "Directory",
    "stdin",
    "stdout",
    "stderr",
    "Any",
]


CWLDirectoryType = TypedDict(
    "CWLDirectoryType",
    {
        "class": Required[Literal["Directory"]],
        "location": str,
        "path": str,
        "basename": str,
        "listing": MutableSequence["CWLFileType | CWLDirectoryType"],
    },
    total=False,
)


CWLFileType = TypedDict(
    "CWLFileType",
    {
        "class": Required[Literal["File"]],
        "location": str,
        "path": str,
        "basename": str,
        "dirname": str,
        "nameroot": str,
        "nameext": str,
        "checksum": str,
        "size": int,
        "secondaryFiles": MutableSequence["CWLFileType | CWLDirectoryType"],
        "format": str,
        "contents": str,
    },
    total=False,
)


CWLOutputType: TypeAlias = (
    bool
    | str
    | int
    | float
    | CWLFileType
    | CWLDirectoryType
    | MutableSequence["CWLOutputType | None"]
    | MutableMapping[str, "CWLOutputType | None"]
)
CWLObjectType: TypeAlias = MutableMapping[str, CWLOutputType | None]
SinkType: TypeAlias = CWLOutputType | CWLObjectType


class CWLRuntimeParameterContext(TypedDict, total=False):
    outdir: str
    tmpdir: str
    cores: float | str
    ram: float | str
    outdirSize: float | str
    tmpdirSize: float | str
    exitCode: int


class CWLParameterContext(TypedDict, total=False):
    inputs: CWLObjectType
    self: CWLOutputType | None
    runtime: CWLRuntimeParameterContext


class DirentType(TypedDict, total=False):
    entry: Required[str]
    entryname: str
    writable: bool


def is_cwl_parameter_context_key(
    key: Any,
) -> TypeGuard[Literal["inputs", "self", "runtime"]]:
    return key in ("inputs", "self", "runtime")


def is_directory(value: Any) -> TypeIs[CWLDirectoryType]:
    return isinstance(value, Mapping) and value.get("class") == "Directory"


def is_directory_key(
    key: Any,
) -> TypeGuard[Literal["class", "location", "path", "basename", "listing"]]:
    return key in ("class", "location", "path", "basename", "listing")


def is_file(value: Any) -> TypeIs[CWLFileType]:
    return isinstance(value, Mapping) and value.get("class") == "File"


def is_file_key(
    key: Any,
) -> TypeGuard[
    Literal[
        "class",
        "location",
        "path",
        "basename",
        "dirname",
        "nameroot",
        "nameext",
        "checksum",
        "size",
        "secondaryFiles",
        "format",
        "contents",
    ]
]:
    return key in (
        "class",
        "location",
        "path",
        "basename",
        "dirname",
        "nameroot",
        "nameext",
        "checksum",
        "size",
        "secondaryFiles",
        "format",
        "contents",
    )


def is_file_or_directory(
    value: Any,
) -> TypeIs[CWLFileType | CWLDirectoryType]:
    return isinstance(value, Mapping) and value.get("class") in ("File", "Directory")

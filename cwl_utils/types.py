# SPDX-License-Identifier: Apache-2.0
# From https://github.com/rabix/sbpack/blob/b8404a0859ffcbe1edae6d8f934e51847b003320/sbpack/lib.py
"""Shared Python type definitions for commons JSON like CWL objects."""
from collections.abc import MutableMapping, MutableSequence
from typing import TypeAlias, TypedDict

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


CWLOutputAtomType: TypeAlias = (
    None
    | bool
    | str
    | int
    | float
    | MutableSequence["CWLOutputAtomType"]
    | MutableMapping[str, "CWLOutputAtomType"]
)
CWLOutputType: TypeAlias = (
    bool
    | str
    | int
    | float
    | MutableSequence[CWLOutputAtomType]
    | MutableMapping[str, CWLOutputAtomType]
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


class CWLParameterContext(TypedDict, total=False):
    inputs: CWLObjectType
    self: CWLOutputType | None
    runtime: CWLRuntimeParameterContext

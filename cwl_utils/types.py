# SPDX-License-Identifier: Apache-2.0
# From https://github.com/rabix/sbpack/blob/b8404a0859ffcbe1edae6d8f934e51847b003320/sbpack/lib.py
"""Shared Python type definitions for commons JSON like CWL objects."""
from typing import Any, MutableMapping, MutableSequence, Optional, Union

built_in_types = [
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


CWLOutputAtomType = Union[
    None,
    bool,
    str,
    int,
    float,
    MutableSequence[
        Union[
            None, bool, str, int, float, MutableSequence[Any], MutableMapping[str, Any]
        ]
    ],
    MutableMapping[
        str,
        Union[
            None, bool, str, int, float, MutableSequence[Any], MutableMapping[str, Any]
        ],
    ],
]
CWLOutputType = Union[
    bool,
    str,
    int,
    float,
    MutableSequence[CWLOutputAtomType],
    MutableMapping[str, CWLOutputAtomType],
]
CWLObjectType = MutableMapping[str, Optional[CWLOutputType]]

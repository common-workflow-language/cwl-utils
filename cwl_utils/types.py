from typing import Any, MutableMapping, MutableSequence, Optional, Union

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

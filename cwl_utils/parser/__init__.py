# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
from typing import Any, MutableMapping, MutableSequence, Optional, Union, cast
from urllib.parse import unquote_plus, urlparse

from schema_salad.exceptions import ValidationException
from schema_salad.utils import yaml_no_ts

from ..errors import GraphTargetMissingException
from . import cwl_v1_0, cwl_v1_1, cwl_v1_2

LoadingOptions = Union[
    cwl_v1_0.LoadingOptions, cwl_v1_1.LoadingOptions, cwl_v1_2.LoadingOptions
]
Savable = Union[cwl_v1_0.Savable, cwl_v1_1.Savable, cwl_v1_2.Savable]
Workflow = Union[cwl_v1_0.Workflow, cwl_v1_1.Workflow, cwl_v1_2.Workflow]
WorkflowTypes = (cwl_v1_0.Workflow, cwl_v1_1.Workflow, cwl_v1_2.Workflow)
WorkflowStep = Union[
    cwl_v1_0.WorkflowStep, cwl_v1_1.WorkflowStep, cwl_v1_2.WorkflowStep
]
CommandLineTool = Union[
    cwl_v1_0.CommandLineTool, cwl_v1_1.CommandLineTool, cwl_v1_2.CommandLineTool
]
ExpressionTool = Union[
    cwl_v1_0.ExpressionTool, cwl_v1_1.ExpressionTool, cwl_v1_2.ExpressionTool
]
DockerRequirement = Union[
    cwl_v1_0.DockerRequirement, cwl_v1_1.DockerRequirement, cwl_v1_2.DockerRequirement
]
DockerRequirementTypes = (
    cwl_v1_0.DockerRequirement,
    cwl_v1_1.DockerRequirement,
    cwl_v1_2.DockerRequirement,
)
_Loader = Union[cwl_v1_0._Loader, cwl_v1_1._Loader, cwl_v1_2._Loader]


def _get_id_from_graph(yaml: MutableMapping[str, Any], id_: Optional[str]) -> Any:
    if id_ is None:
        id_ = "main"
    for el in yaml["$graph"]:
        if el["id"].lstrip("#") == id_:
            return el
    raise GraphTargetMissingException(
        "Tool file contains graph of multiple objects, must specify "
        "one of #%s" % ", #".join(el["id"] for el in yaml["$graph"])
    )


def cwl_version(yaml: Any) -> Optional[str]:
    """Return the cwlVersion of a YAML object.

    Args:
        yaml: A YAML object

    Raises:
        ValidationException: If `yaml` is not a MutableMapping.
    """
    if not isinstance(yaml, MutableMapping):
        raise ValidationException("MutableMapping is required")
    if "cwlVersion" not in list(yaml.keys()):
        return None
    return cast(str, yaml["cwlVersion"])


def load_document_by_uri(
    path: Union[str, Path],
    loadingOptions: Optional[LoadingOptions] = None,
) -> Any:
    """Load a CWL object from a URI or a path."""
    if isinstance(path, str):
        uri = urlparse(path)
        id_ = uri.fragment or None
        if not uri.scheme or uri.scheme == "file":
            real_path = Path(unquote_plus(uri.path)).resolve().as_uri()
        else:
            real_path = path
    else:
        real_path = path.resolve().as_uri()
        id_ = path.resolve().name.split("#")[1] if "#" in path.resolve().name else None

    baseuri = str(real_path)

    if loadingOptions is None:
        loadingOptions = cwl_v1_2.LoadingOptions(fileuri=baseuri)

    doc = loadingOptions.fetcher.fetch_text(real_path)
    return load_document_by_string(doc, baseuri, loadingOptions, id_)


def load_document(
    doc: Any,
    baseuri: Optional[str] = None,
    loadingOptions: Optional[LoadingOptions] = None,
    id_: Optional[str] = None,
) -> Any:
    """Load a CWL object from a serialized YAML string or a YAML object."""
    if baseuri is None:
        baseuri = cwl_v1_0.file_uri(os.getcwd()) + "/"
    if isinstance(doc, str):
        return load_document_by_string(doc, baseuri, loadingOptions, id_)
    return load_document_by_yaml(doc, baseuri, loadingOptions, id_)


def load_document_by_string(
    string: str,
    uri: str,
    loadingOptions: Optional[LoadingOptions] = None,
    id_: Optional[str] = None,
) -> Any:
    """Load a CWL object from a serialized YAML string."""
    yaml = yaml_no_ts()
    result = yaml.load(string)
    return load_document_by_yaml(result, uri, loadingOptions, id_)


def load_document_by_yaml(
    yaml: Any,
    uri: str,
    loadingOptions: Optional[LoadingOptions] = None,
    id_: Optional[str] = None,
) -> Any:
    """Load a CWL object from a YAML object."""
    version = cwl_version(yaml)
    if "$graph" in yaml:
        yaml = _get_id_from_graph(yaml, id_)
        yaml["cwlVersion"] = version
    if version == "v1.0":
        result = cwl_v1_0.load_document_by_yaml(
            yaml, uri, cast(Optional[cwl_v1_0.LoadingOptions], loadingOptions)
        )
    elif version == "v1.1":
        result = cwl_v1_1.load_document_by_yaml(
            yaml, uri, cast(Optional[cwl_v1_1.LoadingOptions], loadingOptions)
        )
    elif version == "v1.2":
        result = cwl_v1_2.load_document_by_yaml(
            yaml, uri, cast(Optional[cwl_v1_2.LoadingOptions], loadingOptions)
        )
    elif version is None:
        raise ValidationException("could not get the cwlVersion")
    else:
        raise ValidationException(
            f"Version error. Did not recognise {version} as a CWL version"
        )

    if isinstance(result, MutableSequence):
        lst = []
        for r in result:
            if "cwlVersion" in r.attrs:
                r.cwlVersion = version
            lst.append(r)
        return lst
    return result


def save(
    val: Optional[Union[Savable, MutableSequence[Savable]]],
    top: bool = True,
    base_url: str = "",
    relative_uris: bool = True,
) -> Any:
    """Convert a given CWL object into a built-in typed object."""
    if (
        isinstance(val, cwl_v1_0.Savable)
        or isinstance(val, cwl_v1_1.Savable)
        or isinstance(val, cwl_v1_2.Savable)
    ):
        return val.save(top=top, base_url=base_url, relative_uris=relative_uris)
    if isinstance(val, MutableSequence):
        lst = [
            save(v, top=top, base_url=base_url, relative_uris=relative_uris)
            for v in val
        ]
        if top and all(is_process(v) for v in val):
            vers = [
                e.get("cwlVersion") for i, e in enumerate(lst) if is_process(val[i])
            ]
            latest = max(
                (v for v in vers if v is not None), key=cast(Any, version_split)
            )
            return {"cwlVersion": latest, "$graph": lst}
        return lst
    if isinstance(val, MutableMapping):
        newdict = {}
        for key in val:
            newdict[key] = save(
                val[key], top=False, base_url=base_url, relative_uris=relative_uris
            )
        return newdict
    return val


def is_process(v: Any) -> bool:
    return (
        isinstance(v, cwl_v1_0.Process)
        or isinstance(v, cwl_v1_1.Process)
        or isinstance(v, cwl_v1_2.Process)
    )


def version_split(version: str) -> MutableSequence[int]:
    return [int(v) for v in version[1:].split(".")]

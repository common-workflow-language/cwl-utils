# SPDX-License-Identifier: Apache-2.0

import os
from abc import ABC
from collections.abc import MutableMapping, MutableSequence, Sequence
from pathlib import Path
from typing import Any, Literal, Optional, TypeAlias, cast
from urllib.parse import unquote_plus, urlparse

from schema_salad.exceptions import ValidationException
from schema_salad.utils import yaml_no_ts

from ..errors import GraphTargetMissingException
from . import cwl_v1_0, cwl_v1_1, cwl_v1_2


class NoType(ABC):
    pass


LoadingOptions: TypeAlias = (
    cwl_v1_0.LoadingOptions | cwl_v1_1.LoadingOptions | cwl_v1_2.LoadingOptions
)
"""Type union for a CWL v1.x LoadingOptions object."""
Saveable: TypeAlias = cwl_v1_0.Saveable | cwl_v1_1.Saveable | cwl_v1_2.Saveable
"""Type union for a CWL v1.x Saveable object."""
InputParameter: TypeAlias = (
    cwl_v1_0.InputParameter | cwl_v1_1.InputParameter | cwl_v1_2.InputParameter
)
"""Type union for a CWL v1.x InputEnumSchema object."""
InputRecordField: TypeAlias = (
    cwl_v1_0.InputRecordField | cwl_v1_1.InputRecordField | cwl_v1_2.InputRecordField
)
"""Type union for a CWL v1.x InputRecordSchema object."""
InputSchema: TypeAlias = (
    cwl_v1_0.InputSchema | cwl_v1_1.InputSchema | cwl_v1_2.InputSchema
)
"""Type union for a CWL v1.x InputSchema object."""
OutputParameter: TypeAlias = (
    cwl_v1_0.OutputParameter | cwl_v1_1.OutputParameter | cwl_v1_2.OutputParameter
)
"""Type union for a CWL v1.x OutputParameter object."""
OutputArraySchema: TypeAlias = (
    cwl_v1_0.OutputArraySchema | cwl_v1_1.OutputArraySchema | cwl_v1_2.OutputArraySchema
)
"""Type union for a CWL v1.x OutputArraySchema object."""
OutputArraySchemaTypes = (
    cwl_v1_0.OutputArraySchema,
    cwl_v1_1.OutputArraySchema,
    cwl_v1_2.OutputArraySchema,
)
OutputEnumSchema: TypeAlias = (
    cwl_v1_0.OutputEnumSchema | cwl_v1_1.OutputEnumSchema | cwl_v1_2.OutputEnumSchema
)
"""Type union for a CWL v1.x OutputEnumSchema object."""
OutputEnumSchemaTypes = (
    cwl_v1_0.OutputEnumSchema,
    cwl_v1_1.OutputEnumSchema,
    cwl_v1_2.OutputEnumSchema,
)
OutputRecordField: TypeAlias = (
    cwl_v1_0.OutputRecordField | cwl_v1_1.OutputRecordField | cwl_v1_2.OutputRecordField
)
"""Type union for a CWL v1.x OutputRecordField object."""
OutputRecordSchema: TypeAlias = (
    cwl_v1_0.OutputRecordSchema
    | cwl_v1_1.OutputRecordSchema
    | cwl_v1_2.OutputRecordSchema
)
"""Type union for a CWL v1.x OutputRecordSchema object."""
OutputRecordSchemaTypes = (
    cwl_v1_0.OutputRecordSchema,
    cwl_v1_1.OutputRecordSchema,
    cwl_v1_2.OutputRecordSchema,
)
OutputSchema: TypeAlias = (
    cwl_v1_0.OutputSchema | cwl_v1_1.OutputSchema | cwl_v1_2.OutputSchema
)
BasicOutputTypeSchemas: TypeAlias = (
    OutputArraySchema
    | OutputEnumSchema
    | OutputRecordSchema
    | str
    | Literal[
        "null",
        "boolean",
        "int",
        "long",
        "float",
        "double",
        "string",
        "File",
        "Directory",
        "stderr",
        "stdout",
    ]
)
OutputTypeSchemas: TypeAlias = BasicOutputTypeSchemas | Sequence[BasicOutputTypeSchemas]
"""Type union for a CWL v1.x OutputSchema object."""
Workflow: TypeAlias = cwl_v1_0.Workflow | cwl_v1_1.Workflow | cwl_v1_2.Workflow
WorkflowTypes = (cwl_v1_0.Workflow, cwl_v1_1.Workflow, cwl_v1_2.Workflow)
"""Type union for a CWL v1.x Workflow object."""
WorkflowInputParameter: TypeAlias = (
    cwl_v1_0.InputParameter
    | cwl_v1_1.WorkflowInputParameter
    | cwl_v1_2.WorkflowInputParameter
)
"""Type union for a CWL v1.x WorkflowInputParameter object."""
WorkflowOutputParameter: TypeAlias = (
    cwl_v1_0.WorkflowOutputParameter
    | cwl_v1_1.WorkflowOutputParameter
    | cwl_v1_2.WorkflowOutputParameter
)
"""Type union for a CWL v1.x WorkflowOutputParameter object."""
WorkflowStep: TypeAlias = (
    cwl_v1_0.WorkflowStep | cwl_v1_1.WorkflowStep | cwl_v1_2.WorkflowStep
)
"""Type union for a CWL v1.x WorkflowStep object."""
ScatterWorkflowStep: TypeAlias = (
    cwl_v1_0.WorkflowStep | cwl_v1_1.WorkflowStep | cwl_v1_2.WorkflowStep
)
"""Type union for a CWL v1.x ScatterWorkflowStep object."""
LoopWorkflowStep: TypeAlias = NoType
"""Type union for a CWL v1.x LoopWorkflowStep object."""
WorkflowStepInput: TypeAlias = (
    cwl_v1_0.WorkflowStepInput | cwl_v1_1.WorkflowStepInput | cwl_v1_2.WorkflowStepInput
)
"""Type union for a CWL v1.x WorkflowStepInput object."""
WorkflowStepOutput: TypeAlias = (
    cwl_v1_0.WorkflowStepOutput
    | cwl_v1_1.WorkflowStepOutput
    | cwl_v1_2.WorkflowStepOutput
)
"""Type union for a CWL v1.x WorkflowStepOutput object."""
CommandLineTool: TypeAlias = (
    cwl_v1_0.CommandLineTool | cwl_v1_1.CommandLineTool | cwl_v1_2.CommandLineTool
)
CommandLineToolTypes = (
    cwl_v1_0.CommandLineTool,
    cwl_v1_1.CommandLineTool,
    cwl_v1_2.CommandLineTool,
)
"""Type union for a CWL v1.x CommandLineTool object."""
CommandLineBinding: TypeAlias = (
    cwl_v1_0.CommandLineBinding
    | cwl_v1_1.CommandLineBinding
    | cwl_v1_2.CommandLineBinding
)

"""Type union for a CWL v1.x CommandLineBinding object."""
CommandOutputBinding: TypeAlias = (
    cwl_v1_0.CommandOutputBinding
    | cwl_v1_1.CommandOutputBinding
    | cwl_v1_2.CommandOutputBinding
)
"""Type union for a CWL v1.x CommandOutputBinding object."""
CommandInputParameter: TypeAlias = (
    cwl_v1_0.CommandInputParameter
    | cwl_v1_1.CommandInputParameter
    | cwl_v1_2.CommandInputParameter
)
"""Type union for a CWL v1.x CommandInputParameter object."""
CommandOutputParameter: TypeAlias = (
    cwl_v1_0.CommandOutputParameter
    | cwl_v1_1.CommandOutputParameter
    | cwl_v1_2.CommandOutputParameter
)

"""Type union for a CWL v1.x CommandOutputParameter object."""
CommandOutputRecordField: TypeAlias = (
    cwl_v1_0.CommandOutputRecordField
    | cwl_v1_1.CommandOutputRecordField
    | cwl_v1_2.CommandOutputRecordField
)
"""Type union for a CWL v1.x CommandOutputRecordField object."""
ExpressionTool: TypeAlias = (
    cwl_v1_0.ExpressionTool | cwl_v1_1.ExpressionTool | cwl_v1_2.ExpressionTool
)
"""Type union for a CWL v1.x ExpressionTool object."""
ExpressionToolOutputParameter: TypeAlias = (
    cwl_v1_0.ExpressionToolOutputParameter
    | cwl_v1_1.ExpressionToolOutputParameter
    | cwl_v1_2.ExpressionToolOutputParameter
)
"""Type union for a CWL v1.x ExpressionToolOutputParameter object."""
DockerRequirement: TypeAlias = (
    cwl_v1_0.DockerRequirement | cwl_v1_1.DockerRequirement | cwl_v1_2.DockerRequirement
)
DockerRequirementTypes = (
    cwl_v1_0.DockerRequirement,
    cwl_v1_1.DockerRequirement,
    cwl_v1_2.DockerRequirement,
)
"""Type union for a CWL v1.x DockerRequirement object."""
Process: TypeAlias = Workflow | CommandLineTool | ExpressionTool | cwl_v1_2.Operation
"""Type Union for a CWL v1.x Process object."""
ProcessRequirement: TypeAlias = (
    cwl_v1_0.ProcessRequirement
    | cwl_v1_1.ProcessRequirement
    | cwl_v1_2.ProcessRequirement
)
"""Type Union for a CWL v1.x ProcessRequirement object."""
ProcessRequirementTypes = (
    cwl_v1_0.ProcessRequirement,
    cwl_v1_1.ProcessRequirement,
    cwl_v1_2.ProcessRequirement,
)
SoftwareRequirement: TypeAlias = (
    cwl_v1_0.SoftwareRequirement
    | cwl_v1_1.SoftwareRequirement
    | cwl_v1_2.SoftwareRequirement
)
SoftwareRequirementTypes = (
    cwl_v1_0.SoftwareRequirement,
    cwl_v1_1.SoftwareRequirement,
    cwl_v1_2.SoftwareRequirement,
)
"""Type union for a CWL v1.x SoftwareRequirement object."""
ArraySchema: TypeAlias = (
    cwl_v1_0.ArraySchema | cwl_v1_1.ArraySchema | cwl_v1_2.ArraySchema
)
InputArraySchema: TypeAlias = (
    cwl_v1_0.InputArraySchema | cwl_v1_1.InputArraySchema | cwl_v1_2.InputArraySchema
)
InputArraySchemaTypes = (
    cwl_v1_0.InputArraySchema,
    cwl_v1_1.InputArraySchema,
    cwl_v1_2.InputArraySchema,
)
"""Type Union for a CWL v1.x ArraySchema object."""
EnumSchema: TypeAlias = cwl_v1_0.EnumSchema | cwl_v1_1.EnumSchema | cwl_v1_2.EnumSchema
InputEnumSchema: TypeAlias = (
    cwl_v1_0.InputEnumSchema | cwl_v1_1.InputEnumSchema | cwl_v1_2.InputEnumSchema
)
InputEnumSchemaTypes = (
    cwl_v1_0.InputEnumSchema,
    cwl_v1_1.InputEnumSchema,
    cwl_v1_2.InputEnumSchema,
)
"""Type Union for a CWL v1.x EnumSchema object."""
RecordSchema: TypeAlias = (
    cwl_v1_0.RecordSchema | cwl_v1_1.RecordSchema | cwl_v1_2.RecordSchema
)
InputRecordSchema: TypeAlias = (
    cwl_v1_0.InputRecordSchema | cwl_v1_1.InputRecordSchema | cwl_v1_2.InputRecordSchema
)
InputRecordSchemaTypes = (
    cwl_v1_0.InputRecordSchema,
    cwl_v1_1.InputRecordSchema,
    cwl_v1_2.InputRecordSchema,
)
"""Type Union for a CWL v1.x RecordSchema object."""

BasicInputTypeSchemas: TypeAlias = (
    InputArraySchema
    | InputEnumSchema
    | InputRecordSchema
    | str
    | Literal[
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
    ]
)
InputTypeSchemas: TypeAlias = BasicInputTypeSchemas | Sequence[BasicInputTypeSchemas]

File: TypeAlias = cwl_v1_0.File | cwl_v1_1.File | cwl_v1_2.File
"""Type Union for a CWL v1.x File object."""
SecondaryFileSchema: TypeAlias = (
    cwl_v1_1.SecondaryFileSchema | cwl_v1_2.SecondaryFileSchema
)
"""Type Union for a CWL v1.x SecondaryFileSchema object."""
Directory: TypeAlias = cwl_v1_0.Directory | cwl_v1_1.Directory | cwl_v1_2.Directory
"""Type Union for a CWL v1.x Directory object."""
Dirent: TypeAlias = cwl_v1_0.Dirent | cwl_v1_1.Dirent | cwl_v1_2.Dirent
"""Type Union for a CWL v1.x Dirent object."""
LoadContents: TypeAlias = cwl_v1_1.LoadContents | cwl_v1_2.LoadContents
"""Type Union for a CWL v1.x LoadContents object."""
SchemaDefRequirement: TypeAlias = (
    cwl_v1_0.SchemaDefRequirement
    | cwl_v1_1.SchemaDefRequirement
    | cwl_v1_2.SchemaDefRequirement
)
"""Type Union for a CWL v1.x SchemaDefRequirement object."""
_Loader: TypeAlias = cwl_v1_0._Loader | cwl_v1_1._Loader | cwl_v1_2._Loader
"""Type union for a CWL v1.x _Loader."""


def _get_id_from_graph(yaml: MutableMapping[str, Any], id_: str | None) -> Any:
    if id_ is None:
        id_ = "main"
    for el in yaml["$graph"]:
        if el["id"].lstrip("#") == id_:
            return el
    raise GraphTargetMissingException(
        "Tool file contains graph of multiple objects, must specify "
        "one of #%s" % ", #".join(el["id"] for el in yaml["$graph"])
    )


def cwl_version(yaml: Any) -> str | None:
    """
    Return the cwlVersion of a YAML object.

    :param yaml: ruamel.yaml object for a CWL document

    :raises ValidationException: If `yaml` is not a MutableMapping.
    """
    if not isinstance(yaml, MutableMapping):
        raise ValidationException("MutableMapping is required")
    if "cwlVersion" not in list(yaml.keys()):
        return None
    return cast(str, yaml["cwlVersion"])


def load_document_by_uri(
    path: str | Path,
    loadingOptions: LoadingOptions | None = None,
    load_all: bool = False,
) -> Any:
    """Load a CWL object from a URI or a path."""
    if isinstance(path, str):
        uri = urlparse(path)
        id_ = uri.fragment or None
        if not uri.scheme or uri.scheme == "file":
            real_uri = Path(unquote_plus(uri.path)).resolve().as_uri()
            base_uri = Path(unquote_plus(uri.path)).resolve().parent.as_uri()
        else:
            real_uri = path
            base_uri = os.path.dirname(path)
    else:
        real_uri = path.resolve().as_uri()
        base_uri = path.resolve().parent.as_uri()
        id_ = path.resolve().name.split("#")[1] if "#" in path.resolve().name else None

    match loadingOptions:
        case cwl_v1_0.LoadingOptions():
            loadingOptions = cwl_v1_0.LoadingOptions(
                fileuri=real_uri, baseuri=base_uri, copyfrom=loadingOptions
            )
            return load_document_by_string(
                loadingOptions.fetcher.fetch_text(real_uri),
                real_uri,
                loadingOptions,
                id_,
                load_all,
            )
        case cwl_v1_1.LoadingOptions():
            loadingOptions = cwl_v1_1.LoadingOptions(
                fileuri=real_uri, baseuri=base_uri, copyfrom=loadingOptions
            )
            return load_document_by_string(
                loadingOptions.fetcher.fetch_text(real_uri),
                real_uri,
                loadingOptions,
                id_,
                load_all,
            )
        case cwl_v1_2.LoadingOptions():
            loadingOptions = cwl_v1_2.LoadingOptions(
                fileuri=real_uri, baseuri=base_uri, copyfrom=loadingOptions
            )
            return load_document_by_string(
                loadingOptions.fetcher.fetch_text(real_uri),
                real_uri,
                loadingOptions,
                id_,
                load_all,
            )
        case None:
            loadingOptions = cwl_v1_2.LoadingOptions(fileuri=real_uri, baseuri=base_uri)
            return load_document_by_string(
                loadingOptions.fetcher.fetch_text(real_uri),
                real_uri,
                None,
                id_,
                load_all,
            )
        case _:
            raise ValidationException(
                f"Unsupported loadingOptions type: {type(loadingOptions)}"
            )


def load_document(
    doc: Any,
    baseuri: str | None = None,
    loadingOptions: LoadingOptions | None = None,
    id_: str | None = None,
    load_all: bool = False,
) -> Any:
    """Load a CWL object from a serialized YAML string or a YAML object."""
    if baseuri is None:
        baseuri = cwl_v1_0.file_uri(str(Path.cwd())) + "/"
    if isinstance(doc, str):
        return load_document_by_string(doc, baseuri, loadingOptions, id_)
    return load_document_by_yaml(doc, baseuri, loadingOptions, id_, load_all)


def load_document_by_string(
    string: str,
    uri: str,
    loadingOptions: LoadingOptions | None = None,
    id_: str | None = None,
    load_all: bool = False,
) -> Any:
    """Load a CWL object from a serialized YAML string."""
    result = yaml_no_ts().load(string)
    return load_document_by_yaml(result, uri, loadingOptions, id_, load_all)


def load_document_by_yaml(
    yaml: Any,
    uri: str,
    loadingOptions: LoadingOptions | None = None,
    id_: str | None = None,
    load_all: bool = False,
) -> Any:
    """Load a CWL object from a YAML object."""
    version = cwl_version(yaml)
    if "$graph" in yaml and not load_all:
        yaml = _get_id_from_graph(yaml, id_)
        yaml["cwlVersion"] = version
    match version:
        case "v1.0":
            result = cwl_v1_0.load_document_by_yaml(
                yaml, uri, cast(Optional[cwl_v1_0.LoadingOptions], loadingOptions)
            )
        case "v1.1":
            result = cwl_v1_1.load_document_by_yaml(
                yaml, uri, cast(Optional[cwl_v1_1.LoadingOptions], loadingOptions)
            )
        case "v1.2":
            result = cwl_v1_2.load_document_by_yaml(
                yaml, uri, cast(Optional[cwl_v1_2.LoadingOptions], loadingOptions)
            )
        case None:
            raise ValidationException("could not get the cwlVersion")
        case _:
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
    val: Saveable | MutableSequence[Saveable] | None,
    top: bool = True,
    base_url: str = "",
    relative_uris: bool = True,
) -> Any:
    """Convert a CWL Python object into a JSON/YAML serializable object."""
    match val:
        case cwl_v1_0.Saveable() | cwl_v1_1.Saveable() | cwl_v1_2.Saveable():
            return val.save(top=top, base_url=base_url, relative_uris=relative_uris)
        case MutableSequence():
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
        case MutableMapping():
            newdict = {}
            for key in val:
                newdict[key] = save(
                    val[key], top=False, base_url=base_url, relative_uris=relative_uris
                )
            return newdict
    return val


def is_process(v: Any) -> bool:
    """Test to see if the object is a CWL v1.x Python Process object."""
    return isinstance(v, cwl_v1_0.Process | cwl_v1_1.Process | cwl_v1_2.Process)


def version_split(version: str) -> MutableSequence[int]:
    """Split a cwlVersion value into its numerical components."""
    return [int(v) for v in version[1:].split(".")]

# Generating the Workflow Input JSON Schema Template

<!-- TOC -->
* [Generating the Workflow Input JSON Schema Template](#generating-the-workflow-input-json-schema-template)
  * [Part 1 - Clone the CWL-TS-Auto directory](#part-1---clone-the-cwl-ts-auto-directory)
  * [Part 2 - Install the typescript-json-schema package](#part-2---install-the-typescript-json-schema-package)
  * [Part 3 - Generate the Workflow Input JSON Schema Template](#part-3---generate-the-workflow-input-json-schema-template)
  * [Part 4 - Refine the template with the following python script](#part-4---refine-the-template-with-the-following-python-script)
  * [Part 5 - Run schema generation against all tests in the cwl v1.2 directory](#part-5---run-schema-generation-against-all-tests-in-the-cwl-v12-directory)
<!-- TOC -->

## Part 1 - Clone the CWL-TS-Auto directory

```
git clone https://github.com/common-workflow-lab/cwl-ts-auto

cd cwl-ts-auto
```

## Part 2 - Install the typescript-json-schema package

```
npm install typescript-json-schema@^0.62.0
```

## Part 3 - Generate the Workflow Input JSON Schema Template

```bash
npx typescript-json-schema \
  --required \
  --noExtraProps \
  tsconfig.json \
  WorkflowInputParameter > workflow_input_json_schema_template.primary.json
```

## Part 4 - Refine the template with the following python script

<details>

<summary>Click to expand!</summary>

```python
#!/usr/bin/env python3

import json
from copy import deepcopy
from itertools import chain
from pathlib import Path
from typing import Dict, List, Any
import sys

CLEANED_FILE_DEFINITION = {
    "File": {
        "additionalProperties": False,
        "description": "Represents a file (or group of files when `secondaryFiles` is provided) that\nwill be accessible by tools using standard POSIX file system call API such as\nopen(2) and read(2).\n\nFiles are represented as objects with `class` of `File`.  File objects have\na number of properties that provide metadata about the file.\n\nThe `location` property of a File is a URI that uniquely identifies the\nfile.  Implementations must support the `file://` URI scheme and may support\nother schemes such as `http://` and `https://`.  The value of `location` may also be a\nrelative reference, in which case it must be resolved relative to the URI\nof the document it appears in.  Alternately to `location`, implementations\nmust also accept the `path` property on File, which must be a filesystem\npath available on the same host as the CWL runner (for inputs) or the\nruntime environment of a command line tool execution (for command line tool\noutputs).\n\nIf no `location` or `path` is specified, a file object must specify\n`contents` with the UTF-8 text content of the file.  This is a \"file\nliteral\".  File literals do not correspond to external resources, but are\ncreated on disk with `contents` with when needed for executing a tool.\nWhere appropriate, expressions can return file literals to define new files\non a runtime.  The maximum size of `contents` is 64 kilobytes.\n\nThe `basename` property defines the filename on disk where the file is\nstaged.  This may differ from the resource name.  If not provided,\n`basename` must be computed from the last path part of `location` and made\navailable to expressions.\n\nThe `secondaryFiles` property is a list of File or Directory objects that\nmust be staged in the same directory as the primary file.  It is an error\nfor file names to be duplicated in `secondaryFiles`.\n\nThe `size` property is the size in bytes of the File.  It must be computed\nfrom the resource and made available to expressions.  The `checksum` field\ncontains a cryptographic hash of the file content for use it verifying file\ncontents.  Implementations may, at user option, enable or disable\ncomputation of the `checksum` field for performance or other reasons.\nHowever, the ability to compute output checksums is required to pass the\nCWL conformance test suite.\n\nWhen executing a CommandLineTool, the files and secondary files may be\nstaged to an arbitrary directory, but must use the value of `basename` for\nthe filename.  The `path` property must be file path in the context of the\ntool execution runtime (local to the compute node, or within the executing\ncontainer).  All computed properties should be available to expressions.\nFile literals also must be staged and `path` must be set.\n\nWhen collecting CommandLineTool outputs, `glob` matching returns file paths\n(with the `path` property) and the derived properties. This can all be\nmodified by `outputEval`.  Alternately, if the file `cwl.output.json` is\npresent in the output, `outputBinding` is ignored.\n\nFile objects in the output must provide either a `location` URI or a `path`\nproperty in the context of the tool execution runtime (local to the compute\nnode, or within the executing container).\n\nWhen evaluating an ExpressionTool, file objects must be referenced via\n`location` (the expression tool does not have access to files on disk so\n`path` is meaningless) or as file literals.  It is legal to return a file\nobject with an existing `location` but a different `basename`.  The\n`loadContents` field of ExpressionTool inputs behaves the same as on\nCommandLineTool inputs, however it is not meaningful on the outputs.\n\nAn ExpressionTool may forward file references from input to output by using\nthe same value for `location`.",
        "properties": {
            "basename": {
                "description": "The base name of the file, that is, the name of the file without any\nleading directory path.  The base name must not contain a slash `/`.\n\nIf not provided, the implementation must set this field based on the\n`location` field by taking the final path component after parsing\n`location` as an IRI.  If `basename` is provided, it is not required to\nmatch the value from `location`.\n\nWhen this file is made available to a CommandLineTool, it must be named\nwith `basename`, i.e. the final component of the `path` field must match\n`basename`.",
                "type": "string"
            },
            "checksum": {
                "description": "Optional hash code for validating file integrity.  Currently, must be in the form\n\"sha1$ + hexadecimal string\" using the SHA-1 algorithm.",
                "type": "string"
            },
            "class": {
                "const": "File",
                "description": "Must be `File` to indicate this object describes a file.",
                "type": "string"
            },
            "contents": {
                "description": "File contents literal.\n\nIf neither `location` nor `path` is provided, `contents` must be\nnon-null.  The implementation must assign a unique identifier for the\n`location` field.  When the file is staged as input to CommandLineTool,\nthe value of `contents` must be written to a file.\n\nIf `contents` is set as a result of a Javascript expression,\nan `entry` in `InitialWorkDirRequirement`, or read in from\n`cwl.output.json`, there is no specified upper limit on the\nsize of `contents`.  Implementations may have practical limits\non the size of `contents` based on memory and storage\navailable to the workflow runner or other factors.\n\nIf the `loadContents` field of an `InputParameter` or\n`OutputParameter` is true, and the input or output File object\n`location` is valid, the file must be a UTF-8 text file 64 KiB\nor smaller, and the implementation must read the entire\ncontents of the file and place it in the `contents` field.  If\nthe size of the file is greater than 64 KiB, the\nimplementation must raise a fatal error.",
                "type": "string"
            },
            "dirname": {
                "description": "The name of the directory containing file, that is, the path leading up\nto the final slash in the path such that `dirname + '/' + basename ==\npath`.\n\nThe implementation must set this field based on the value of `path`\nprior to evaluating parameter references or expressions in a\nCommandLineTool document.  This field must not be used in any other\ncontext.",
                "type": "string"
            },
            "format": {
                "description": "The format of the file: this must be an IRI of a concept node that\nrepresents the file format, preferably defined within an ontology.\nIf no ontology is available, file formats may be tested by exact match.\n\nReasoning about format compatibility must be done by checking that an\ninput file format is the same, `owl:equivalentClass` or\n`rdfs:subClassOf` the format required by the input parameter.\n`owl:equivalentClass` is transitive with `rdfs:subClassOf`, e.g. if\n`<B> owl:equivalentClass <C>` and `<B> owl:subclassOf <A>` then infer\n`<C> owl:subclassOf <A>`.\n\nFile format ontologies may be provided in the \"$schemas\" metadata at the\nroot of the document.  If no ontologies are specified in `$schemas`, the\nruntime may perform exact file format matches.",
                "type": "string"
            },
            "location": {
                "description": "An IRI that identifies the file resource.  This may be a relative\nreference, in which case it must be resolved using the base IRI of the\ndocument.  The location may refer to a local or remote resource; the\nimplementation must use the IRI to retrieve file content.  If an\nimplementation is unable to retrieve the file content stored at a\nremote resource (due to unsupported protocol, access denied, or other\nissue) it must signal an error.\n\nIf the `location` field is not provided, the `contents` field must be\nprovided.  The implementation must assign a unique identifier for\nthe `location` field.\n\nIf the `path` field is provided but the `location` field is not, an\nimplementation may assign the value of the `path` field to `location`,\nthen follow the rules above.",
                "type": "string"
            },
            "nameext": {
                "description": "The basename extension such that `nameroot + nameext == basename`, and\n`nameext` is empty or begins with a period and contains at most one\nperiod.  Leading periods on the basename are ignored; a basename of\n`.cshrc` will have an empty `nameext`.\n\nThe implementation must set this field automatically based on the value\nof `basename` prior to evaluating parameter references or expressions.",
                "type": "string"
            },
            "nameroot": {
                "description": "The basename root such that `nameroot + nameext == basename`, and\n`nameext` is empty or begins with a period and contains at most one\nperiod.  For the purposes of path splitting leading periods on the\nbasename are ignored; a basename of `.cshrc` will have a nameroot of\n`.cshrc`.\n\nThe implementation must set this field automatically based on the value\nof `basename` prior to evaluating parameter references or expressions.",
                "type": "string"
            },
            "path": {
                "description": "The local host path where the File is available when a CommandLineTool is\nexecuted.  This field must be set by the implementation.  The final\npath component must match the value of `basename`.  This field\nmust not be used in any other context.  The command line tool being\nexecuted must be able to access the file at `path` using the POSIX\n`open(2)` syscall.\n\nAs a special case, if the `path` field is provided but the `location`\nfield is not, an implementation may assign the value of the `path`\nfield to `location`, and remove the `path` field.\n\nIf the `path` contains [POSIX shell metacharacters](http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_02)\n(`|`,`&`, `;`, `<`, `>`, `(`,`)`, `$`,`` ` ``, `\\`, `\"`, `'`,\n`<space>`, `<tab>`, and `<newline>`) or characters\n[not allowed](http://www.iana.org/assignments/idna-tables-6.3.0/idna-tables-6.3.0.xhtml)\nfor [Internationalized Domain Names for Applications](https://tools.ietf.org/html/rfc6452)\nthen implementations may terminate the process with a\n`permanentFailure`.",
                "type": "string"
            },
            "secondaryFiles": {
                "description": "A list of additional files or directories that are associated with the\nprimary file and must be transferred alongside the primary file.\nExamples include indexes of the primary file, or external references\nwhich must be included when loading primary document.  A file object\nlisted in `secondaryFiles` may itself include `secondaryFiles` for\nwhich the same rules apply.",
                "items": {
                    "anyOf": [
                        {
                            "$ref": "#/definitions/File"
                        },
                        {
                            "$ref": "#/definitions/Directory"
                        }
                    ]
                },
                "type": "array"
            },
            "size": {
                "description": "Optional file size (in bytes)",
                "type": "number"
            }
        },
        "required": [
            "class"
        ],
        "type": "object"
    }
}

CLEANED_DIRECTORY_DEFINITION = {
    "Directory": {
        "additionalProperties": False,
        "description": "Represents a directory to present to a command line tool.\n\nDirectories are represented as objects with `class` of `Directory`.  Directory objects have\na number of properties that provide metadata about the directory.\n\nThe `location` property of a Directory is a URI that uniquely identifies\nthe directory.  Implementations must support the file:// URI scheme and may\nsupport other schemes such as http://.  Alternately to `location`,\nimplementations must also accept the `path` property on Directory, which\nmust be a filesystem path available on the same host as the CWL runner (for\ninputs) or the runtime environment of a command line tool execution (for\ncommand line tool outputs).\n\nA Directory object may have a `listing` field.  This is a list of File and\nDirectory objects that are contained in the Directory.  For each entry in\n`listing`, the `basename` property defines the name of the File or\nSubdirectory when staged to disk.  If `listing` is not provided, the\nimplementation must have some way of fetching the Directory listing at\nruntime based on the `location` field.\n\nIf a Directory does not have `location`, it is a Directory literal.  A\nDirectory literal must provide `listing`.  Directory literals must be\ncreated on disk at runtime as needed.\n\nThe resources in a Directory literal do not need to have any implied\nrelationship in their `location`.  For example, a Directory listing may\ncontain two files located on different hosts.  It is the responsibility of\nthe runtime to ensure that those files are staged to disk appropriately.\nSecondary files associated with files in `listing` must also be staged to\nthe same Directory.\n\nWhen executing a CommandLineTool, Directories must be recursively staged\nfirst and have local values of `path` assigned.\n\nDirectory objects in CommandLineTool output must provide either a\n`location` URI or a `path` property in the context of the tool execution\nruntime (local to the compute node, or within the executing container).\n\nAn ExpressionTool may forward file references from input to output by using\nthe same value for `location`.\n\nName conflicts (the same `basename` appearing multiple times in `listing`\nor in any entry in `secondaryFiles` in the listing) is a fatal error.",
        "properties": {
            "basename": {
                "description": "The base name of the directory, that is, the name of the file without any\nleading directory path.  The base name must not contain a slash `/`.\n\nIf not provided, the implementation must set this field based on the\n`location` field by taking the final path component after parsing\n`location` as an IRI.  If `basename` is provided, it is not required to\nmatch the value from `location`.\n\nWhen this file is made available to a CommandLineTool, it must be named\nwith `basename`, i.e. the final component of the `path` field must match\n`basename`.",
                "type": "string"
            },
            "class": {
                "const": "Directory",
                "description": "Must be `Directory` to indicate this object describes a Directory.",
                "type": "string"
            },
            "listing": {
                "description": "List of files or subdirectories contained in this directory.  The name\nof each file or subdirectory is determined by the `basename` field of\neach `File` or `Directory` object.  It is an error if a `File` shares a\n`basename` with any other entry in `listing`.  If two or more\n`Directory` object share the same `basename`, this must be treated as\nequivalent to a single subdirectory with the listings recursively\nmerged.",
                "items": {
                    "anyOf": [
                        {
                            "$ref": "#/definitions/File"
                        },
                        {
                            "$ref": "#/definitions/Directory"
                        }
                    ]
                },
                "type": "array"
            },
            "location": {
                "description": "An IRI that identifies the directory resource.  This may be a relative\nreference, in which case it must be resolved using the base IRI of the\ndocument.  The location may refer to a local or remote resource.  If\nthe `listing` field is not set, the implementation must use the\nlocation IRI to retrieve directory listing.  If an implementation is\nunable to retrieve the directory listing stored at a remote resource (due to\nunsupported protocol, access denied, or other issue) it must signal an\nerror.\n\nIf the `location` field is not provided, the `listing` field must be\nprovided.  The implementation must assign a unique identifier for\nthe `location` field.\n\nIf the `path` field is provided but the `location` field is not, an\nimplementation may assign the value of the `path` field to `location`,\nthen follow the rules above.",
                "type": "string"
            },
            "path": {
                "description": "The local path where the Directory is made available prior to executing a\nCommandLineTool.  This must be set by the implementation.  This field\nmust not be used in any other context.  The command line tool being\nexecuted must be able to access the directory at `path` using the POSIX\n`opendir(2)` syscall.\n\nIf the `path` contains [POSIX shell metacharacters](http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_02)\n(`|`,`&`, `;`, `<`, `>`, `(`,`)`, `$`,`` ` ``, `\\`, `\"`, `'`,\n`<space>`, `<tab>`, and `<newline>`) or characters\n[not allowed](http://www.iana.org/assignments/idna-tables-6.3.0/idna-tables-6.3.0.xhtml)\nfor [Internationalized Domain Names for Applications](https://tools.ietf.org/html/rfc6452)\nthen implementations may terminate the process with a\n`permanentFailure`.",
                "type": "string"
            }
        },
        "required": [
            "class"
        ],
        "type": "object"
    }
}

CLEANED_ANY_DEFINITION = {
    "Any": {
        "description": "A placeholder for any type of CWL object.",
        "anyOf": [
            {
                "type": "boolean"
            },
            {
                "type": "integer"
            },
            {
                "type": "number"
            },
            {
                "type": "string"
            },
            {
                "type": "array"
            },
            {
                "type": "object"
            },
            {
                "$ref": "#/definitions/File"
            },
            {
                "$ref": "#/definitions/Directory"
            }
        ],
        "properties": dict(
            map(
                lambda iter_: (iter_, True),
                list(
                    set(
                            list(CLEANED_DIRECTORY_DEFINITION["Directory"]["properties"].keys()) +  
                            list(CLEANED_FILE_DEFINITION["File"]["properties"].keys())
                    )
                )
            )
        )
    }
}

DEFINTIIONS_TO_REMOVE = ["DefaultFetcher", "Dictionary<any>", "Dictionary<string>", "Fetcher", "T"]



def remove_loading_options_and_extension_fields_from_schema(schema_dict: Any) -> Dict:
    """
    Remove loadingOptions from schema recursively
    :param schema_dict:
    :return:
    """

    new_schema_dict = {}

    if isinstance(schema_dict, Dict):
        for key, value in deepcopy(schema_dict).items():
            if isinstance(value, Dict):
                if "loadingOptions" in value:
                    del value["loadingOptions"]
                if "LoadingOptions" in value:
                    del value["LoadingOptions"]
                if "extensionFields" in value:
                    del value["extensionFields"]
                new_schema_dict[key] = remove_loading_options_and_extension_fields_from_schema(value)
            elif isinstance(value, List):
                if "loadingOptions" in value:
                    _ = value.pop(value.index("loadingOptions"))
                if "LoadingOptions" in value:
                    _ = value.pop(value.index("LoadingOptions"))
                if "extensionFields" in value:
                    _ = value.pop(value.index("extensionFields"))
                new_schema_dict[key] = remove_loading_options_and_extension_fields_from_schema(value)
            else:
                new_schema_dict[key] = value
    elif isinstance(schema_dict, List):
        new_schema_dict = list(
            map(lambda value_iter: remove_loading_options_and_extension_fields_from_schema(value_iter), schema_dict))
    else:
        # Item is a list of number
        new_schema_dict = schema_dict

    return new_schema_dict


def read_schema_in_from_file(file_path: Path) -> Dict:
    """
    Read in the auto-generated schema from the file
    :param file_path:
    :return:
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File {file_path} does not exist")

    with open(file_path, "r") as file_h:
        return json.load(file_h)


def assert_definitions_key(schema_dict: Dict):
    """
    Ensure that the definitions key is part of the schema dictionary and is itself is a dictionary
    :param schema_dict:
    :return:
    """
    if "definitions" not in schema_dict.keys() and not isinstance(schema_dict["definitions"], Dict):
        raise ValueError("Schema does not contain a 'definitions' key or 'definitions' is not a dictionary")


def add_import_and_include_to_schema(schema_dict) -> Dict:
    """
    Under the definitions section, add in the $import and $include definitions
    Copied from https://github.com/common-workflow-language/cwl-v1.2/blob/76bdf9b55e2378432e0e6380ccedebb4a94ce483/json-schema/cwl.yaml#L57-L72

    {
      "CWLImportManual": {
        "description": \"\"\"
           Represents an '$import' directive that should point toward another compatible CWL file to import
           where specified.
           The contents of the imported file should be relevant contextually where it is being imported
          \"\"\",
        "$comment": \"\"\"
          The schema validation of the CWL will not itself perform the '$import' to resolve and validate its contents.
          Therefore, the complete schema will not be validated entirely, and could still be partially malformed.
          To ensure proper and exhaustive validation of a CWL definition with this schema, all '$import' directives
          should be resolved and extended beforehand.
        \"\"\",
        "type": "object",
        "properties": {
          "$import": {
            "type": "string"
          }
        },
        "required": [
          "$import"
        ],
        "additionalProperties": false
      }
    }

    Ditto for $include directive

    {
      "CWLIncludeManual": {
        "description": "
           Represents an '$include' directive that should point toward another compatible CWL file to import
           where specified.
           The contents of the imported file should be relevant contextually where it is being imported
          ",
        "$comment": "
          The schema validation of the CWL will not itself perform the '$include' to resolve and validate its contents.
          Therefore, the complete schema will not be validated entirely, and could still be partially malformed.
          To ensure proper and exhaustive validation of a CWL definition with this schema, all '$include' directives
          should be resolved and extended beforehand.
        ",
        "type": "object",
        "properties": {
          "$include": {
            "type": "string"
          }
        },
        "required": [
          "$include"
        ],
        "additionalProperties": false
      }
    }


    :param schema_dict:
    :return:
    """

    # Always do a deepcopy on the input
    schema_dict = deepcopy(schema_dict)

    # Confirm definitions key
    assert_definitions_key(schema_dict)

    # Add in the $import and $include to the definitions
    schema_dict["definitions"].update(
        {
            "CWLImportManual": {
                "description": ""
                               "Represents an '$import' directive that should point toward another compatible "
                               "CWL file to import where specified. The contents of the imported file should be "
                               "relevant contextually where it is being imported",
                "$comment": ""
                            "The schema validation of the CWL will not itself perform the '$import' to resolve and "
                            "validate its contents. Therefore, the complete schema will not be validated entirely, "
                            "and could still be partially malformed. "
                            "To ensure proper and exhaustive validation of a CWL definition with this schema, "
                            "all '$import' directives should be resolved and extended beforehand",
                "type": "object",
                "properties": {
                    "$import": {
                        "type": "string"
                    }
                },
                "required": [
                    "$import"
                ],
                "additionalProperties": False
            },
            "CWLIncludeManual": {
                "description": ""
                               "Represents an '$include' directive that should point toward another compatible "
                               "CWL file to import where specified. The contents of the imported file should be "
                               "relevant contextually where it is being imported",
                "$comment": ""
                            "The schema validation of the CWL will not itself perform the '$include' to resolve and "
                            "validate its contents. Therefore, the complete schema will not be validated entirely, "
                            "and could still be partially malformed. "
                            "To ensure proper and exhaustive validation of a CWL definition with this schema, "
                            "all '$include' directives should be resolved and extended beforehand",
                "type": "object",
                "properties": {
                    "$include": {
                        "type": "string"
                    }
                },
                "required": [
                    "$include"
                ],
                "additionalProperties": False
            }
        }
    )

    return schema_dict


def fix_inline_javascript_requirement(schema_dict: Dict) -> Dict:
    """
    Fix the InlineJavascriptRequirement.expressionLib array to allow for $include

    FROM

    {
      "InlineJavascriptRequirement": {
        "additionalProperties": false,
        "description": "Auto-generated class implementation for https://w3id.org/cwl/cwl#InlineJavascriptRequirement\n\nIndicates that the workflow platform must support inline Javascript expressions.\nIf this requirement is not present, the workflow platform must not perform expression\ninterpolation.",
        "properties": {
          "class": {
            "const": "InlineJavascriptRequirement",
            "description": "Always 'InlineJavascriptRequirement'",
            "type": "string"
          },
          "expressionLib": {
            "description": "Additional code fragments that will also be inserted\nbefore executing the expression code.  Allows for function definitions that may\nbe called from CWL expressions.",
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "extensionFields": {
            "$ref": "#/definitions/Dictionary<any>"
          },
          "loadingOptions": {
            "$ref": "#/definitions/LoadingOptions"
          }
        },
        "required": [
          "class"
        ],
        "type": "object"
      }
    }

    TO

    {
      "InlineJavascriptRequirement": {
        "additionalProperties": false,
        "description": "Auto-generated class implementation for https://w3id.org/cwl/cwl#InlineJavascriptRequirement\n\nIndicates that the workflow platform must support inline Javascript expressions.\nIf this requirement is not present, the workflow platform must not perform expression\ninterpolation.",
        "properties": {
          "class": {
            "const": "InlineJavascriptRequirement",
            "description": "Always 'InlineJavascriptRequirement'",
            "type": "string"
          },
          "expressionLib": {
            "description": "Additional code fragments that will also be inserted\nbefore executing the expression code.  Allows for function definitions that may\nbe called from CWL expressions.",
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                    "$ref": "#/definitions/CWLIncludeManual"
                }
              ]
            },
            "type": "array"
          },
          "extensionFields": {
            "$ref": "#/definitions/Dictionary<any>"
          }
        },
        "required": [
          "class"
        ],
        "type": "object"
      }
    }

    """

    # Always do a deepcopy on the input
    schema_dict = deepcopy(schema_dict)

    # Confirm definitions key
    assert_definitions_key(schema_dict)

    # Assert InlineJavascriptRequirement exists in definitions
    if "InlineJavascriptRequirement" not in schema_dict["definitions"]:
        raise ValueError("Schema does not contain an 'InlineJavascriptRequirement' key in 'definitions'")

    # Confirm that the InlineJavascriptRequirement has a properties key and the properties key is a dictionary
    if (
            "properties" not in schema_dict["definitions"]["InlineJavascriptRequirement"] or
            not isinstance(schema_dict["definitions"]["InlineJavascriptRequirement"]["properties"], Dict)
    ):
        raise ValueError(
            "Schema does not contain a 'properties' key in 'InlineJavascriptRequirement.definitions' "
            "or 'properties' is not a dictionary"
        )

    # Confirm that properties has an expressionLib key
    if "expressionLib" not in schema_dict["definitions"]["InlineJavascriptRequirement"]["properties"]:
        raise ValueError("Schema does not contain an 'expressionLib' key in 'InlineJavascriptRequirement.properties'")

    # Confirm that expressionLib is of type array and has an items key
    if (
            "type" not in schema_dict["definitions"]["InlineJavascriptRequirement"]["properties"]["expressionLib"]
            or
            not schema_dict["definitions"]["InlineJavascriptRequirement"]["properties"]["expressionLib"][
                    "type"] == "array"
            or
            "items" not in schema_dict["definitions"]["InlineJavascriptRequirement"]["properties"]["expressionLib"]
    ):
        raise ValueError(
            "Schema does not contain an 'expressionLib' key in 'InlineJavascriptRequirement.properties' "
            "of type array with an 'items' key"
        )

    # Allow for $include in the expressionLib array by updating the the expressionLib items to be a anyOf array
    schema_dict["definitions"]["InlineJavascriptRequirement"]["properties"]["expressionLib"]["items"] = {
        "anyOf": [
            {
                "type": "string"
            },
            {
                "$ref": "#/definitions/CWLIncludeManual"
            }
        ]
    }

    return schema_dict


def fix_schema_def_requirement(schema_dict: Dict) -> Dict:
    """
    Allow SchemaDefRequirement.types array to be $import type

    FROM

    {
      "SchemaDefRequirement": {
        "additionalProperties": false,
        "description": ""
                       "Auto-generated class implementation for https://w3id.org/cwl/cwl#SchemaDefRequirement"
                       "This field consists of an array of type definitions which must be used when"
                       "interpreting the `inputs` and `outputs` fields.  When a `type` field"
                       "contains a IRI, the implementation must check if the type is defined in"
                       "`schemaDefs` and use that definition.  If the type is not found in"
                       "`schemaDefs`, it is an error.  The entries in `schemaDefs` must be"
                       "processed in the order listed such that later schema definitions may refer"
                       "to earlier schema definitions."
                       "- **Type definitions are allowed for `enum` and `record` types only.**"
                       "- Type definitions may be shared by defining them in a file and then"
                       "  `$include`-ing them in the `types` field.\n- A file can contain a list of type definitions",
        "properties": {
          "class": {
            "const": "SchemaDefRequirement",
            "description": "Always 'SchemaDefRequirement'",
            "type": "string"
          },
          "extensionFields": {
            "$ref": "#/definitions/Dictionary<any>"
          },
          "loadingOptions": {
            "$ref": "#/definitions/LoadingOptions"
          },
          "types": {
            "description": "The list of type definitions.",
            "items": {
              "anyOf": [
                {
                  "$ref": "#/definitions/CommandInputArraySchema"
                },
                {
                  "$ref": "#/definitions/CommandInputRecordSchema"
                },
                {
                  "$ref": "#/definitions/CommandInputEnumSchema"
                }
              ]
            },
            "type": "array"
          }
        },
        "required": [
          "class",
          "types"
        ],
        "type": "object"
      }
    }

    TO

    {
      "SchemaDefRequirement": {
        "additionalProperties": false,
        "description": ""
                       "Auto-generated class implementation for https://w3id.org/cwl/cwl#SchemaDefRequirement"
                       "This field consists of an array of type definitions which must be used when"
                       "interpreting the `inputs` and `outputs` fields.  When a `type` field"
                       "contains a IRI, the implementation must check if the type is defined in"
                       "`schemaDefs` and use that definition.  If the type is not found in"
                       "`schemaDefs`, it is an error.  The entries in `schemaDefs` must be"
                       "processed in the order listed such that later schema definitions may refer"
                       "to earlier schema definitions."
                       "- **Type definitions are allowed for `enum` and `record` types only.**"
                       "- Type definitions may be shared by defining them in a file and then"
                       "  `$include`-ing them in the `types` field.\n- A file can contain a list of type definitions",
        "properties": {
          "class": {
            "const": "SchemaDefRequirement",
            "description": "Always 'SchemaDefRequirement'",
            "type": "string"
          },
          "extensionFields": {
            "$ref": "#/definitions/Dictionary<any>"
          },
          "loadingOptions": {
            "$ref": "#/definitions/LoadingOptions"
          },
          "types": {
            "description": "The list of type definitions.",
            "items": {
              "anyOf": [
                {
                  "$ref": "#/definitions/CommandInputArraySchema"
                },
                {
                  "$ref": "#/definitions/CommandInputRecordSchema"
                },
                {
                  "$ref": "#/definitions/CommandInputEnumSchema"
                },
                {
                  "$ref": "#/definitions/CWLImportManual"
                }
              ]
            },
            "type": "array"
          }
        },
        "required": [
          "class",
          "types"
        ],
        "type": "object"
      }
    }

    :param schema_dict:
    :return:
    """

    # Always do a deepcopy on the input
    schema_dict = deepcopy(schema_dict)

    # Confirm definitions key
    assert_definitions_key(schema_dict)

    # Assert SchemaDefRequirement exists in definitions
    if "SchemaDefRequirement" not in schema_dict["definitions"]:
        raise ValueError("Schema does not contain an 'SchemaDefRequirement' key in 'definitions'")

    # Confirm that the SchemaDefRequirement has a properties key and the properties key is a dictionary
    if (
            "properties" not in schema_dict["definitions"]["SchemaDefRequirement"] or
            not isinstance(schema_dict["definitions"]["SchemaDefRequirement"]["properties"], Dict)
    ):
        raise ValueError(
            "Schema does not contain a 'properties' key in 'SchemaDefRequirement.definitions' "
            "or 'properties' is not a dictionary"
        )

    # Confirm that properties has a types key
    if "types" not in schema_dict["definitions"]["SchemaDefRequirement"]["properties"]:
        raise ValueError("Schema does not contain an 'types' key in 'SchemaDefRequirement.properties'")

    # Confirm that types is of type array and has an items key
    if (
            "type" not in schema_dict["definitions"]["SchemaDefRequirement"]["properties"]["types"]
            or
            not schema_dict["definitions"]["SchemaDefRequirement"]["properties"]["types"]["type"] == "array"
            or
            "items" not in schema_dict["definitions"]["SchemaDefRequirement"]["properties"]["types"]
    ):
        raise ValueError(
            "Schema does not contain an 'types' key in 'SchemaDefRequirement.properties' "
            "of type array with an 'items' key"
        )

    # Confirm that the types items has an anyOf key and the anyOf key is an array
    if (
            "anyOf" not in schema_dict["definitions"]["SchemaDefRequirement"]["properties"]["types"]["items"]
            or
            not isinstance(schema_dict["definitions"]["SchemaDefRequirement"]["properties"]["types"]["items"]["anyOf"],
                           List)
    ):
        raise ValueError(
            "Schema does not contain an 'anyOf' key in 'SchemaDefRequirement.properties.types.items' "
            "or 'anyOf' is not a list"
        )

    # Allow for $import in the types array by updating the types items to be a anyOf array
    schema_dict["definitions"]["SchemaDefRequirement"]["properties"]["types"]["items"]["anyOf"].append(
        {
            "$ref": "#/definitions/CWLImportManual"
        }
    )

    return schema_dict


def add_cwl_metadata_to_schema(schema_dict: Dict) -> Dict:
    """
    Add in the CWL metadata to the schema
    Derived from https://github.com/common-workflow-language/cwl-v1.2/blob/76bdf9b55e2378432e0e6380ccedebb4a94ce483/json-schema/cwl.yaml#L2231-L2241
    :param schema_dict:
    :return:
    """

    # Always do a deepcopy on the input
    schema_dict = deepcopy(schema_dict)

    # Assert definitions
    assert_definitions_key(schema_dict)

    # Add in the CWL metadata to the definitions
    schema_dict["definitions"].update(
        {
            "CWLDocumentMetadata": {
                "description": "Metadata for a CWL document",
                "type": "object",
                "properties": {
                    "$namespaces": {
                        "description": "The namespaces used in the document",
                        "type": "object",
                        "patternProperties": {
                            "^[_a-zA-Z][a-zA-Z0-9_-]*$": {
                                "type": "string"
                            }
                        }
                    },
                    "$schemas": {
                        "description": "The schemas used in the document",
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "patternProperties": {
                    "^s:.*$": {
                        "type": "object"
                    },
                    # Or the full version
                    "^https://schema.org/.*$": {
                        "type": "object"
                    }
                },
                "additionalProperties": False,
                "required": []
            }
        }
    )
    return schema_dict


def write_schema_out_to_file(schema_dict: Dict, file_path: Path):
    """
    Write out the schema to the file
    :param schema_dict:
    :param file_path:
    :return:
    """
    with open(file_path, "w") as file_h:
        json.dump(schema_dict, file_h, indent=4)


def rename_all_keys_with_trailing_underscore(schema_dict: Any) -> Dict:
    """
    Keys such as class_, type_ etc. are renames from TypeScript. We need to rename them in the JSON schema back
    to their original names to generate a valid CWL JSON schema
    :param schema_dict:
    :return:
    """

    new_schema_dict = {}

    if isinstance(schema_dict, Dict):
        for key, value in deepcopy(schema_dict).items():
            key = key.rstrip("_")
            if isinstance(value, Dict):
                new_schema_dict[key] = rename_all_keys_with_trailing_underscore(value)
            elif isinstance(value, List):
                new_schema_dict[key] = rename_all_keys_with_trailing_underscore(value)
            else:
                new_schema_dict[key] = value
    elif isinstance(schema_dict, List):
        new_schema_dict = list(
            map(lambda value_iter: rename_all_keys_with_trailing_underscore(value_iter), schema_dict))
    else:
        # Item is a value
        new_schema_dict = schema_dict.rstrip("_")

    return new_schema_dict


def add_cwl_file(schema_dict: Dict) -> Dict:
    """
    Large updates to the actual file body

    Can come in two forms, File and Graph.

    In File form, can be of type Workflow, ExpressionTool or CommandLineTool,
    In Graph form, we have the $graph property which then has elements of type CWLFile

    Both can have the metadata objects such as $namespaces and $schemas

    We initialise both objects.

    Then state that the file can be a file or a graph

    :param schema_dict:
    :return:
    """
    # Always deep copy the input
    schema_dict = deepcopy(schema_dict)

    # Assert $ref key
    if "$ref" not in schema_dict:
        raise ValueError("Schema does not contain a '$ref' key")

    # Assert $ref value is "#/definitions/Workflow"
    if schema_dict["$ref"] != "#/definitions/Workflow":
        raise ValueError("Schema does not contain a '$ref' value of '#/definitions/Workflow'")

    # Update the schema to use 'if-else' for CommandlineTool and Expression
    schema_dict.update(
        {
            "$ref": "#/definitions/CWLFile",
        }
    )

    schema_dict["definitions"].update(
        {
            # First create the yaml option
            # Which is either a workflow, commandline tool or expression tool
            "CWLFile": {
                "type": "object",
                "additionalProperties": False,
                "allOf": [
                    {
                        "oneOf": [
                            {
                                "$ref": "#/definitions/Workflow"
                            },
                            {
                                "$ref": "#/definitions/CommandLineTool"
                            },
                            {
                                "$ref": "#/definitions/ExpressionTool"
                            }
                        ]
                    },
                    {
                        "oneOf": [
                            {
                                "$ref": "#/definitions/CWLDocumentMetadata"
                            }
                        ]
                    }
                ]
            }
        }
    )

    return schema_dict


def add_cwl_graph(schema_dict: Dict) -> Dict:
    """
    Large updates to the actual file body

    Can come in two forms, File and Graph.

    In File form, can be of type Workflow, ExpressionTool or CommandLineTool,
    In Graph form, we have the $graph property which then has elements of type CWLFile

    Both can have the metadata objects such as $namespaces and $schemas

    We initialise both objects.

    Then state that the file can be a file or a graph

    :param schema_dict:
    :return:
    """
    # Always deep copy the input
    schema_dict = deepcopy(schema_dict)

    # Assert $ref key
    if "$ref" not in schema_dict:
        raise ValueError("Schema does not contain a '$ref' key")

    # Update the schema
    schema_dict.update(
        {
            "$ref": "#/definitions/CWLGraphWithMetadata",
        }
    )

    # Update definitions
    schema_dict["definitions"].update(
        {
            # Now create the graph option
            "CWLGraph": {
                "type": "object",
                "properties": {
                    "$graph": {
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/CWLFile"
                        }
                    },
                    # Copy from Workflow
                    "cwlVersion": schema_dict["definitions"]["Workflow"]["properties"]["cwlVersion"]
                },
                "required": [
                    "$graph"
                ]
            },
            "CWLGraphWithMetadata": {
                "type": "object",
                "additionalProperties": False,
                "allOf": [
                    {
                        "$ref": "#/definitions/CWLGraph"
                    },
                    {
                        "$ref": "#/definitions/CWLDocumentMetadata"
                    }
                ]
            }
        }
    )

    return schema_dict


def fix_descriptions(schema_dict: Dict) -> Dict:
    """
    Fix the descriptions for all definitions by removing the 'Auto-generated' class implementation ...
    Means that users will see helpful descriptions in the schema
    :param schema_dict:
    :return:
    """
    # Always deep copy the input
    schema_dict = deepcopy(schema_dict)

    # Assert definitions
    assert_definitions_key(schema_dict)

    # Iterate over all definitions and remove the 'Auto-generated' class implementation
    for schema_def_name, schema_def_dict in schema_dict.get("definitions", {}).items():
        if "description" not in schema_def_dict:
            continue
        schema_dict["definitions"][schema_def_name]["description"] = (
            schema_def_dict.get("description", "").split("\n\n", 1)[-1]
        )

    # Update top level description
    schema_dict["description"] = schema_dict.get("description", "").split("\n\n", 1)[-1]

    return schema_dict


def fix_additional_properties(schema_dict: Dict, top_definition: str, sub_definition_keys: List) -> Dict:
    """
    Fix the additionalProperties issues demonstrated in https://stoic-agnesi-d0ac4a.netlify.app/37
    :param schema_dict:
    :return:
    """
    # Always copy the input
    schema_dict = deepcopy(schema_dict)

    # Part 1, drop additionalProperties: false from Workflow, CommandLineTool and ExpressionTool definitions
    for definition_key in sub_definition_keys:
        _ = schema_dict["definitions"][definition_key].pop("additionalProperties", None)

    # Part 2
    # For CWLFileorGraph definition, add in the collective set of properties keys defined under
    # Workflow, CommandLineTool, ExpressionTool, $graph and CWLMetadata
    # And for each property key set the value to true -
    property_keys = []
    for definition_key in sub_definition_keys:
        if "properties" not in schema_dict["definitions"][definition_key]:
            continue
        property_keys.append(list(schema_dict["definitions"][definition_key]["properties"].keys()))
    property_keys = list(set(chain(*property_keys)))

    schema_dict["definitions"][top_definition]["properties"] = dict(
        map(
            lambda property_key_iter: (property_key_iter, True),
            property_keys
        )
    )

    # Part 2a, copy over patternProperties
    pattern_property_objects = {}
    for definition_key in sub_definition_keys:
        if "patternProperties" not in schema_dict["definitions"][definition_key]:
            continue
        pattern_property_objects.update(
            schema_dict["definitions"][definition_key]["patternProperties"]
        )

    schema_dict["definitions"][top_definition]["patternProperties"] = pattern_property_objects

    # Make additionalProperties false to this top CWLDocumentMetadata
    schema_dict["definitions"][top_definition]["additionalProperties"] = False

    return schema_dict


def fix_hints(schema_dict, definition_key):
    """
    Hints property should be the same as requirements for the given key
    :param schema_dict:
    :param definition_key:
    :return:
    """

    # Always do a deepcopy on the input
    schema_dict = deepcopy(schema_dict)

    # Assert definitions key
    assert_definitions_key(schema_dict)

    # Confirm definitions key exists
    if definition_key not in schema_dict["definitions"]:
        raise ValueError(f"Schema does not contain an '{definition_key}' key in 'definitions'")

    # Confirm that the definition_key has a properties key and the properties key is a dictionary
    if (
            "properties" not in schema_dict["definitions"][definition_key] or
            not isinstance(schema_dict["definitions"][definition_key]["properties"], Dict)
    ):
        raise ValueError(
            f"Schema does not contain a 'properties' key in '{definition_key}.definitions' "
            "or 'properties' is not a dictionary"
        )

    # Confirm that properties has a requirements key
    if "requirements" not in schema_dict["definitions"][definition_key]["properties"]:
        raise ValueError(f"Schema does not contain an 'requirements' key in '{definition_key}.properties'")

    # Copy requirements to hints
    schema_dict["definitions"][definition_key]["properties"]["hints"] = \
        schema_dict["definitions"][definition_key]["properties"]["requirements"]

    return schema_dict


def add_file_and_directory_to_schema(schema_dict: Dict) -> Dict:
    """
    Add file and directory definitions to schema
    :param schema_dict:
    :return:
    """
    # Always do a deepcopy on the input
    schema_dict = deepcopy(schema_dict)

    # Assert definitions key
    assert_definitions_key(schema_dict)

    # Add in the File and Directory definitions to the schema
    schema_dict['definitions'].update(
        CLEANED_FILE_DEFINITION
    )
    schema_dict['definitions'].update(
        CLEANED_DIRECTORY_DEFINITION
    )
    schema_dict['definitions'].update(
        CLEANED_ANY_DEFINITION
    )

    return schema_dict


def drop_properties_and_required(schema_dict: Dict) -> Dict:
    """
    Drop the properties and required keys
    :param schema_dict:
    :return:
    """
    # Always do a deepcopy on the input
    schema_dict = deepcopy(schema_dict)

    # Doesn't matter if they're not present
    _ = schema_dict.pop("properties", None)
    _ = schema_dict.pop("required", None)

    # Also drop additionalProperties
    _ = schema_dict.pop("additionalProperties", None)

    return schema_dict


def main():
    # Step 1 - read in existing schema
    schema_dict = read_schema_in_from_file(Path(sys.argv[1]))

    # Remove loading options from schema
    schema_dict = remove_loading_options_and_extension_fields_from_schema(schema_dict)

    # Rename all keys with trailing underscore
    schema_dict = rename_all_keys_with_trailing_underscore(schema_dict)

    # Drop the following definitions
    # DefaultFetcher
    # Dictionary<any>
    # Dictionary<string>
    # Fetcher
    # T
    for definition in DEFINTIIONS_TO_REMOVE:
        _ = schema_dict["definitions"].pop(definition)

    # Add the following definitions
    # File, Directory,
    schema_dict = add_file_and_directory_to_schema(schema_dict)

    # Drop existing properties and required list (this will be populated by the script)
    schema_dict = drop_properties_and_required(schema_dict)

    # Write out the new schema
    write_schema_out_to_file(schema_dict, Path(sys.argv[2]))


if __name__ == "__main__":
    main()

```
</details>

Run the python script above

```
python3 refine_workflow_input_json_schema_template.py \
  workflow_input_json_schema_template.primary.json \
  workflow_input_json_schema_template.json
```


## Part 5 - Run schema generation against all tests in the cwl v1.2 directory

> Note there is a set of six urls and inputs that we test the schema generation against in the tests directory

<details>

<summary>Click to expand!</summary>

```python
#!/usr/bin/env python3
import json
from json import JSONDecodeError
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from jsonschema import validate
from jsonschema.exceptions import SchemaError, ValidationError
from ruamel.yaml import YAML

from cwl_utils.loghandler import _logger as _cwlutilslogger

FAILED_TESTS = [
    "filesarray_secondaryfiles2",  # Conditional logic too complex for json schema
    "wf_step_access_undeclared_param",  # Inputs are valid, workflow expected to fail at tool level
    "input_records_file_entry_with_format_and_bad_regular_input_file_format",  # Don't validate formats
    "secondary_files_missing",  # Inputs are valid, workflow expected to fail at tool level
    "input_records_file_entry_with_format_and_bad_entry_file_format",  # Don't validate formats
    "input_records_file_entry_with_format_and_bad_entry_array_file_format",  # Don't validate formats
    "timelimit_basic",  # Inputs are valid, workflow expected to fail at tool level
    "timelimit_invalid",  # Inputs are valid, workflow expected to fail at tool level
    "timelimit_from_expression",  # Inputs are valid, workflow expected to fail at tool level
    "timelimit_basic_wf",  # Inputs are valid, workflow expected to fail at tool level
    "timelimit_from_expression_wf",  # Inputs are valid, workflow expected to fail at tool level
    "networkaccess_disabled",  # Inputs are valid, workflow expected to fail at tool level
    "glob_outside_outputs_fails",  # Inputs are valid, workflow expected to fail at tool level
    "illegal_symlink",  # Inputs are valid, workflow expected to fail at tool level
    "params_broken_null",  # Inputs are valid, workflow expected to fail at tool level
    "length_for_non_array",  # Inputs are valid, workflow expected to fail at tool level
    "capture_files",  # Inputs are valid, workflow expected to fail at tool level
    "capture_dirs",  # Inputs are valid, workflow expected to fail at tool level
]

# Clone cwl1.2 repo into temp dir
with TemporaryDirectory() as temp_dir:

    run(['git', 'clone', 'https://github.com/common-workflow-language/cwl-v1.2'], cwd=temp_dir)

    tests_dir = Path(temp_dir) / 'cwl-v1.2' / 'tests'

    # Open conformance test yaml file
    yaml = YAML()

    with open(Path(temp_dir) / 'cwl-v1.2' / "conformance_tests.yaml") as tests_yaml_h:
        tests_list = yaml.load(tests_yaml_h)

    failed_runs = []

    for test_item in tests_list:
        id_ = test_item.get('id')

        # Check tool key exists
        if test_item.get('tool', None) is None:
            _cwlutilslogger.info(f"Skipping conformance test {id_}, no tool key")
            continue

        tool = Path(test_item.get('tool').split("#", 1)[0])
        should_fail = test_item.get('should_fail', False)

        if "#" in test_item.get("tool") and not "#main" in test_item.get("tool"):
            _cwlutilslogger.info(f"Skipping conformance test {id_}, we cannot load non main graphs")
            continue

        if id_ in FAILED_TESTS:
            _cwlutilslogger.info(f"Skipping conformance test {id_}")
            continue

        _cwlutilslogger.info(f"Running conformance test {id_}")

        _cwlutilslogger.info(f"Generating schema for {tool.name}")
        schema_gen_proc = run(
            [
                "python3", str(Path(__file__).parent / "cwl_utils" / "inputs_schema_gen.py"),  Path(temp_dir) / 'cwl-v1.2' / tool
            ],
            capture_output=True
        )

        if not schema_gen_proc.returncode == 0:
            _cwlutilslogger.error(schema_gen_proc.stderr.decode())
            raise ChildProcessError

        schema_gen_stdout = schema_gen_proc.stdout.decode()

        if test_item.get('job', None) is None:
            continue

        job = Path(test_item.get('job'))

        try:
            input_schema_dict = json.loads(schema_gen_stdout)
        except JSONDecodeError:
            raise JSONDecodeError

        # Collect job
        with open(Path(temp_dir) / 'cwl-v1.2' / job) as job_h:
            job_dict = yaml.load(job_h)

        _cwlutilslogger.info(f"Testing {job.name} against schema generated for input {tool.name}")
        try:
            validate(job_dict, input_schema_dict)
        except (ValidationError, SchemaError) as err:
            if not should_fail:
                _cwlutilslogger.error(f"Failed schema validation with {err}")
                failed_runs.append(id_)
        else:
            if should_fail:
                _cwlutilslogger.error(f"Expected to fail but passed")
                failed_runs.append(id_)

    if len(failed_runs) > 0:
        _cwlutilslogger.error("The following tests failed")
        for failed_run in failed_runs:
            _cwlutilslogger.error(failed_run)

```

</details>
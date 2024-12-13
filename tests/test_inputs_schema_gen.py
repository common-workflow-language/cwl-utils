# SPDX-License-Identifier: Apache-2.0
"""Tests for cwl-inputs-schema-gen."""
from json import dumps
from typing import Dict

import pytest

from cwl_utils.inputs_schema_gen import cwl_inputs_to_jsonschema
from cwl_utils.parser import load_document_by_uri, save

TEST_PARAMS = [
    # When the definition itself is a nasty case.
    {
        "url": "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/echo-tool-packed.cwl",
        "expected": '''{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "in": {
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
        }
      ]
    }
  },
  "required": [
    "in"
  ],
  "additionalProperties": false
}'''},
    {
        "url": "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/revsort-packed.cwl",
        "expected": '''{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "input": {
      "type": "object",
      "properties": {
        "class": {
          "type": "string",
          "const": "File"
        },
        "path": {
          "type": "string"
        },
        "location": {
          "type": "string"
        }
      },
      "required": [
        "class"
      ],
      "oneOf": [
        {
          "required": [
            "path"
          ]
        },
        {
          "required": [
            "location"
          ]
        }
      ],
      "additionalProperties": false
    },
    "reverse_sort": {
      "type": "boolean",
      "default": true
    }
  },
  "required": [
    "input"
  ],
  "additionalProperties": false
}'''},
    # When the type is nasty.
    {
        "url": "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/anon_enum_inside_array.cwl",
        "expected": '''{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "first": {
      "type": "object",
      "properties": {
        "species": {
          "type": "string",
          "enum": [
            "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/anon_enum_inside_array.cwl#first/species/homo_sapiens",
            "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/anon_enum_inside_array.cwl#first/species/mus_musculus"
          ],
          "nullable": true
        }
      },
      "required": [
        "species"
      ],
      "additionalProperties": false
    },
    "second": {
      "type": "string",
      "enum": [
        "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/anon_enum_inside_array.cwl#second/homo_sapiens",
        "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/anon_enum_inside_array.cwl#second/mus_musculus"
      ],
      "nullable": true
    }
  },
  "required": [
    "first"
  ],
  "additionalProperties": false
}'''},
    # The number of parameters is a little large, and the definition itself is a straightforward case.
    {
        "url": "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/bwa-mem-tool.cwl",
        "expected": '''{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "reference": {
      "type": "object",
      "properties": {
        "class": {
          "type": "string",
          "const": "File"
        },
        "path": {
          "type": "string"
        },
        "location": {
          "type": "string"
        }
      },
      "required": [
        "class"
      ],
      "oneOf": [
        {
          "required": [
            "path"
          ]
        },
        {
          "required": [
            "location"
          ]
        }
      ],
      "additionalProperties": false
    },
    "reads": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "class": {
            "type": "string",
            "const": "File"
          },
          "path": {
            "type": "string"
          },
          "location": {
            "type": "string"
          }
        },
        "required": [
          "class"
        ],
        "oneOf": [
          {
            "required": [
              "path"
            ]
          },
          {
            "required": [
              "location"
            ]
          }
        ],
        "additionalProperties": false
      },
      "additionalItems": false
    },
    "minimum_seed_length": {
      "type": "integer"
    },
    "min_std_max_min": {
      "type": "array",
      "items": {
        "type": "integer"
      },
      "additionalItems": false
    },
    "args.py": {
      "type": "object",
      "properties": {
        "class": {
          "type": "string",
          "const": "File"
        },
        "path": {
          "type": "string"
        },
        "location": {
          "type": "string"
        }
      },
      "required": [
        "class"
      ],
      "oneOf": [
        {
          "required": [
            "path"
          ]
        },
        {
          "required": [
            "location"
          ]
        }
      ],
      "additionalProperties": false,
      "default": {
        "class": "File",
        "location": "args.py"
      }
    }
  },
  "required": [
    "reference",
    "reads",
    "minimum_seed_length",
    "min_std_max_min"
  ],
  "additionalProperties": false
}'''},
    # The case where CommandInputParameter is shortened (e.g., param: string)
    {
        "url": "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/env-tool1.cwl",
        "expected": '''{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "in": {
      "type": "string"
    }
  },
  "required": [
    "in"
  ],
  "additionalProperties": false
}'''},
    # No input parameters
    {
        "url": "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/envvar3.cwl",
        "expected": '''{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}'''},
    # Any
    {
        "url": "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/params.cwl",
        "expected": '''{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "bar": {
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
        }
      ],
      "default": {
        "baz": "zab1",
        "b az": 2,
        "b'az": true,
        "b\\\"az": null,
        "buz": [
          "a",
          "b",
          "c"
        ]
      }
    }
  },
  "required": [],
  "additionalProperties": false
}'''},
    # Dir
    {
        "url": "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/dir.cwl",
        "expected": '''{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "indir": {
      "type": "object",
      "properties": {
        "class": {
          "type": "string",
          "const": "Directory"
        },
        "path": {
          "type": "string"
        },
        "location": {
          "type": "string"
        }
      },
      "required": [
        "class"
      ],
      "oneOf": [
        {
          "required": [
            "path"
          ]
        },
        {
          "required": [
            "location"
          ]
        }
      ],
      "additionalProperties": false
    }
  },
  "required": [
    "indir"
  ],
  "additionalProperties": false
}'''},
    # SecondaryFiles
    {
        "url": "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/secondaryfiles/rename-inputs.cwl",
        "expected": '''{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "inputWithSecondary": {
      "type": "object",
      "properties": {
        "class": {
          "type": "string",
          "const": "File"
        },
        "path": {
          "type": "string"
        },
        "location": {
          "type": "string"
        }
      },
      "required": [
        "class"
      ],
      "oneOf": [
        {
          "required": [
            "path"
          ]
        },
        {
          "required": [
            "location"
          ]
        }
      ],
      "additionalProperties": false
    },
    "accessory": {
      "type": "object",
      "properties": {
        "class": {
          "type": "string",
          "const": "File"
        },
        "path": {
          "type": "string"
        },
        "location": {
          "type": "string"
        }
      },
      "required": [
        "class"
      ],
      "oneOf": [
        {
          "required": [
            "path"
          ]
        },
        {
          "required": [
            "location"
          ]
        }
      ],
      "additionalProperties": false
    }
  },
  "required": [
    "inputWithSecondary",
    "accessory"
  ],
  "additionalProperties": false
}'''},
    {
        "url": "https://raw.githubusercontent.com/common-workflow-language/cwl-v1.2/main/tests/stage-array.cwl",
        "expected": '''{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "input_file": {
      "type": "object",
      "properties": {
        "class": {
          "type": "string",
          "const": "File"
        },
        "path": {
          "type": "string"
        },
        "location": {
          "type": "string"
        }
      },
      "required": [
        "class"
      ],
      "oneOf": [
        {
          "required": [
            "path"
          ]
        },
        {
          "required": [
            "location"
          ]
        }
      ],
      "additionalProperties": false
    },
    "optional_file": {
      "type": "object",
      "properties": {
        "class": {
          "type": "string",
          "const": "File"
        },
        "path": {
          "type": "string"
        },
        "location": {
          "type": "string"
        }
      },
      "required": [
        "class"
      ],
      "oneOf": [
        {
          "required": [
            "path"
          ]
        },
        {
          "required": [
            "location"
          ]
        }
      ],
      "additionalProperties": false,
      "nullable": true
    },
    "input_list": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "class": {
            "type": "string",
            "const": "File"
          },
          "path": {
            "type": "string"
          },
          "location": {
            "type": "string"
          }
        },
        "required": [
          "class"
        ],
        "oneOf": [
          {
            "required": [
              "path"
            ]
          },
          {
            "required": [
              "location"
            ]
          }
        ],
        "additionalProperties": false
      },
      "additionalItems": false
    }
  },
  "required": [
    "input_file",
    "input_list"
  ],
  "additionalProperties": false
}'''}
]


@pytest.mark.parametrize("test_param", TEST_PARAMS)
def test_cwl_inputs_to_jsonschema(test_param: Dict[str, str]) -> None:
    url = test_param["url"]
    expected = test_param["expected"]

    cwl_obj = load_document_by_uri(url)
    saved_obj = save(cwl_obj)
    json_serialized_inputs_obj = saved_obj["inputs"]
    jsonschema = cwl_inputs_to_jsonschema(json_serialized_inputs_obj)

    assert dumps(jsonschema, indent=2) == expected

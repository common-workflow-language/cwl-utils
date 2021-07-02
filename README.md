# cwl-utils

A collection of scripts to demonstrate the use of the new Python classes for
loading and parsing [CWL v1.0 ](https://github.com/common-workflow-language/cwl-utils/blob/main/cwl_utils/parser/v1_0.py),
 [CWL v1.1](https://github.com/common-workflow-language/cwl-utils/blob/main/cwl_utils/parser/v1_1.py),
and [CWL v1.2](https://github.com/common-workflow-language/cwl-utils/blob/main/cwl_utils/parser/v1_2.py)
documents.

## Install

Requires Python 3.6+

``` bash
virtualenv -p python3.6 venv3.6  # Python 3.7, 3.8, or 3.9 would also work
source venv3.6/bin/activate
pip install cwl-utils
```
or install the latest development version of `cwl-utils`

``` bash
git clone https://github.com/common-workflow-language/cwl-utils.git
cd cwl-utils
virtualenv -p python3.6 venv3.6  # Python 3.7, 3.8, or 3.9 would also work
source venv3.6/bin/activate
pip install .
```

## Usage

### Pull the all referenced software container images

`docker_extract.py` is useful to cache or pre-pull all software container images
referenced in a CWL CommandLineTool or CWL Workflow (including all referenced
CommandLineTools and sub-Workflows and so on).

The default behaviour is to use the Docker engine to download and save the software
container images in Docker format.

```bash
python docker_extract.py DIRECTORY path_to_my_workflow.cwl
```

Or you can use the Singularity software container engine to download and save the
software container images and convert them to the Singularity format at the same
time.

```bash
python docker_extract.py --singularity DIRECTORY path_to_my_workflow.cwl
```

### Using the CWL Parsers

```python
# Imports
from pathlib import Path
from ruamel import yaml
import sys

# File Input - This is the only thing you will need to adjust or take in as an input to your function:
cwl_file = Path("/path/to/wf.cwl")

# Read in the cwl file from a yaml
with open(cwl_file, "r") as cwl_h:
 yaml_obj = yaml.main.round_trip_load(cwl_h, preserve_quotes=True)
    
# Check CWLVersion
if 'cwlVersion' not in list(yaml_obj.keys()):
    print("Error - could not get the cwlVersion")
    sys.exit(1)

# Import parser based on CWL Version    
if yaml_obj['cwlVersion'] == 'v1.0':
    from cwl_utils import parser_v1_0 as parser
elif yaml_obj['cwlVersion'] == 'v1.1':
    from cwl_utils import parser_v1_1 as parser
elif yaml_obj['cwlVersion'] == 'v1.2':
    from cwl_utils import parser_v1_2 as parser
else:
    print("Version error. Did not recognise {} as a CWL version".format(yaml_obj["CWLVersion"]))
    sys.exit(1)

# Import CWL Object
cwl_obj = parser.load_document_by_yaml(yaml_obj, cwl_file.as_uri())

# View CWL Object
print("List of object attributes:\n{}".format("\n".join(map(str, dir(cwl_obj)))))
```

## Development

### Regenerate parsers

To regenerate install the `schema_salad` package and run:

`cwl_utils/parser_v1_0.py` was created via
`schema-salad-tool --codegen python https://github.com/common-workflow-language/common-workflow-language/raw/main/v1.0/CommonWorkflowLanguage.yml`

`cwl_utils/parser_v1_1.py` was created via
`schema-salad-tool --codegen python https://github.com/common-workflow-language/cwl-v1.1/raw/main/CommonWorkflowLanguage.yml`

`cwl_utils/parser_v1_2.py` was created via
`schema-salad-tool --codegen python https://github.com/common-workflow-language/cwl-v1.2/raw/main/CommonWorkflowLanguage.yml`


### Release

To release CWLUtils, bump the version in `cwl_utils/__meta__.py`, and tag that
commit with the new version. The [gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish)
should release that tag.

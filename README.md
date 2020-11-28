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
commit with the new version. TravisCI should release that tag.

# cwl-utils

A collection of scripts to demonstrate the use of the [new Python classes for loading and parsing CWL v1.0 documents](https://github.com/common-workflow-language/cwl-utils/blob/master/cwl_utils/parser_v1_0.py).


`cwl_utils/parser_v1_0.py` was created via
`schema-salad-tool --codegen python https://github.com/common-workflow-language/common-workflow-language/raw/master/v1.0/CommonWorkflowLanguage.yml`

## Install

Requires Python 3.6.x or Python 3.7

``` bash
git clone https://github.com/common-workflow-language/cwl-utils.git
virtualenv -p python3.6 venv3.6
source venv3.6/bin/activate
pip install cwl-utils
```

## Usage

### Pull the image with Docker

This is the default behaviour:

```bash
python docker_extract.py DIRECTORY path_to_my_workflow.cwl
```

### Pull the image with Singularity

```bash
python docker_extract.py --singularity DIRECTORY path_to_my_workflow.cwl
```

## Regenerate

To regenerate install `schema_salad` package and run:

```
schema-salad-tool --codegen python \
    https://raw.githubusercontent.com/common-workflow-language/common-workflow-language/master/v1.0/CommonWorkflowLanguage.yml
```

## Release

To release CWLUtils, bump the version in `cwl_utils/__meta__.py`, and tag that commit with the new version. TravisCI should release that tag.

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

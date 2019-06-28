A collection of scripts to demonstrate the use of the [new Python classes for loading and parsing CWL v1.0 documents](https://github.com/common-workflow-language/cwl-utils/blob/master/cwl_utils/parser_v1_0.py).

Requires Python 3.6.x or Python 3.7

``` bash
git clone https://github.com/common-workflow-language/cwl-utils.git
virtualenv -p python3.6 venv3.6
source venv3.6/bin/activate
pip install cwl-utils
python docker-extract.py path_to_my_workflow.cwl
```

to regenerate install `schema_salad` package and run:

```
schema-salad-tool --codegen python \
    https://raw.githubusercontent.com/common-workflow-language/common-workflow-language/master/v1.0/CommonWorkflowLanguage.yml
```

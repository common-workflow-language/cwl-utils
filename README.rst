|Linux Build Status| |Code coverage| |Documentation Status|

.. |Linux Build Status| image:: https://github.com/common-workflow-language/cwl-utils/actions/workflows/ci-tests.yml/badge.svg?branch=main
   :target: https://github.com/common-workflow-language/cwl-utils/actions/workflows/ci-tests.yml
.. |Code coverage| image:: https://codecov.io/gh/common-workflow-language/cwl-utils/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/common-workflow-language/cwl-utils
.. |Documentation Status| image:: https://readthedocs.org/projects/cwl-utils/badge/?version=latest
   :target: https://cwl-utils.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

cwl-utils
---------

A collection of scripts to demonstrate the use of the new Python classes
for loading and parsing `CWL
v1.0 <https://github.com/common-workflow-language/cwl-utils/blob/main/cwl_utils/parser/v1_0.py>`__,
`CWL
v1.1 <https://github.com/common-workflow-language/cwl-utils/blob/main/cwl_utils/parser/v1_1.py>`__,
and `CWL
v1.2 <https://github.com/common-workflow-language/cwl-utils/blob/main/cwl_utils/parser/v1_2.py>`__
documents.

Requires Python 3.6+

Installation
------------

::

   pip3 install cwl-utils

To install from source::

   git clone https://github.com/common-workflow-language/cwl-utils.git
   cd cwl-utils
   pip3 install .

Usage
-----

Pull the all referenced software container images
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``docker_extract.py`` is useful to cache or pre-pull all software
container images referenced in a CWL CommandLineTool or CWL Workflow
(including all referenced CommandLineTools and sub-Workflows and so on).

The default behaviour is to use the Docker engine to download and save
the software container images in Docker format.

.. code:: bash

   docker_extract.py DIRECTORY path_to_my_workflow.cwl

Or you can use the Singularity software container engine to download and
save the software container images and convert them to the Singularity
format at the same time.

.. code:: bash

   docker_extract.py --singularity DIRECTORY path_to_my_workflow.cwl

Using the CWL Parsers
~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   from pathlib import Path
   from ruamel import yaml
   import sys

   from cwl_utils.parser import load_document_by_uri, save

   # File Input - This is the only thing you will need to adjust or take in as an input to your function:
   cwl_file = Path("testdata/md5sum.cwl")  # or a plain string works as well

   # Import CWL Object
   cwl_obj = load_document_by_uri(cwl_file)

   # View CWL Object
   print("List of object attributes:\n{}".format("\n".join(map(str, dir(cwl_obj)))))

   # Export CWL Object into a built-in typed object
   saved_obj = save(cwl_obj)
   print(f"Export of the loaded CWL object: {saved_obj}.")

Development
-----------

Regenerate parsers
~~~~~~~~~~~~~~~~~~

To regenerate install the ``schema_salad`` package and run:

``cwl_utils/parser/cwl_v1_0.py`` was created via
``schema-salad-tool --codegen python https://github.com/common-workflow-language/common-workflow-language/raw/main/v1.0/CommonWorkflowLanguage.yml``

``cwl_utils/parser/cwl_v1_1.py`` was created via
``schema-salad-tool --codegen python https://github.com/common-workflow-language/cwl-v1.1/raw/main/CommonWorkflowLanguage.yml``

``cwl_utils/parser/cwl_v1_2.py`` was created via
``schema-salad-tool --codegen python https://github.com/common-workflow-language/cwl-v1.2/raw/1.2.1_proposed/CommonWorkflowLanguage.yml``

Release
~~~~~~~

To release CWLUtils, bump the version in ``cwl_utils/__meta__.py``, and
tag that commit with the new version. The
`gh-action-pypi-publish <https://github.com/pypa/gh-action-pypi-publish>`__
should release that tag.


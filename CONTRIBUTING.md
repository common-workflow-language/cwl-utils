Style guide:
- PEP-8 / format with ``black`` via ``make format``
- Python 3.6+ compatible code
- PEP-484 type hints

In order to contribute to the development of ``cwl-utils``, you need to install cwl-utils from source (preferably in a virtual environment):
Here's a rough guide (improvements are welcome!) 
- Install virtualenv via pip: ``pip install virtualenv``
- Clone the cwl-utils Git repository: ``git clone https://github.com/common-workflow-language/cwl-utils.git``
- Switch to cwl-utils directory: ``cd cwl-utils``
- Create a virtual environment: ``virtualenv env``
- To begin using the virtual environment, it needs to be activated: ``source env/bin/activate``
- To check if you have the virtual environment set up: ``which python`` and it should point to python executable in your virtual env
- Install cwl-utils in the virtual environment: ``pip install -e .``
- Check the version which might be different from the version installed in general on any system: ``pip show cwl-utils``
- After you've made the changes, you can the complete test suite via tox: ``tox``
	- If you want to run specific tests, say ``unit tests`` in Python 3.8, then: ``tox -e py38-unit``.
	- Look at ``tox.ini`` for all available tests and runtimes
- If tests are passing, you can create a PR on ``cwl-utils`` GitHub repository.
- After you're done working on the ``cwl-utils``, you can deactivate the virtual environment: ``deactivate``

#!/usr/bin/env python3
import sys
import os

from setuptools import find_packages, setup

exec(open("cwl_utils/__meta__.py").read())

needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)
pytest_runner = ["pytest < 7", "pytest-runner"] if needs_pytest else []
setup(
    name="cwl-utils",
    version=__version__,
    license="Apache 2.0",
    author="Common workflow language working group",
    author_email="common-workflow-language@googlegroups.com",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "ruamel.yaml<=0.16.5,>=0.12.4",
        "six",
        "requests",
        "schema-salad >= 7, < 8",
        "typing_extensions",
    ],
    setup_requires=[] + pytest_runner,
    tests_require=["pytest<7", "cwltool", "requests"],
    test_suite="tests",
    scripts=[
        "cwl_utils/docker_extract.py",
        "cwl_utils/etools_to_clt.py",
        "cwl_utils/cite_extract.py",
        "cwl_utils/graph_split.py",
    ],
    long_description=open("./README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/common-workflow-language/cwl-utils",
)

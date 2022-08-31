#!/usr/bin/env python3

import os
import pathlib
import sys
from typing import List

from setuptools import setup

SETUP_DIR = os.path.dirname(__file__)
README = os.path.join(SETUP_DIR, "README.rst")

exec(open("cwl_utils/__meta__.py").read())

needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)
pytest_runner: List[str] = ["pytest < 8", "pytest-runner"] if needs_pytest else []
setup(
    name="cwl-utils",
    version=__version__,  # type: ignore
    long_description=open(README).read(),
    long_description_content_type="text/x-rst",
    author="Common workflow language working group",
    author_email="common-workflow-language@googlegroups.com",
    url="https://github.com/common-workflow-language/cwl-utils",
    license="Apache 2.0",
    python_requires=">=3.6",
    setup_requires=pytest_runner,
    packages=["cwl_utils", "cwl_utils.parser", "cwl_utils.tests", "cwl_utils.testdata"],
    package_dir={
        "cwl_utils.parser": "cwl_utils/parser",
        "cwl_utils.tests": "tests",
        "cwl_utils.testdata": "testdata",
    },
    include_package_data=True,
    install_requires=open(
        os.path.join(pathlib.Path(__file__).parent, "requirements.txt")
    )
    .read()
    .splitlines(),
    tests_require=["pytest<8"],
    test_suite="tests",
    extras_require={"pretty": ["cwlformat"]},
    entry_points={
        "console_scripts": [
            "cwl-cite-extract=cwl_utils.cite_extract:main",
            "cwl-docker-extract=cwl_utils.docker_extract:main",
            "cwl-expression-refactor=cwl_utils.expression_refactor:main",
            "cwl-graph-split=cwl_utils.graph_split:main",
            "cwl-normalizer=cwl_utils.normalizer:main",
        ]
    },
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Typing :: Typed",
    ],
)

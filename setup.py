#!/usr/bin/env python3
from setuptools import setup, find_packages

exec(open("cwl_utils/__meta__.py").read())

setup(
    name='cwl-utils',
    version=__version__,
    author='Common workflow language working group',
    author_email='common-workflow-language@googlegroups.com',
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=[
        'ruamel.yaml',
        'six',
        'requests',
        'schema-salad >= 7, < 8',
        'typing_extensions',
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    test_suite='tests',
    scripts=['cwl_utils/docker_extract.py'],
    long_description=open("./README.md").read(),
    long_description_content_type="text/markdown",
    url='https://github.com/common-workflow-language/cwl-utils',
)

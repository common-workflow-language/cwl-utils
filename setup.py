from setuptools import setup, find_packages


setup(
    name='cwl-utils',
    version='0.2',
    author='Common workflow language working group',
    author_email='common-workflow-language@googlegroups.com',
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=[
        'ruamel.yaml',
        'six',
        'requests',
        'schema_salad',
        'typing_extensions',
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    test_suite='tests',
    scripts=['cwl_utils/docker_extract.py'],
)

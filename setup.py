from setuptools import setup, find_packages


setup_requires = [
    'ruamel.yaml',
    'six',
    'requests',
    'cachecontrol',
    'schema_salad',
]

setup(
    name='cwl-utils',
    version='0.1',
    author='Common workflow language working group',
    author_email='common-workflow-language@googlegroups.com',
    packages=find_packages(),
    python_requires='>=3.6',
    setup_requires=setup_requires,
)

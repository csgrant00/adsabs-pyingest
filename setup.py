from setuptools import setup

setup(
    name='pyingest',
    version='0.5.0',
    packages=['pyingest'],
    package_dir={'':['config','extractors','parsers','serializers','validators']}
)

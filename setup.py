import os
from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README.md file and 2) it's easier to type in the README file than to put a
# raw string in below ...


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="prettylint",
    version="0.0.0",
    author="Federico Ressi",
    author_email="federico.ressi@someplace.com",
    description=("A pretty pylint wrapper."),
    license="BSD",
    keywords="test pylint",
    # url="http://packages.python.org/an_example_pypi_project",
    packages=['prettylint'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
    entry_points={
        'console_scripts': [
            'prettylint = prettylint.cmd:main',
        ],
    },
)

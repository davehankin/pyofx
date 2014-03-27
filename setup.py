import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "pyOfx",
    version = "0.0.6",
    author = "Steven Rossiter",
    author_email = "steve@flexsis.co.uk",
    description = ("A wrapper around OrcFxAPI by Orcina "
                                   "to add extra functionality."),
    license = "MIT",
    keywords = "orcaflex api wrapper subsea engineering",
    url = "http://packages.python.org/pyofx",
    packages=['pyofx'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Win32 (MS Windows)",
        "Topic :: Utilities",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 2 :: Only",
        "Topic :: Scientific/Engineering :: Physics"
    ],
)
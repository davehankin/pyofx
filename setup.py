import os
from setuptools import setup
README = os.path.join(os.path.dirname(__file__), 'README.md')
try:
    import pypandoc
    LONG = pypandoc.convert(README, 'rst')
except ImportError as e:
    print e
    LONG = open(README).read()

setup(
    name="pyOfx",
    version="0.0.16",
    author="Steven Rossiter",
    author_email="steve@flexsis.co.uk",
    description=("A wrapper around OrcFxAPI by Orcina "
                 "to add extra functionality."),
    license = "MIT",
    keywords = "orcaflex api wrapper subsea engineering",
    url = "https://pythonhosted.org/pyOfx/",
    packages=['pyofx'],
    long_description=LONG,
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

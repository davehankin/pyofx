.. pyofx documentation master file, created by
   sphinx-quickstart on Thu Oct 09 12:08:08 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pyofx's documentation!
=================================

.. toctree::
   :maxdepth: 2

   api_docs

pyofx is an `OrcFxAPI <http://www.orcina.com/SoftwareProducts/OrcaFlex/Documentation/OrcFxAPIHelp/>`_ extension.

The module contains a number of helper functions useful to those using `OrcaFlex <http://www.orcina.com/SoftwareProducts/OrcaFlex/>`_.

It also wraps the `OrcFxAPI.Model` class to provide extra functionality and offers interfaces to directories of OrcaFlex files and Distributed OrcaFlex.

Pre-requisites
--------------

pyofx has been built and tested on Python 2.7 and with version 9.7 of the OrcaFlex DLL

pyofx is pure Python and does not rely on any external packages with the exception of OrcFxAPI, which you will need to have `installed <http://www.orcina.com/SoftwareProducts/OrcaFlex/Documentation/OrcFxAPIHelp/Content/html/PythonInterface,Installation.htm>`_.


Installation
------------

pyofx can be found at the `Python Package Index <https://pypi.python.org/pypi/pyOfx>`_ and so can be installed with pip/easy_install.  If you don't have pip or easy install you should consider installing `pip-win <https://sites.google.com/site/pydatalog/python/pip-win>`_ on Windows for a pain-free interface to python packages.

There are also Windows installers for the 64-bit version of python. 

You can check if it is installed properly like so:

    >>> import pyofx


Tutorial
--------

Once installed pyofx behaves exactly as OrcFxAPI does and provides all the same functions and classes. 

Model
^^^^^

The only class that is altered is the `OrcFxAPI.Model` class.

`pyofx.Model` has:

- a `path` attribute, the full path of the model on disk
- a `model_name` attribute, the filename without extension
- an `open` method, opens the model in the OrcaFlex GUI
- an `objects_of_type` method, a list of model objects filtered by type (e.g. 'Line') and optionally further conditions
- `lines`, `vessels` and `six_d_buoys` attributes which are shortcuts to the relevant `objects_of_type`

The class docstring contains some further details and examples:

.. autoclass:: pyofx.Model

Folders of Models
^^^^^^^^^^^^^^^^^

Often when using the OrcaFlex API you want to apply some function to a folder or folders containing OrcaFlex .dat/.sim/.yml files. `pyofx.Models` provides an interface to make this easier.

.. autoclass:: pyofx.Models

Distributed OrcaFlex
^^^^^^^^^^^^^^^^^^^^

There is also a way to add files to Distributed OrcaFlex from python with:

.. autoclass:: pyofx.Jobs


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


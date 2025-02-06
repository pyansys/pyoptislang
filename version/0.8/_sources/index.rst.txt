PyOptiSLang documentation |version|
===================================

.. toctree::
   :hidden:
   :maxdepth: 3

   getting_started/index
   user_guide/index
   api/index
   osl_server_api/index
   examples/index
   contributing/index


Introduction
-------------
Ansys optiSLang is a constantly evolving, leading-edge answer to the challenges posed
by CAE-based RDO (Robust Design Optimization). Its state-of-the-art algorithms efficiently
and automatically search for the most robust design configuration, eliminating the slow,
manual process that used to define RDO.

What is PyOptiSLang?
--------------------
PyOptiSLang is part of the larger `PyAnsys <https://docs.pyansys.com>`_
effort to facilitate the use of Ansys technologies directly from
Python.
PyOptiSLang implements a client-server architecture. Communication between PyOptiSLang (client)
and the running optiSLang process (server) is based on the plain TCP/IP technology.
However, you need to interact only with the Python interface.

You can use PyOptiSLang to programmatically create, interact with, and control
an optiSLang project. Additionally, you can use it to create custom scripts
that can speed up and automate simulations.

PyOptiSLang  lets you use optiSLang within a Python environment of your choice
in conjunction with other PyAnsys libraries and external Python libraries.

Features
--------
The ``ansys-optislang-core`` package provides these features:

- Ability to launch optiSLang locally or connect to the remote optiSLang server. For more information,
  see :ref:`ref_launch`.
- Basic commands such as those for opening, saving and running projects as well as queries to
  obtain information about projects. For more information, see :ref:`ref_functions`.
- Executing Python commands from the optiSLang Python API. For more information,
  see :ref:`ref_run_python`.
- Evaluate designs on root project level. For more information,
  see :ref:`ref_design_evaluation`.
- Create and connect nodes. For more information,
  see :ref:`ref_create_workflow`.


Documentation and issues
------------------------
In addition to installation and usage information, the PyOptiSLang documentation provides
API member descriptions, examples, and contribution information.

On the `PyOptiSLang Issues <https://github.com/ansys/pyoptislang/issues>`_ page, you can create
issues to submit questions, report bugs, and request new features. This is the best place to post
questions and code.

Project index
*************

* :ref:`genindex`

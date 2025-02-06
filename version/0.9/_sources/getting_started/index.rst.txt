Getting started
===============
To run PyOptiSLang, you must have access to a licensed copy of optiSLang. The first
supported version of optiSLang is 2023 R1. For more information on optiSLang, see the
`Ansys optiSLang <https://www.ansys.com/products/connect/ansys-optislang>`_ page
on the Ansys website.

************
Installation
************
The ``ansys-optislang-core`` package supports Python 3.8 through 3.12 on
Windows and Linux. Three modes of installation are available:

- User installation
- Developer installation
- Offline installation

For either a developer or offline installation, consider using a `virtual environment
<https://docs.python.org/3/library/venv.html>`_.

User installation
~~~~~~~~~~~~~~~~~
Install the latest release from `PyPi
<https://pypi.org/project/ansys-optislang-core/>`_ with this command:

.. code::

   pip install ansys-optislang-core


Alternatively, install the latest `PyOptiSLang GitHub
<https://github.com/ansys/pyoptislang/issues>`_ package with this command:

.. code::

   pip install git+https://github.com/ansys/pyoptislang.git


Developer installation
~~~~~~~~~~~~~~~~~~~~~~
If you plan on doing local *development* of PyOptiSLang with GitHub,
clone and install PyOptiSLang with this code:

.. code::

   git clone https://github.com/ansys/pyoptislang.git
   cd pyoptislang
   pip install -e .


A developer installation allows you to edit ``ansys-optislang-core``
files locally. Any changes that you make are reflected in your setup
after restarting the Python kernel.

Offline installation
~~~~~~~~~~~~~~~~~~~~
Using a wheelhouse can be helpful if you work for a company that restricts access to
external networks. From the `Releases <https://github.com/ansys/pyoptislang/releases>`_
page in the PyOptiSLang repository, you can find the wheelhouses for a particular release in its
assets and download the wheelhouse corresponding to your setup.

You can then install PyOptiSLang and all of its dependencies from one single entry point
that can be shared internally, which eases the security review of the PyOptiSLang package content.

For example, on Linux with Python 3.8, unzip the wheelhouse and install PyOptiSLang with code
like this:

.. code:: bash

    unzip PyOptiSLang-v0.1.0-wheelhouse-Linux-3.8.zip wheelhouse
    pip install ansys-optislang-core -f wheelhouse --no-index --upgrade --ignore-installed


If you're on Windows with Python 3.9, unzip the wheelhouse to a wheelhouse directory and
then install using the same ``pip`` command as in the preceding Linux code example.

Ansys software requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~
You must have a local licensed copy of optiSLang installed or be able to connect to an
already running remote instance. As mentioned earlier, the first supported optiSLang
version is 2023 R1.

Verify installation
~~~~~~~~~~~~~~~~~~~
To verify your optiSLang installation, run this code:

.. code:: python

   from ansys.optislang.core import Optislang

   osl = Optislang()
   print(osl)
   osl.dispose()


If you see a response, you can start using OptiSLang as a service.
For information on the PyOptiSLang interface, see :ref:`ref_user_guide`.

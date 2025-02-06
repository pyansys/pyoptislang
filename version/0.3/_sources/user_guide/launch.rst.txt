.. _ref_launch:

=============================
OptiSLang instance management
=============================
You use the :class:`Optislang <ansys.optislang.core.optislang.Optislang>`
class to launch optiSLang as a server and to control and query optiSLang projects.
You can either launch optiSLang locally or connect to a remote optiSLang instance.

.. note::
    When you are done using an optiSLang instance, you should always use the
    :func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>` method to
    shut down the instance gracefully. If you use the
    :class:`Optislang <ansys.optislang.core.optislang.Optislang>` class as a
    context manager, it executes the :func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>`
    method automatically, even when an exception is raised.

Launch optiSLang locally
------------------------
The :class:`Optislang <ansys.optislang.core.optislang.Optislang>` class must know 
the location of the optiSLang executable file to run. By default, the latest installed
version of optiSLang is launched. To initialize an optiSLang instance and start it
locally as a server, run this code:

.. code:: python

    from ansys.optislang.core import Optislang

    osl = Optislang()
    print(osl)
    osl.dispose()


Calling the :func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>` method 
closes the connection with the optiSLang server. If an optiSLang instance is started with the
``shutdown_on_finished`` parameter set to ``True``, which is the default, the server shuts down
automatically. For information on how to keep the server running after disposing the optiSLang
instance, see :ref:`optislang-termination`.

To get a list of all supported optiSLang executable files, run this code:

.. code:: python

    from ansys.optislang.core import utils

    print(utils.find_all_osl_exec())


To launch a specific optiSLang version shown in the list of supported executable files, or
to launch a supported version from a non-standard installation location, use the ``executable``
parameter to specify the path to the desired executable file:

.. code:: python

    from ansys.optislang.core import Optislang

    osl = Optislang(
        executable=r"C:\\Program Files\\Dynardo\\Ansys optiSLang\\2023 R1\\optislang.com"
    )
    print(osl)
    osl.dispose()


To open a specific project or create a project, use the ``project_path`` parameter. This
code creates a project in the current working directory:

.. code:: python

    from ansys.optislang.core import Optislang
    from pathlib import Path

    path = Path.cwd()
    project_name = "test.opf"

    osl = Optislang(project_path=path / project_name)
    print(osl)
    osl.dispose()


Connect to a remote optiSLang instance
--------------------------------------
For remote connection, it is assumed that optiSLang is already running as a server
on a remote (or local) host. To connect to this running instance, you must specify the
host and port. Parameters related to the execution of a new optiSLang server are ignored.

This code initializes optiSLang and connects to a remote optiSLang server:

.. code:: python

     from ansys.optislang.core import Optislang

     host = "127.0.0.1"  # specify host
     port = 5310  # specify port

     osl = Optislang(host=host, port=port)
     print(osl)
     osl.dispose()


Calling the :func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>` method 
closes the connection with the remote optiSLang server. However, if this server was
started with the ``shutdown_on_finished`` parameter set to ``False``, the server won't
shut down. You must use the :func:`shutdown() <ansys.optislang.core.optislang.Optislang.shutdown>`
method to shut down the server before disposing the 
:class:`Optislang <ansys.optislang.core.optislang.Optislang>` instance. For more information,
see :ref:`optislang-termination`.

.. _optislang-termination:

Optislang instance disposal and optional optiSLang server shutdown
------------------------------------------------------------------
As mentioned earlier, when an :class:`Optislang <ansys.optislang.core.optislang.Optislang>`
instance is no longer in use, you should always use the
:func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>` method to shut
down the instance gracefully.

Optionally, you can use the :func:`shutdown() <ansys.optislang.core.optislang.Optislang.shutdown>`
method to shut down the OptiSLang server. However, you must call this method before the
:func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>`
method. If you set the ``shutdown_on_finished`` parameter on the
:func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>` method to
``True``, you do not need to use the :func:`shutdown() <ansys.optislang.core.optislang.Optislang.shutdown>`
method.


Differences in the termination methods mentioned earlier follow:

* The :func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>` method only closes
  the connection with the optiSLang server.
* The :func:`shutdown() <ansys.optislang.core.optislang.Optislang.shutdown>` method sends a
  command to shut down the optiSLang server, which is necessary when termination of the
  server is requested and either of these situations exist:
  
  * The server is started locally by an optiSLang instance with the
    ``shutdown_on_finished`` parameter set to ``False``.
  * The optiSLang instance is connected to a remote optiSLang server. 


To specify whether to automatically shut down the optiSLang server, you can use the
``shutdown_on_finished`` parameter in the :class:`Optislang <ansys.optislang.core.optislang.Optislang>`
instance constructor. The default value for this parameter is ``True``. This means that
the optiSLang server is shut down automatically after the
:func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>` method is called.

To keep a locally started optiSLang server running even after disposing the
:class:`Optislang <ansys.optislang.core.optislang.Optislang>` instance, you must set the
``shutdown_on_finished`` parameter to ``False`` when creating the instance. In
this case, to shut down the optiSLang server, you must call the
:func:`shutdown() <ansys.optislang.core.optislang.Optislang.shutdown>` method before
disposing the :class:`Optislang <ansys.optislang.core.optislang.Optislang>` instance.

The following examples show possible termination cases of the optiSLang instance
initialized with the ``shutdown_on_finished`` parameter set to ``False``.

* To keep the optiSLang server running, use only the
  :func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>` method:

  .. code:: python

        from ansys.optislang.core import Optislang

        osl = Optislang(shutdown_on_finished=False)
        print(osl)
        osl.dispose()


* To shut down the optiSLang server, use both the
   :func:`shutdown() <ansys.optislang.core.optislang.Optislang.shutdown>` and
   :func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>` methods: 
   
   .. code:: python

        from ansys.optislang.core import Optislang

        osl = Optislang(shutdown_on_finished=False)
        print(osl)
        osl.shutdown()
        osl.dispose()


You can use the same approach when connected to a remote optiSLang server.

+-----------------+----------------------------+----------------+----------------------------------+
| Initialization  |  ``shutdown_on_finished``  |    Methods     |   optiSLang server is running    |
+=================+============================+================+==================================+
| Local           | ``True``                   | ``dispose()``  | No                               |
|                 +----------------------------+----------------+----------------------------------+
|                 | ``False``                  | ``dispose()``  | Yes                              |
|                 |                            +----------------+----------------------------------+
|                 |                            | ``shutdown()`` | No                               |
|                 |                            | ``dispose()``  |                                  |
+-----------------+----------------------------+----------------+----------------------------------+
| Remote          | ``True``                   | ``dispose()``  | No                               |
|                 +----------------------------+----------------+----------------------------------+
|                 | ``False``                  | ``dispose()``  | Yes                              |
|                 |                            +----------------+----------------------------------+
|                 |                            | ``shutdown()`` | No                               |
|                 |                            | ``dispose()``  |                                  |
+-----------------+----------------------------+----------------+----------------------------------+


Context manager
---------------
You should use the :class:`Optislang() <ansys.optislang.core.optislang.Optislang>` class as a context
manager. The main advantage of this approach is that the optiSLang instance and connection to
the optiSLang server automatically shut down gracefully, even if an error occurs when calling
the :func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>` method.

.. code:: python

    from ansys.optislang.core import Optislang

    with Optislang() as osl:
        print(osl)
        osl.start()


.. note::

    When an optiSLang instance is started with the ``shutdown_on_finished`` parameter set
    to ``False``, or if the instance is connected to an optiSLang server started with this
    setting, the default behavior is to close the connection and keep the optiSLang server
    running. To stop the optiSLang server, you must use the
    :func:`shutdown() <ansys.optislang.core.optislang.Optislang.shutdown>` method.

    .. code:: python

        from ansys.optislang.core import Optislang

        with Optislang(shutdown_on_finished=False) as osl:
            print(osl)
            osl.start()
            osl.shutdown()


.. _ref_functions:

===========
Basic usage
===========
An instance of the :py:class:`Optislang <ansys.optislang.core.optislang.Optislang>` includes 
a property :py:attr:`application <ansys.optislang.core.optislang.Optislang.application>`, 
which encapsulates an instance 
of the :py:class:`Application <ansys.optislang.core.application.Application>`
class, equipped with functionalities to retrieve information about the employed server 
and perform manipulations on the project.

.. code:: python

    from ansys.optislang.core import Optislang

    osl = Optislang()
    application = osl.application

Within the context of the :py:class:`Application <ansys.optislang.core.application.Application>` 
class instance, there is further
property :py:attr:`project <ansys.optislang.core.application.Application.project>`, 
which holds an instance of the :py:class:`Project <ansys.optislang.core.project.Project>` class
(if any project is loaded). This instance groups functionality to get project information
and execute operations on the active project.

.. code:: python

    project = osl.application.project


To start a project, you use the :py:meth:`start() <ansys.optislang.core.project.Project.start>`
method. This code starts the project for the :ref:`ref_simple_calculator` example:

.. code:: python

    from ansys.optislang.core import examples

    path_to_file = examples.get_files("simple_calculator")[0]
    osl.application.project.run_python_file(file_path=path_to_file)
    osl.application.project.start()


To save the project, use the
:py:meth:`save() <ansys.optislang.core.application.Application.save>`,
:py:meth:`save_as() <ansys.optislang.core.application.Application.save_as>`, or
:py:meth:`save_copy() <ansys.optislang.core.application.Application.save_copy>`
method. This code uses the :py:meth:`save_as() <ansys.optislang.core.application.Application.save_as>`
method:

.. code:: python

    from pathlib import Path

    project_path = Path().cwd() / "test_project.opf"
    osl.application.save_as(project_path)


If an optiSLang instance is created with the default parameters, the optiSLang project
is located in a temporary directory. Therefore, to preserve the project permanently,
you should use either the :py:meth:`save_as() <ansys.optislang.core.application.Application.save_as>`
or :py:meth:`save_copy() <ansys.optislang.core.application.Application.save_copy>` method.

To create a project or open an existing one, you use the
:py:meth:`new() <ansys.optislang.core.application.Application.new>` or
:py:meth:`open() <ansys.optislang.core.application.Application.open>` method. This code
creates a project: 

.. code:: python

    new_project = Path().cwd() / "new_project.opf"
    osl.application.new()
    osl.application.save_as(new_project)

To obtain some general information about a project, run this code:

.. code:: python

    print(osl)

Or, you can run specific requests like shown in this code:

.. code:: python

    print(f"Version: {osl.application.get_version_string()}")
    print(f"Working directory: {osl.application.project.get_working_dir()}")

When you no longer need to use the :py:class:`Optislang <ansys.optislang.core.optislang.Optislang>`
instance, close the connection with the optiSLang server by running this code:

.. code:: python

    osl.dispose()

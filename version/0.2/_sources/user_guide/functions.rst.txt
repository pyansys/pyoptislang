.. _ref_functions:

===========
Basic usage
===========
To start a project, you use the :func:`start <ansys.optislang.core.optislang.Optislang.start>`
method. This code starts the project for the :ref:`ref_simple_calculator` example:

.. code:: python

    from pathlib import Path
    from ansys.optislang.core import Optislang, examples

    osl = Optislang()
    path_to_file = examples.get_files("simple_calculator")[0]
    osl.run_python_file(file_path=path_to_file)
    osl.start()


To save the project, use the
:func:`save() <ansys.optislang.core.optislang.Optislang.save>`,
:func:`save_as() <ansys.optislang.core.optislang.Optislang.save_as>`, or
:func:`save_copy() <ansys.optislang.core.optislang.Optislang.save_copy>`
method. This code uses the :func:`save_as() <ansys.optislang.core.optislang.Optislang.save_as>`
method:

.. code:: python

    project_path = Path().cwd() / "test_project.opf"
    osl.save_as(project_path)


If an optiSLang instance is created with the default parameters, the optiSLang project
is located in a temporary directory. Therefore, to preserve the project permanently,
you should use either the :func:`save_as() <ansys.optislang.core.optislang.Optislang.save_as>`
or :func:`save_copy() <ansys.optislang.core.optislang.Optislang.save_copy>` method.

To create a project or open an existing one, you use the
:func:`new() <ansys.optislang.core.optislang.Optislang.new>` or
:func:`open() <ansys.optislang.core.optislang.Optislang.open>` method. This code
creates a project: 

.. code:: python

    new_project = Path().cwd() / "new_project.opf"
    osl.new()
    osl.save_as(new_project)

To obtain some general information about a project, run this code:

.. code:: python

    print(osl)

Or, you can run specific requests like shown in this code:

.. code:: python

    print(f"Version: {osl.get_osl_version_string()}")
    print(f"Working directory: {osl.get_working_dir()}")

When you no longer need to use the :class:`Optislang() <ansys.optislang.core.optislang.Optislang>`
instance, close the connection with the optiSLang server by running this code:

.. code:: python

    osl.dispose()

.. _ref_run_python:

================================================
Executing commands from the optiSLang Python API
================================================
When optiSLang is active, you can send individual Python commands to it as a genuine
Python snippet. For example, this code gets general information about the sensitivity
actor:

.. code:: python

    from ansys.optislang.core import Optislang

    osl = Optislang()
    print(osl.run_python_script("""help(actors.SensitivityActor)"""))
    osl.dispose()


.. note::
    Be aware that each time the
    :func:`run_python_script() <ansys.optislang.core.optislang.Optislang.run_python_script>`
    method is called, a new Python context is created inside optiSLang. This
    means that variables from previous calls won't be available.

For longer scripts, instead of sending a string to optiSLang as in the preceding
example, you can send the path to the Python script. This script is converted to a
string automatically. For example, the following code creates a workflow with
variable actors and a calculator. For more information, see the :ref:`ref_simple_calculator`
example.

.. code:: python

    from ansys.optislang.core import Optislang
    from ansys.optislang.core import examples

    osl = Optislang()
    path_to_file = examples.get_files("simple_calculator")[0]
    osl.run_python_file(file_path=path_to_file)
    osl.dispose()

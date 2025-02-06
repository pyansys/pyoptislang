.. _ref_design_evaluation:

==================
Design evaluation
==================
You use the :class:`RootSystem() <ansys.optislang.core.nodes.RootSystem>` class to
create and evaluate designs. To access this class from the
:class:`Optislang() <ansys.optislang.core.optislang.Optislang>` instance,
you use the :func:`project <ansys.optislang.core.project.Project>` method:

.. code:: python

    from ansys.optislang.core import Optislang
    from ansys.optislang.core.project_parametric import Design
    from ansys.optislang.core import examples
    from pathlib import Path

    # open project with defined parameters
    parametric_project = examples.get_files("calculator_with_params")[1][0]
    osl = Optislang(project_path=parametric_project)

    # do not modify original file
    osl.save_as(Path.cwd() / "parametric_project.opf")

    # get root system
    root_system = osl.project.root_system


.. note::

    The *Design evaluation* use case aims for creating and evaluating designs
    on the project root level. It is intended to be used when optiSLang is
    is being used in other environments to manage a parametric workflow, expose input
    and output parameters (that is parameters and responses), and evaluate designs based
    on this parametric workflow. This use case does not cover the generation or monitoring
    of designs of optiSLang internal nested analysis systems, such as **Sensitivity** and
    **Optimization** systems. To support the *Design evaluation* use case, the optiSLang
    project must be prepared in a certain way:

    - Create the workflow and register parameters and responses at the root system level.
    - Connect the workflow to the root system using the **Receive designs** and
      **Send back designs** options.

    For more information, see the :ref:`ref_ten_bar_truss_evaluate_design`
    example and the optiSLang user documentation on generating workflows.


Create a design
---------------
To create an instance of the :class:`Design() <ansys.optislang.core.project_parametric.Design>`
class, you can obtain a design with reference values from the
:class:`RootSystem() <ansys.optislang.core.nodes.RootSystem>` class
and either modify its parameters or specify design parameters from scratch.


Create a design from reference values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If a design has all parameters specified in the project, you can use the
:func:`get_reference_design() <ansys.optislang.core.nodes.RootSystem.create_design>`
method to obtain the design's reference values. You can then modify
parameter values using methods in the
:class:`Design() <ansys.optislang.core.project_parametric.Design>` class.

.. code:: python

    # ...

    from ansys.optislang.core.project_parametric import DesignVariable

    reference_design = root_system.get_reference_design()

    # modify parameter value using ``name`` and ``value``
    reference_design.set_parameter_by_name(name="a", value=12)

    # instance of ``DesignVariable`` or ``Parameter`` can be used as well
    a = DesignVariable(name="a", value=12)
    reference_design.set_parameter(parameter=a)


Create a design from scratch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You can create a design from scratch by directly creating an instance of the
:class:`Design() <ansys.optislang.core.project_parametric.Design>` class.
You do not have to provide parameters when initializing a new design.

.. code:: python

    # design created directly using Design() class
    direct_design = Design(parameters={"a": 3, "b": 4})

    # create empty design and add parameters afterward
    empty_design = Design()
    empty_design.set_parameter_by_name(name="a", value=3)
    empty_design.set_parameter_by_name(name="q", value=4)

    # Remove a parameter if desired
    empty_design.remove_parameter(name="c")

    # Remove all parameters if desired
    empty_design.clear_parameters()


Verify design parameters
~~~~~~~~~~~~~~~~~~~~~~~~
To verify if the design contains all parameters defined in the
project, you use the
:func:`get_missing_parameters_names() <ansys.optislang.core.nodes.RootSystem.get_missing_parameters_names>`
method. To verify if the design contains parameters that are not defined
in the project, you use the
:func:`get_undefined_parameters_names() <ansys.optislang.core.nodes.RootSystem.get_undefined_parameters_names>`
method. Running these verifications are not necessary though, because they
always run internally while evaluating the design.

.. code:: python

    # ...

    missing_parameters = root_system.get_missing_parameters(empty_design)
    undefined_parameters = root_system.get_undefined_parameters(direct_design)


Evaluate the design
-------------------
To evaluate a design, you use the
:func:`evaluate_design() <ansys.optislang.core.nodes.RootSystem.evaluate_design>` method.
This method returns the same :class:`Design() <ansys.optislang.core.project_parametric.Design>`
instance with updated results.

.. code:: python

    # ...

    # single design
    result_design = root_system.evaluate_design(design=reference_design)

.. note::

    optiSLang retains only the last evaluated design at the project root system.
    If results of previous designs are required for later usage, you must store
    them locally. For example, you can store results as an instance of
    the :class:`Design() <ansys.optislang.core.project_parametric.Design>` class.

Finally, when you are done using this :class:`Optislang() <ansys.optislang.core.optislang.Optislang>`
instance, use the :func:`dispose() <ansys.optislang.core.optislang.Optislang.dispose>` method
to close it:

.. code:: python

    osl.dispose()

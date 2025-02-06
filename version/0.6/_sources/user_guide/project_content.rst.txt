.. _ref_project_content:

Project
-------
The :py:class:`Project <ansys.optislang.core.project.Project>` class can be accessed
through the :py:class:`Optislang <ansys.optislang.core.optislang.Optislang>` instance.
This class provides methods for obtaining information about the loaded project,
its content and to execute operations on it:

.. code:: python

    from ansys.optislang.core import Optislang
    from ansys.optislang.core import examples
    from pathlib.Path import Path

    example = examples.get_files("calculator_with_params")[1][0]
    osl = Optislang(project_path=example)
    osl.application.save_copy(Path.cwd() / "project_content.opf")
    project = osl.application.project

    # print project info
    print(project)
    # obtain these information directly
    name = project.get_name()
    location = project.get_location()
    status = project.get_status()


Project structure
-----------------
The optiSLang project can be represented by a rooted tree structure. This structure consists 
of nodes and the connections between these nodes. On the top level, there is one node
designated as a project root system. It is represented by the
:py:class:`RootSystem <ansys.optislang.core.nodes.RootSystem>` 
instance. Each :py:class:`System <ansys.optislang.base_core.nodes.System>`
, such as the :py:class:`RootSystem <ansys.optislang.core.nodes.RootSystem>` class or 
:py:class:`ParametricSystem <ansys.optislang.core.nodes.ParametricSystem>` class, has a 
:py:meth:`get_nodes() <ansys.optislang.core.nodes.System.get_nodes>` method that returns all its
direct children nodes. This provides the ability to determine the entire project structure.

The code shows how to go through all nodes in the project and print information about them:

.. code:: python

    # ...


    def print_node_info(node):
        name = node.get_name()
        type_ = node.get_type()
        status = node.get_status()
        print(name, type_, status)


    def process_nodes(nodes):
        for node in nodes:
            print_node_info(node)
            if isinstance(node, System):
                process_nodes(node.get_nodes())


    root_system = project.root_system
    nodes = root_system.get_nodes()
    process_nodes(nodes)


Parameters
----------
To obtain defined parameters of any parametric system, an instance of the 
:py:class:`ParameterManager <ansys.optislang.core.managers.ParameterManager>`
class can be used. This class contains the
:py:meth:`get_parameters() <ansys.optislang.core.managers.ParameterManager.get_parameters>`, 
method for returning tuple with detailed information for instances of the 
:py:class:`OptimizationParameter <ansys.optislang.core.project_parametric.OptimizationParameter>`,
:py:class:`StochasticParameter <ansys.optislang.core.project_parametric.StochasticParameter>`,
:py:class:`MixedParameter <ansys.optislang.core.project_parametric.MixedParameter>`, and
:py:class:`DepenedentParameter <ansys.optislang.core.project_parametric.DepenedentParameter>` classes.

The :py:meth:`get_parameters_names() <ansys.optislang.core.managers.ParameterManager.get_parameters_names>`
method  returns a tuple with only the names of the parameters:

.. code:: python

    # ...

    parameter_manager = root_system.parameter_manager
    parameters = parameter_manager.get_parameters()
    parameters_names = parameter_manager.get_parameters_names()

To add new parameter, use method 
:py:meth:`add_parameter() <ansys.optislang.core.managers.ParameterManager.add_parameter>`:

.. code:: python

    # ...

    from ansys.optislang.core.project_parametric import OptimizationParameter

    new_parameter = OptimizationParameter(
        name="new_parameter", reference_value=2.5, range=(-5, 10)
    )
    parameter_manager.add_parameter(new_parameter)

To modify parameter, use method
:py:meth:`modify_parameter() <ansys.optislang.core.managers.ParameterManager.modify_parameter>`,
or modify directly parameter property via
:py:meth:`modify_parameter_property() <ansys.optislang.core.managers.ParameterManager.modify_parameter_property>`.
Parameter name is used as identifier in both cases:

.. code:: python

    # ...

    # create new instance of parameter with modified properties
    from ansys.optislang.core.project_parametric import MixedParameter

    modified_parameter = MixedParameter(
        name="new_parameter", reference_value=5, range=(0, 10)
    )
    parameter_manager.modify_parameter(modified_parameter)

    # modify desired property directly
    parameter_manager.modify_parameter_property(
        parameter_name="new_parameter",
        property_name="reference_value",
        property_value=2,
    )


Criteria
--------
To obtain defined criteria of any parametric system, an instance of the
:py:class:`CriteriaManager <ansys.optislang.core.managers.CriteriaManager>`
class can be used. This class contains the
:py:meth:`get_criteria() <ansys.optislang.core.managers.CriteriaManager.get_criteria>`, 
method for returning tuple with detailed information for instances of the 
:py:class:`ConstraintCriterion <ansys.optislang.core.project_parametric.ConstraintCriterion>`,
:py:class:`ObjectiveCriterion <ansys.optislang.core.project_parametric.ObjectiveCriterion>`,
:py:class:`LimitStateCriterion <ansys.optislang.core.project_parametric.LimitStateCriterion>`, and
:py:class:`VariableCriterion <ansys.optislang.core.project_parametric.VariableCriterion>` classes.

.. code:: python

    # ...

    criteria_manager = root_system.criteria_manager
    criteria = criteria_manager.get_criteria()
    criteria_names = criteria_manager.get_criteria_names()

To add new criterion, use method 
:py:meth:`add_criterion() <ansys.optislang.core.managers.CriteriaManager.add_criterion>`:

.. code:: python

    # ...

    from ansys.optislang.core.project_parametric import ConstraintCriterion, ComparisonType

    new_criterion = ConstraintCriterion(
        name="new_criterion",
        expression="1",
        criterion=ComparisonType.LESSEQUAL,
        limit_expression="2",
    )
    criteria_manager.add_criterion(new_criterion)

To modify criterion, use method
:py:meth:`modify_criterion() <ansys.optislang.core.managers.CriteriaManager.modify_criterion>`,
or modify directly criterion property via
:py:meth:`modify_criterion_property() <ansys.optislang.core.managers.CriteriaManager.modify_criterion_property>`.
Criterion name is used as identifier in both cases:

.. code:: python

    # ...

    # create new instance of criterion with modified properties
    from ansys.optislang.core.project_parametric import LimitStateCriterion

    modified_criterion = LimitStateCriterionCriterion(
        name="new_criterion",
        expression="2**2",
        criterion=ComparisonType.LESSLIMITSTATE,
        limit_expression="2^3",
    )
    criteria_manager.modify_criterion(modified_criterion)

    # modify desired property directly
    criteria_manager.modify_criterion_property(
        criterion_name="new_criterion",
        property_name="limit",
        property_value="2^2+1",
    )

Responses
---------
To obtain defined responses of any parametric system, an instance of the
:py:class:`ResponseManager <ansys.optislang.core.managers.ResponseManager>`
class can be used. This class contains the
:py:meth:`get_responses() <ansys.optislang.core.managers.ResponseManager.get_responses>`, 
method for returning tuple with detailed information for instance of the 
:py:class:`Response <ansys.optislang.core.project_parametric.Response>` class.

.. code:: python

    # ...

    response_manager = root_system.response_manager
    responses = response_manager.get_responses()
    responses_names = response_manager.get_responses_names()


When the :py:class:`Optislang <ansys.optislang.core.optislang.Optislang>` instance is no longer 
needed, stop the connection with optiSLang server by running:

.. code:: python

    osl.dispose()


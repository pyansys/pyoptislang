.. _ref_project_content:

Project
-------
You can access the :class:`Project() <ansys.optislang.core.project.Project>` class
from the :class:`Optislang() <ansys.optislang.core.optislang.Optislang>` instance.
This class provides methods for obtaining information about the loaded project and
its content:

.. code:: python

    from ansys.optislang.core import Optislang
    from ansys.optislang.core import examples
    from pathlib.Path import Path

    example = examples.get_files("calculator_with_params")[1][0]
    osl = Optislang(project_path=example)
    osl.save_copy(Path.cwd() / "project_content.opf")
    project = osl.project

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
:class:`RootSystem() <ansys.optislang.core.nodes.RootSystem>` 
instance. Each :class:`System() <ansys.optislang.core.nodes.System>`
, such as the :class:`RootSystem() <ansys.optislang.core.nodes.RootSystem>` class or 
:class:`ParametricSystem() <ansys.optislang.core.nodes.ParametricSystem>` class, has a 
:func:`get_nodes() <ansys.optislang.core.nodes.get_nodes>` method that returns all its
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
:class:`ParameterManager() <ansys.optislang.core.project_parametric.ParameterManager>`
class can be used. This class contains the
:func:`get_parameters() <ansys.optislang.core.project_parametric.ParameterManager.get_parameters>`, 
method for returning tuple with detailed information for instances of the 
:class:`OptimizationParameter() <ansys.optislang.core.project_parametric.OptimizationParameter>`,
:class:`StochasticParameter() <ansys.optislang.core.project_parametric.StochasticParameter>`,
:class:`MixedParameter() <ansys.optislang.core.project_parametric.MixedParameter>`, and
:class:`DepenedentParameter() <ansys.optislang.core.project_parametric.DepenedentParameter>` classes.

The :func:`get_parameters_names() <ansys.optislang.core.project_parametric.ParameterManager.get_parameters_names>`
method  returns a tuple with only the names of the parameters:

.. code:: python

    # ...

    parameter_manager = root_system.parameter_manager
    parameters = parameter_manager.get_parameters()
    parameters_names = parameter_manager.get_parameters_names()

Criteria
--------
To obtain defined criteria of any parametric system, an instance of the
:class:`CriteriaManager() <ansys.optislang.core.project_parametric.CriteriaManager>`
class can be used. This class contains the
:func:`get_criteria() <ansys.optislang.core.project_parametric.CriteriaManager.get_criteria>`, 
method for returning tuple with detailed information for instances of the 
:class:`ConstraintCriterion() <ansys.optislang.core.project_parametric.ConstraintCriterion>`,
:class:`ObjectiveCriterion() <ansys.optislang.core.project_parametric.ObjectiveCriterion>`,
:class:`LimitStateCriterion() <ansys.optislang.core.project_parametric.LimitStateCriterion>`, and
:class:`VariableCriterion() <ansys.optislang.core.project_parametric.VariableCriterion>` classes.

.. code:: python

    # ...

    criteria_manager = root_system.criteria_manager
    criteria = criteria_manager.get_criteria()
    criteria_names = criteria_manager.get_criteria_names()

Responses
---------
To obtain defined responses of any parametric system, an instance of the
:class:`ResponseManager() <ansys.optislang.core.project_parametric.ResponseManager>`
class can be used. This class contains the
:func:`get_responses() <ansys.optislang.core.project_parametric.ResponseManager.get_responses>`, 
method for returning tuple with detailed information for instance of the 
:class:`Response() <ansys.optislang.core.project_parametric.Response>` class.

.. code:: python

    # ...

    response_manager = root_system.response_manager
    responses = criteria_manager.get_responses()
    responses_names = response_manager.get_responses_names()


When the :class:`Optislang() <ansys.optislang.core.optislang.Optislang>` instance is no longer 
needed, stop the connection with optiSLang server by running:

.. code:: python

    osl.dispose()


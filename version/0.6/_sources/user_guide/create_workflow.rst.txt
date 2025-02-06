.. _ref_create_workflow:

===============
Create workflow
===============

Create nodes
------------
New nodes can be created from any system via 
:py:meth:`create_node() <ansys.optislang.core.nodes.System.create_node>` method. Constants 
with types of most of the available nodes are declared in 
:py:mod:`node_types <ansys.optislang.core.node_types>` module.

.. code:: python

    from ansys.optislang.core import Optislang
    from ansys.optislang.core.nodes import DesignFlow
    import ansys.optislang.core.node_types as node_types

    osl = Optislang()
    root_system = osl.application.project.root_system

    sensitivity = root_system.create_node(
        type_=node_types.Sensitivity,
    )


Type of the created node can be also created manually using
:py:class:`NodeType <ansys.optislang.core.node_types.NodeType>` if constant is not available.
Code below shows value of constant 
:py:const:`Sensitivity <ansys.optislang.core.node_types.Sensitivity>` from snippet above:

.. code:: python

    # ...
    manual_type = node_types.NodeType(
        id="Sensitivity", subtype=node_types.AddinType.BUILT_IN
    )


Connect nodes
-------------
Nodes can be connected to the parenting system during creation by specifying argument 
`design_flow` of the :py:meth:`create_node() <ansys.optislang.core.nodes.System.create_node>` 
method.

.. code:: python

    # ...
    Calculator = Sensitivity.create_node(
        type_=node_types.CalculatorSet,
        design_flow=DesignFlow.RECEIVE_SEND,
    )

Another option how to connect node is by using instances of the 
:ref:`Slot classes<ref_slot_classes>`, which can be obtained via
:py:meth:`get_input_slots() <ansys.optislang.core.nodes.Node.get_input_slots>` 
and :py:meth:`get_output_slots() <ansys.optislang.core.nodes.Node.get_output_slots>` methods 
of any node. Parametric systems additionally have
:py:meth:`get_inner_input_slots() <ansys.optislang.core.nodes.ParametricSystem.get_inner_input_slots>` 
and :py:meth:`get_inner_output_slots() <ansys.optislang.core.nodes.ParametricSystem.get_inner_output_slots>` 
methods.


.. code:: python

    # ...
    IIDesign = root_system.get_inner_input_slots("IIDesign")[0]
    IODesign = root_system.get_inner_output_slots("IODesign")[0]

    IReferenceDesign = sensitivity.get_input_slots("IReferenceDesign")[0]
    OReferenceDesign = sensitivity.get_output_slots("OReferenceDesign")[0]

    IODesign.connect_to(IReferenceDesign)
    OReferenceDesign.connect_to(IIDesign)

When the :py:class:`Optislang <ansys.optislang.core.optislang.Optislang>` instance is no longer 
needed, stop the connection with optiSLang server by running:

.. code:: python

    osl.dispose()



# Copyright (C) 2022 - 2025 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
.. _ref_rdo_proxy_solver:

Robust design with optimization with proxy solver
=================================================

This example demonstrates how to create robust design optimization workflow.

It creates multiple parametric systems using `Proxy Solver` node as a solver and then runs the workflow by parts.
"""

#########################################################
# Perform required imports
# ------------------------
# Perform the required imports.

import time
from typing import Union

from ansys.optislang.core import Optislang
import ansys.optislang.core.node_types as node_types
from ansys.optislang.core.nodes import (
    DesignFlow,
    ExecutionOption,
    IntegrationNode,
    Node,
    ParametricSystem,
    ProxySolverNode,
)
from ansys.optislang.core.project_parametric import (
    ComparisonType,
    MixedParameter,
    ObjectiveCriterion,
    OptimizationParameter,
    ParameterType,
)
from ansys.optislang.core.utils import find_all_osl_exec

#########################################################
# Create solver
# -------------
# Define a simple calculator function to solve the variations.


def calculator(hid, X1, X2, X3, X4, X5):
    from math import sin, sqrt

    Y = 0.5 * X1 + X2 + 0.5 * X1 * X2 + 5 * sin(X3) + 0.2 * X4 + 0.1 * X5
    Z = ((-1) * sqrt(abs(Y))) ** 3
    return Y, Z


def calculate(designs):
    result_design_list = []
    print(f"Calculate {len(designs)} designs")
    for design in designs:
        hid = design["hid"]
        parameters = design["parameters"]
        X1 = 0.0
        X2 = 0.0
        X3 = 0.0
        X4 = 0.0
        X5 = 0.0
        for parameter in parameters:
            if parameter["name"] == "X1":
                X1 = parameter["value"]
            elif parameter["name"] == "X2":
                X2 = parameter["value"]
            elif parameter["name"] == "X3":
                X3 = parameter["value"]
            elif parameter["name"] == "X4":
                X4 = parameter["value"]
            elif parameter["name"] == "X5":
                X5 = parameter["value"]
        Y, Z = calculator(hid, X1, X2, X3, X4, X5)

        result_design = {}
        result_design["hid"] = hid
        responses = []
        responses.append({"name": "Y", "value": Y})
        responses.append({"name": "Z", "value": Z})
        result_design["responses"] = responses
        result_design_list.append(result_design)

    print(f"Return {len(result_design_list)} designs")
    return result_design_list


########################################################
# Create workflow creation and execution routines
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  - Define a routine that adds a proxy solver node into parametric system and registers parameters, responses and criteria.
#  - Define a routine that handles `ProxySolver` node execution.


def add_solver_node_to_parent_system(
    parent_system: ParametricSystem,
    parameter_type: Union[
        ParameterType.DETERMINISTIC, ParameterType.MIXED
    ] = ParameterType.DETERMINISTIC,
) -> IntegrationNode:
    """Create and set up solver node within the parent system.

    Parameters
    ----------
    parent_system : ParametricSystem
        Parent system to which the solver node will be added.
    parameter_type: Union[ParameterType.DETERMINISTIC, ParameterType.MIXED]
        Parameter type to be created in parent system.

    Returns
    -------
    IntegrationNode
        The created solver node.
    """
    solver: ProxySolverNode = parent_system.create_node(
        type_=node_types.ProxySolver, name="Proxy Solver", design_flow=DesignFlow.RECEIVE_SEND
    )

    # Set the desired maximum number of designs you handle in one go.
    multi_design_launch_num = -1  # set -1 to solve all designs simultaneously
    solver.set_property("MultiDesignLaunchNum", multi_design_launch_num)
    solver.set_property("ForwardHPCLicenseContextEnvironment", True)

    # Load the available parameters and responses.

    load_json = {}
    load_json["parameters"] = []
    load_json["responses"] = []

    for i in range(1, 6):
        parameter = {"dir": {"value": "input"}, "name": f"X{i}", "value": 1.0}
        load_json["parameters"].append(parameter)

    response_y = {"dir": {"value": "output"}, "name": "Y", "value": 3.0}
    response_z = {"dir": {"value": "output"}, "name": "Z", "value": 3.0}
    load_json["responses"].append(response_y)
    load_json["responses"].append(response_z)

    solver.load(args=load_json)

    # Register parameters and responses to be available in the amop system.

    solver.register_locations_as_parameter()
    solver.register_locations_as_response()

    # Change parameter bounds.

    for i in range(1, 6):
        if parameter_type == ParameterType.DETERMINISTIC:
            parent_system.parameter_manager.modify_parameter(
                OptimizationParameter(name=f"X{i}", reference_value=1.0, range=(-3.14, 3.14))
            )
        elif parameter_type == ParameterType.MIXED:
            parent_system.parameter_manager.modify_parameter(
                MixedParameter(name=f"X{i}", reference_value=1.0, range=(-3.14, 3.14))
            )

    # Create a criterion in the amop system

    parent_system.criteria_manager.add_criterion(
        ObjectiveCriterion(name="obj_y", expression="Y", criterion=ComparisonType.MIN)
    )
    parent_system.criteria_manager.add_criterion(
        ObjectiveCriterion(name="obj_z", expression="Z", criterion=ComparisonType.MIN)
    )
    return solver


def run_proxy_solver_in_parent_system(osl: Optislang, solver: ProxySolverNode):
    """Run the solver node within the parent system.

    Parameters
    ----------
    osl : Optislang
        The optiSLang instance.
    solver : IntegrationNode
        The solver node to run.
    """
    # Loop until get_status() returns "FINISHED" for the project system. Use the GET_DESIGNS query and the SET_DESIGNS command
    # for the Proxy Solver node to get designs and set responses until the system is done.
    while True:
        status = osl.application.project.get_status()
        if status == "FINISHED":
            osl.log.info(f"Project status: {status}")
            break
        elif status == "STOPPED":
            osl.log.info(f"Project status: {status}")
            break
        design_list = solver.get_designs()
        if len(design_list):
            responses_dict = calculate(design_list)
            solver.set_designs(responses_dict)
        time.sleep(0.1)


#########################################################
# Create optiSLang instance
# -------------------------
# Find the optiSLang >= 25.1 executable. Initialize the Optislang class instance with the executable.

available_optislang_executables = find_all_osl_exec()
version, executables = available_optislang_executables.popitem(last=False)
# ProxySolver node is available since version 25R1
if not version >= 251:
    raise KeyError("OptiSLang installation >= 25R1 wasn't found, please specify path manually.")

osl = Optislang(executable=executables[0], loglevel="INFO")
osl.log.info(f"Using optiSLang version {osl.osl_version_string}")


#########################################################
# Create workflow
# ---------------

root_system = osl.application.project.root_system

#########################################################
# AMOP system of your choice
# ~~~~~~~~~~~~~~~~~~~~~~~~~~

amop_system: ParametricSystem = root_system.create_node(type_=node_types.AMOP, name="AMOP")

# Optionally modify algorithm settings
# num_discretization = 2000
# amop_settings = amop_system.get_property("AlgorithmSettings")
# amop_settings["num_discretization"] = num_discretization
# amop_system.set_property("AlgorithmSettings", amop_settings)

# Fast running solver settings

amop_system.set_property("AutoSaveMode", "no_auto_save")
amop_system.set_property("SolveTwice", True)
amop_system.set_property("UpdateResultFile", "at_end")
# amop_system.set_property("WriteDesignStartSetFlag", False)

# Add the Proxy Solver node.

amop_proxy_solver: ProxySolverNode = add_solver_node_to_parent_system(amop_system)

#########################################################
# Optimization on MOP
# ~~~~~~~~~~~~~~~~~~~

oco_on_mop: ParametricSystem = root_system.create_node(type_=node_types.OCO, name="OCO_MOP")

# oco_on_mop.set_property("PreferCriteriaFromSlot", True)
oco_on_mop.set_property("AutoSaveMode", "no_auto_save")
oco_on_mop.set_property("SolveTwice", True)
oco_on_mop.set_property("UpdateResultFile", "at_end")
# oco_on_mop.set_property("ParameterMergingMode", "merge_from_slot")

oco_mop_solver: IntegrationNode = oco_on_mop.create_node(
    type_=node_types.Mopsolver, name="MOP Solver", design_flow=DesignFlow.RECEIVE_SEND
)

# connect
amop_system.get_output_slots("OParameterManager")[0].connect_to(
    oco_on_mop.get_input_slots("IParameterManager")[0]
)
amop_system.get_output_slots("OMDBPath")[0].connect_to(
    oco_mop_solver.get_input_slots("IMDBPath")[0]
)

ref_val = float(1.0000000000000000001)

for i in range(1, 6):
    oco_mop_solver.register_location_as_parameter(
        location={
            "base": "X1",
            "dir": {"enum": ["input", "output"], "value": "input"},
            "id": f"X{i}",
            "suffix": "",
            "value_type": {
                "enum": ["value", "cop", "rmse", "error", "abs_error", "density"],
                "value": "value",
            },
        },
        # {'is_important': True},
        reference_value=ref_val,
    )

oco_mop_solver.register_location_as_response(
    location={
        "base": "Y",
        "dir": {"value": "output"},
        "id": "Y",
        "suffix": "",
        "value_type": {"value": "value"},
    },
    reference_value=0.6987874926243327,
)

oco_mop_solver.register_location_as_response(
    location={
        "base": "Z",
        "dir": {"value": "output"},
        "id": "Z",
        "suffix": "",
        "value_type": {"value": "value"},
    },
    reference_value=-0.5841409930323823,
)

for i in range(1, 6):
    oco_on_mop.parameter_manager.modify_parameter(
        OptimizationParameter(name=f"X{i}", reference_value=1.0, range=(-3.14, 3.14))
    )

oco_on_mop.criteria_manager.add_criterion(
    ObjectiveCriterion(name="obj_y", expression="Y", criterion=ComparisonType.MIN)
)
oco_on_mop.criteria_manager.add_criterion(
    ObjectiveCriterion(name="obj_z", expression="Z", criterion=ComparisonType.MIN)
)

#########################################################
# Filter designs
# ~~~~~~~~~~~~~~

filter_node: IntegrationNode = root_system.create_node(
    type_=node_types.DataMining, name="VALIDATOR_FILTER_NODE"
)

# connect
osl.osl_server.create_input_slot(filter_node.uid, "IBestDesigns")
oco_on_mop.get_output_slots("OBestDesigns")[0].connect_to(
    filter_node.get_input_slots("IBestDesigns")[0]
)


ofilter = {
    "OFilteredBestDesigns": [
        {
            "First": {"name": "AddDesignsFromSlot"},
            "Second": [
                {"design_container": []},
                {"string": "OBestDesigns"},
                {"design_entry": False},
            ],
        }
    ]
}


dmm = filter_node.get_property("DataMiningManager")
dmm["id_filter_list_map"] = ofilter
filter_node.set_property("DataMiningManager", dmm)

getbestdesigns = {
    "First": {"name": "GetBestDesigns"},
    "Second": [{"design_container": []}, {"design_entry": 2}],  # number of best designs - user set?
}

dmm = filter_node.get_property("DataMiningManager")
dmm["id_filter_list_map"]["OFilteredBestDesigns"].append(getbestdesigns)
filter_node.set_property("DataMiningManager", dmm)

filter_node.load()
filter_node.register_location_as_output_slot(
    location="OFilteredBestDesigns", name="OFilteredBestDesigns"
)

#########################################################
# Validator system
# ~~~~~~~~~~~~~~~~

validator_system: ParametricSystem = osl.application.project.root_system.create_node(
    type_=node_types.Sensitivity, name="Validator System"
)
validator_proxy_solver = add_solver_node_to_parent_system(validator_system)

# Connect
filter_node.get_output_slots("OFilteredBestDesigns")[0].connect_to(
    validator_system.get_input_slots("IStartDesigns")[0]
)
oco_on_mop.get_output_slots("OCriteria")[0].connect_to(
    validator_system.get_input_slots("ICriteria")[0]
)

#########################################################
# Design filter for postprocessing
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

append_node: IntegrationNode = osl.application.project.root_system.create_node(
    type_=node_types.DataMining, name="Append Designs"
)

# python script to workaround missing pyoptislang functionalities
command = f"append_node = find_actor('Append Designs')\n" "append_node.init_append_best_designs()\n"
osl.application.project.run_python_script(command)

validator_system.get_output_slots("ODesigns")[0].connect_to(
    append_node.get_input_slots("IDesigns")[0]
)
oco_on_mop.get_output_slots("OMDBPath")[0].connect_to(append_node.get_input_slots("IMDBPath")[0])

#########################################################
# Postprocessing node
# ~~~~~~~~~~~~~~~~~~~

postprocessing_node: Node = root_system.create_node(
    type_=node_types.Postprocessing, name="PostProcessing"
)

# connect
append_node.get_output_slots("OValidatedMDBPath")[0].connect_to(
    postprocessing_node.get_input_slots("IMDBPath")[0]
)

#########################################################
# Optimization on solver
# ~~~~~~~~~~~~~~~~~~~~~~

oco_on_solver: ParametricSystem = root_system.create_node(type_=node_types.OCO, name="OCO_SOLVER")

# oco_on_solver.set_property("PreferCriteriaFromSlot", True)
oco_on_solver.set_property("AutoSaveMode", "no_auto_save")
oco_on_solver.set_property("SolveTwice", True)
oco_on_solver.set_property("UpdateResultFile", "at_end")
# oco_on_solver.set_property("ParameterMergingMode", "merge_from_slot")

oco_proxy_solver = add_solver_node_to_parent_system(oco_on_solver)

# connect
validator_system.get_output_slots("OBestDesigns")[0].connect_to(
    oco_on_solver.get_input_slots("IStartDesigns")[0]
)

#########################################################
# Robustness system
# ~~~~~~~~~~~~~~~~~

robustness: ParametricSystem = root_system.create_node(
    type_=node_types.Robustness, name="Robustness"
)
robustness_solver = add_solver_node_to_parent_system(robustness, ParameterType.MIXED)

# connect
oco_on_solver.get_output_slots("OBestDesigns")[0].connect_to(
    robustness.get_input_slots("INominalDesigns")[0]
)

#########################################################
# MOP node
# ~~~~~~~~

mop_node = root_system.create_node(type_=node_types.Mop, name="MOP")

# connect
robustness.get_output_slots("OMDBPath")[0].connect_to(mop_node.get_input_slots("IMDBPath")[0])
robustness.get_output_slots("OParameterManager")[0].connect_to(
    mop_node.get_input_slots("IParameterManager")[0]
)

osl.log.info("Workflow created")

#########################################################
# Optionally save project
# ~~~~~~~~~~~~~~~~~~~~~~~
# If you want to save the project to some desired location,
# uncomment and edit these lines:
#
# .. code:: python
#
#   from pathlib import Path
#   dir_path = Path(r"<insert-desired-location>")
#   project_name = "rdo_workflow.opf"
#   osl.application.save_as(dir_path / project_name)


#########################################################
# Run workflow
# ------------
# Run the workflow created by the preceding scripts. In this example, workflow is run in multiple steps.
# At first, all systems/nodes are set to inactive except the AMOP system with it's proxy solver. The AMOP system is then executed.
# Then, the other systems/nodes are activated and run one by one.

#########################################################
# AMOP system
# ~~~~~~~~~~~
# Set AMOP system as starting and end point and set all other systems/nodes to inactive state.

amop_system.set_execution_options(
    ExecutionOption.ACTIVE | ExecutionOption.STARTING_POINT | ExecutionOption.END_POINT
)
amop_proxy_solver.set_execution_options(ExecutionOption.ACTIVE)
oco_on_mop.set_execution_options(ExecutionOption.INACTIVE)
oco_mop_solver.set_execution_options(ExecutionOption.INACTIVE)
filter_node.set_execution_options(ExecutionOption.INACTIVE)
validator_system.set_execution_options(ExecutionOption.INACTIVE)
validator_proxy_solver.set_execution_options(ExecutionOption.INACTIVE)
append_node.set_execution_options(ExecutionOption.INACTIVE)
oco_on_solver.set_execution_options(ExecutionOption.INACTIVE)
oco_proxy_solver.set_execution_options(ExecutionOption.INACTIVE)
robustness.set_execution_options(ExecutionOption.INACTIVE)
robustness_solver.set_execution_options(ExecutionOption.INACTIVE)
postprocessing_node.set_execution_options(ExecutionOption.INACTIVE)
mop_node.set_execution_options(ExecutionOption.INACTIVE)

# Start the optiSLang project execution.
osl.log.info("Start execution of the AMOP system.")
osl.application.project.start(wait_for_finished=False)
run_proxy_solver_in_parent_system(osl, amop_proxy_solver)
osl.log.info("AMOP system finished.")

#########################################################
# OCO_MOP system
# ~~~~~~~~~~~~~~
# Remove starting and end point setting from system executed in previous step, set up and start current system.

amop_system.set_execution_options(ExecutionOption.ACTIVE)
oco_on_mop.set_execution_options(
    ExecutionOption.ACTIVE | ExecutionOption.STARTING_POINT | ExecutionOption.END_POINT
)
oco_mop_solver.set_execution_options(ExecutionOption.ACTIVE)
osl.log.info("Start execution of the OCO_MOP system.")
osl.application.project.start()
osl.log.info("OCO_MOP system finished.")

#########################################################
# Validator system
# ~~~~~~~~~~~~~~~~
# Remove starting and end point setting from system executed in previous step, set up and start current system.

oco_on_mop.set_execution_options(ExecutionOption.ACTIVE)
filter_node.set_execution_options(ExecutionOption.ACTIVE | ExecutionOption.STARTING_POINT)
validator_system.set_execution_options(ExecutionOption.ACTIVE | ExecutionOption.END_POINT)
validator_proxy_solver.set_execution_options(ExecutionOption.ACTIVE)
osl.log.info("Start execution of the Validator system.")
osl.application.project.start(wait_for_finished=False)
run_proxy_solver_in_parent_system(osl, validator_proxy_solver)
osl.log.info("Validator system finished.")

#########################################################
# Append Designs filter and postprocessing node
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Remove starting and end point setting from system executed in previous step, set up and start current system.

filter_node.set_execution_options(ExecutionOption.ACTIVE)
validator_system.set_execution_options(ExecutionOption.ACTIVE)
append_node.set_execution_options(ExecutionOption.ACTIVE | ExecutionOption.STARTING_POINT)
postprocessing_node.set_execution_options(ExecutionOption.ACTIVE | ExecutionOption.END_POINT)
osl.log.info("Start execution of the Append Designs filter and Postprocessing node.")
osl.application.project.start()
osl.log.info("Append Designs filter and Postprocessing node finished.")

#########################################################
# Optimization on solver
# ~~~~~~~~~~~~~~~~~~~~~~
# Remove starting and end point setting from system executed in previous step, set up and start current system.

append_node.set_execution_options(ExecutionOption.ACTIVE)
postprocessing_node.set_execution_options(ExecutionOption.ACTIVE)
oco_on_solver.set_execution_options(
    ExecutionOption.ACTIVE | ExecutionOption.STARTING_POINT | ExecutionOption.END_POINT
)
oco_proxy_solver.set_execution_options(ExecutionOption.ACTIVE)
osl.log.info("Start execution of the optimization system with solver.")
osl.application.project.start(wait_for_finished=False)
run_proxy_solver_in_parent_system(osl, oco_proxy_solver)
osl.log.info("Optimization system with solver finished.")

#########################################################
# Robustness system
# ~~~~~~~~~~~~~~~~~
# Remove starting and end point setting from system executed in previous step, set up and start current system.

oco_on_solver.set_execution_options(ExecutionOption.ACTIVE)
robustness.set_execution_options(
    ExecutionOption.ACTIVE | ExecutionOption.STARTING_POINT | ExecutionOption.END_POINT
)
robustness_solver.set_execution_options(ExecutionOption.ACTIVE)
osl.log.info("Start execution of the Robustness system.")
osl.application.project.start(wait_for_finished=False)
run_proxy_solver_in_parent_system(osl, robustness_solver)
osl.log.info("Robustness system finished.")

#########################################################
# MOP system
# ~~~~~~~~~~
# Remove starting and end point setting from system executed in previous step, set up and start current system.
# Finally remove starting and end point execution option from current system.

robustness.set_execution_options(ExecutionOption.ACTIVE)
mop_node.set_execution_options(
    ExecutionOption.ACTIVE | ExecutionOption.STARTING_POINT | ExecutionOption.END_POINT
)
osl.log.info("Start execution of the MOP system.")
osl.application.project.start()
osl.log.info("MOP system finished.")
mop_node.set_execution_options(ExecutionOption.ACTIVE)

osl.application.save()
osl.log.info("Project saved.")

#########################################################
# Stop and cancel project
# ~~~~~~~~~~~~~~~~~~~~~~~
# Stop and cancel the project.

osl.dispose()

#########################################################
# View generated workflow
# -----------------------
# This image shows the generated workflow.
#
# .. image:: ../../_static/04_2_RDO_w_proxysolver.png
#  :width: 1200
#  :alt: Result of script.

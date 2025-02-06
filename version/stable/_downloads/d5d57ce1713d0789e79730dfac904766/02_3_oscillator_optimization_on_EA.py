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
.. _ref_oscillator_optimization_on_EA_create_workflow:

Oscillator optimization using EA flow
-------------------------------------

This example demonstrates how to create and run a direct optimization.

It creates a direct optimization workflow for an oscillator with the Nature Inspired Optimization
(Evolutionary Algorithm) using pyOptiSLang. It then explains how you can optionally save
the project to a desired location.
"""

#########################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform the required imports.

import os
from pathlib import Path

from ansys.optislang.core import Optislang
import ansys.optislang.core.node_types as node_types
from ansys.optislang.core.nodes import DesignFlow, IntegrationNode, ParametricSystem
from ansys.optislang.core.project_parametric import (
    ComparisonType,
    ConstraintCriterion,
    DistributionType,
    MixedParameter,
    ObjectiveCriterion,
    StochasticParameter,
)

example_files_path = Path(os.environ["OSL_EXAMPLES"]) / "00_run_script" / "oscillator" / "files"

#########################################################
# Create optiSLang instance
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Create the optiSLang instance.

osl = Optislang(ini_timeout=60)
print(osl)

#########################################################
# Create workflow
# ~~~~~~~~~~~~~~~

root_system = osl.application.project.root_system

# Create EA optimizer system and postprocessing

noa2: ParametricSystem = root_system.create_node(type_=node_types.NOA2)
omdb_path_slot = noa2.get_output_slots("OMDBPath")[0]

post_processing = root_system.create_node(type_=node_types.Postprocessing)

imdb_path_slot = post_processing.get_input_slots("IMDBPath")[0]
omdb_path_slot.connect_to(imdb_path_slot)

# Create oscillator

python_node: IntegrationNode = noa2.create_node(
    type_=node_types.Python2, design_flow=DesignFlow.RECEIVE_SEND
)
python_node.set_property(
    name="Path",
    value={
        "path": {
            "base_path_mode": {"value": "ABSOLUTE_PATH"},
            "split_path": {"head": "", "tail": str(example_files_path / "oscillator.py")},
        }
    },
)
python_node.set_property(name="MaxParallel", value=4)

python_node.register_location_as_parameter(
    location="m",
    reference_value={
        "kind": {"value": "scalar"},
        "scalar": {"real": 2.0, "imag": 0.0},
    },
)
python_node.register_location_as_parameter(location="k", reference_value=20)
python_node.register_location_as_parameter(
    location="D",
    reference_value={
        "kind": {"value": "scalar"},
        "scalar": {"real": 0.02, "imag": 0.0},
    },
)
python_node.register_location_as_parameter(location="Ekin", reference_value=10)

python_node.register_location_as_response(location="omega_damped", reference_value=4.47124)
python_node.register_location_as_response(location="x_max", reference_value=0.62342)


# Modify registered parameters
noa2.parameter_manager.modify_parameter(
    MixedParameter(
        name="k",
        reference_value=20.0,
        range=(10, 50),
        distribution_type=DistributionType.NORMAL,
        distribution_parameters=(20.0, 1.0),
    )
)
noa2.parameter_manager.modify_parameter(
    StochasticParameter(
        name="Ekin",
        reference_value=10.0,
        distribution_type=DistributionType.NORMAL,
        distribution_parameters=(0.02, 0.002),
    )
)

# Setup EA
noa2.criteria_manager.add_criterion(
    ObjectiveCriterion(name="obj", expression="x_max", criterion=ComparisonType.MIN)
)
noa2.criteria_manager.add_criterion(
    ConstraintCriterion(
        name="constr",
        expression="omega_damped",
        criterion=ComparisonType.LESSEQUAL,
        limit_expression="8.0",
    )
)

optimizer_settings = noa2.get_property("OptimizerSettings")
optimizer_settings["settings"]["MaxGenerations"] = 20
noa2.set_property("OptimizerSettings", optimizer_settings)

# Setup postprocessing
post_processing.set_property("PostprocessingMode", {"value": "automatic"})
post_processing.set_property("ShowPostProcessingDuringRun", False)
post_processing.set_property("WaitForPostprocessingToFinish", True)

#########################################################
# Optionally save project
# ~~~~~~~~~~~~~~~~~~~~~~~
# If you want to save the project to some desired location,
# uncomment and edit these lines:
#
# .. code:: python
#
#   dir_path = Path(r"<insert-desired-location>")
#   project_name = "oscillator_optimization_workflow.opf"
#   osl.application.save_as(dir_path / project_name)


#########################################################
# Run workflow
# ~~~~~~~~~~~~
# Run the workflow created by the preceding scripts.

osl.application.project.start()
osl.application.save()

#########################################################
# Stop and cancel project
# ~~~~~~~~~~~~~~~~~~~~~~~
# Stop and cancel the project.

osl.dispose()

#########################################################
# View generated workflow
# ~~~~~~~~~~~~~~~~~~~~~~~
# This image shows the generated workflow.
#
# .. image:: ../../_static/02_3_optimization_on_EA_pyOSL_workflow.png
#  :width: 400
#  :alt: Result of script.
#

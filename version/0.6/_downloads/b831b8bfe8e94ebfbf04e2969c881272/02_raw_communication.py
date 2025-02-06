# Copyright (C) 2022 - 2024 ANSYS, Inc. and/or its affiliates.
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
.. _ref_osl_server_raw:

Raw communication with osl server
---------------------------------

This example demonstrates how to use PyOptiSLang to perform raw
queries/commands on the optiSLang server using the commands and
queries convenience classes.

"""

#########################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform the required imports.

from pathlib import Path
import tempfile
from typing import TYPE_CHECKING

from ansys.optislang.core import Optislang
import ansys.optislang.core.examples as examples
from ansys.optislang.core.project_parametric import Parameter
from ansys.optislang.core.tcp import server_commands as commands
from ansys.optislang.core.tcp import server_queries as queries

if TYPE_CHECKING:
    from ansys.optislang.core.tcp.osl_server import TcpOslServer

#########################################################
# Create optiSLang instance
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Create the optiSLang instance.

example_path = examples.get_files("ten_bar_truss")[1][0]
tmp_dir = Path(tempfile.mkdtemp())
file_path = tmp_dir / "evaluate_design_example.opf"

osl = Optislang(project_path=example_path, ini_timeout=60)
osl.application.save_as(file_path)
osl_server: TcpOslServer = osl.osl_server

#########################################################
# Modify root project parameters
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Use raw osl server communication to modify the first parameter
# on project root level.

# Get the first parameter on project root level
root_system_uid = osl.project.root_system.uid
root_system_properties = osl_server.send_command(queries.actor_properties(uid=root_system_uid))
root_system_pm_raw = root_system_properties["properties"]["ParameterManager"]

first_parameter = Parameter.from_dict(root_system_pm_raw["parameter_container"][0])

# Print out the reference value
print(f'Parameter "{first_parameter.name}" reference value: {first_parameter.reference_value}')

# Modify the reference value
first_parameter.reference_value = 15.0

# Adapt the parameter manager to the changes and
# send the modified parameter manager back to optiSLang
root_system_pm_raw["parameter_container"][0] = first_parameter.to_dict()

server_response = osl_server.send_command(
    commands.set_actor_property(
        actor_uid=root_system_uid, name="ParameterManager", value=root_system_pm_raw
    )
)

print(f'Modifying parameter reference value: {server_response[0]["status"]}')

# Get and print the (now modified) first parameter on project root level
root_system_properties = osl_server.send_command(queries.actor_properties(uid=root_system_uid))
root_system_pm_raw = root_system_properties["properties"]["ParameterManager"]

modified_first_parameter = Parameter.from_dict(root_system_pm_raw["parameter_container"][0])

print(
    f'Modified parameter "{modified_first_parameter.name}" reference value: {modified_first_parameter.reference_value}'
)

#########################################################
# Stop and cancel project
# ~~~~~~~~~~~~~~~~~~~~~~~
# Stop and cancel the project.

osl.dispose()

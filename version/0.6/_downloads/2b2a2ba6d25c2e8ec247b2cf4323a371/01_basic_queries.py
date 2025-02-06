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
.. _ref_api_basic_queries:

Basic API queries
-----------------

This example demonstrates the usage of the explicit API
to perform basic queries on root project level.

"""

#########################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform the required imports.

from pathlib import Path
import tempfile

from ansys.optislang.core import Optislang
import ansys.optislang.core.examples as examples
from ansys.optislang.core.nodes import ParametricSystem, System

#########################################################
# Helper functions
# ~~~~~~~~~~~~~~~~
# Define a few helper functions.


def print_node(node):
    print(node)


def print_parameters(node):
    if isinstance(node, ParametricSystem):
        print(f"** Parameters of {node.get_name()} **")
        [print(parameter) for parameter in node.parameter_manager.get_parameters()]


def print_responses(node):
    if isinstance(node, ParametricSystem):
        print(f"** Responses of {node.get_name()} **")
        [print(response) for response in node.response_manager.get_responses()]


def print_criteria(node):
    if isinstance(node, ParametricSystem):
        print(f"** Criteria of {node.get_name()} **")
        [print(criterion) for criterion in node.criteria_manager.get_criteria()]


def for_each_child_node(node, function, recursive=False):
    for child_node in node.get_nodes():
        function(child_node)
        if recursive:
            if isinstance(child_node, System):
                for_each_child_node(child_node, function)


#########################################################
# Create optiSLang instance
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Create the optiSLang instance.

osl = Optislang(ini_timeout=60)

#########################################################
# Get paths of example scripts and run them
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get the paths of the example scripts and then run
# these scripts.

paths1 = examples.get_files("oscillator_sensitivity_mop")
paths2 = examples.get_files("oscillator_optimization_on_mop")

osl.run_python_file(paths1[0])
osl.run_python_file(paths2[0])

#########################################################
# Query project tree
# ~~~~~~~~~~~~~~~~~~
# Print each project node/system.
# Print parameters/responses/criteria for each parametric system
# in the project.

print("*** Project Nodes ***")
for_each_child_node(osl.application.project.root_system, print_node, recursive=True)

print("*** Registered parameters of parametric systems ***")
for_each_child_node(osl.application.project.root_system, print_parameters, recursive=True)

print("*** Registered responses of parametric systems ***")
for_each_child_node(osl.application.project.root_system, print_responses, recursive=True)

print("*** Defined criteria of parametric systems ***")
for_each_child_node(osl.application.project.root_system, print_criteria, recursive=True)

#########################################################
# Stop and cancel project
# ~~~~~~~~~~~~~~~~~~~~~~~
# Stop and cancel the project.

osl.dispose()

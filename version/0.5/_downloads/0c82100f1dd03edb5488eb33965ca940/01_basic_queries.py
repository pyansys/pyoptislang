"""
.. _ref_osl_server_basic_queries:

Basic server queries
--------------------

This example demonstrates how to use PyOptiSLang to perform basic
queries/commands on the optiSLang server using the explicit API.

"""

#########################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform the required imports.

from pathlib import Path
import tempfile

from ansys.optislang.core import Optislang
import ansys.optislang.core.examples as examples

#########################################################
# Create optiSLang instance
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Create the optiSLang instance.

example_path = examples.get_files("ten_bar_truss")[1][0]
tmp_dir = Path(tempfile.mkdtemp())
file_path = tmp_dir / "evaluate_design_example.opf"

osl = Optislang(project_path=example_path)
osl.save_as(file_path)

#########################################################
# Get optiSLang server connection info
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Print osl server host and port.
print(f"Server host/address: {osl.get_osl_server().get_host()}")
print(f"Server port: {osl.get_osl_server().get_port()}")

#########################################################
# Get optiSLang info and optiSLang server info
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Print optiSLang and optiSLang server info.
print(f"Server info: {osl.get_osl_server().get_server_info()}")
print(f"optiSLang version: {osl.get_osl_server().get_osl_version()}")
print(f"optiSLang version string: {osl.get_osl_server().get_osl_version_string()}")

#########################################################
# Get basic project info
# ~~~~~~~~~~~~~~~~~~~~~~
# Query basic server/project info.

print(f"Basic project info: {osl.get_osl_server().get_basic_project_info()}")
print(f"Project description: {osl.get_osl_server().get_project_description()}")
print(f"Project file location: {osl.get_osl_server().get_project_location()}")
print(f"Project working directory: {osl.get_osl_server().get_working_dir()}")
print(f"Project name: {osl.get_osl_server().get_project_name()}")
print(f"Project (run) status: {osl.get_osl_server().get_project_status()}")
print(f"Full project tree: {osl.get_osl_server().get_full_project_tree()}")

#########################################################
# Stop and cancel project
# ~~~~~~~~~~~~~~~~~~~~~~~
# Stop and cancel the project.

osl.dispose()

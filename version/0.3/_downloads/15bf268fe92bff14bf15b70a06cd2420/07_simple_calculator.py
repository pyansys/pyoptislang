"""
.. _ref_simple_calculator:

Simple calculator
-----------------

This example demonstrates how to create a simple calculator flow.

It uses the ``simple_calculator.py`` file to create and run
a simple flow of four nodes. It then explains how you can optionally
save a copy of the project to a desired location.
"""

####################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform the required imports.
from ansys.optislang.core import Optislang
import ansys.optislang.core.examples as examples

#########################################################
# Create optiSLang instance
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Create the optiSLang instance.

osl = Optislang()
paths = examples.get_files("simple_calculator")

#########################################################
# Get path of example script and run it
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get the path of the example script and then run this
# script.

osl.run_python_file(paths[0])

#########################################################
# Run workflow
# ~~~~~~~~~~~~
# Run the workflow created by the preceding script.

osl.start()

#########################################################
# Optionally save project
# ~~~~~~~~~~~~~~~~~~~~~~~
# If you want to save the project to some desired
# location, uncomment and edit these lines:
#
# .. code:: python
#
#   path = r'<insert-desired-location>'
#   osl.save_as(os.path.join(path, "test_project.opf"))
#

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
# .. image:: ../../_static/07_simple_calculator.png
#  :width: 400
#  :alt: Result of script.
#

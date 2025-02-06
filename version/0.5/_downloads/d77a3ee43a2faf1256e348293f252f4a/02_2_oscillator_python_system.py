"""
.. _ref_oscillator_python_systems:

Oscillator parametric system
----------------------------

This example demonstrates how to create and run parametric system for an oscillator.

It uses the ``oscillator_system_python.py`` file to create and run the
parametric system for an oscillator. It then explains how you can optionally
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
print(osl)

#########################################################
# Get path of example script and run it
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get the path of the example script and then run
# this script.

paths = examples.get_files("oscillator_system_python")
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
# .. image:: ../../_static/02_2_python_system.png
#  :width: 300
#  :alt: Result of script.
#

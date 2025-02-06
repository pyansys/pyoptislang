"""
.. _ref_oscillator_oscillator_calibration_systems:

Oscillator calibration systems
------------------------------

This example demonstrates how to create and solver chains
using different solver.

It uses the ``oscillatorcalibration_system_python.py``
and ``oscillatorcalibration_system_ascii.py`` files to create
parametric systems for oscillator calibration and then runs
these systems. Lastly, it explains how you can optionally save
a copy of the project to a desired location.
"""

#########################################################
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
# Get paths of example scripts and run them
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get the paths of the example scripts and then run
# these scripts.

paths1 = examples.get_files("oscillatorcalibration_system_python")
paths2 = examples.get_files("oscillatorcalibration_system_ascii")

osl.run_python_file(paths1[0])
osl.run_python_file(paths2[0])

#########################################################
# Run workflow
# ~~~~~~~~~~~~
# Run the workflow created by the preceding scripts.

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
# .. image:: ../../_static/02_5_oscillator_calibration_systems.png
#  :width: 400
#  :alt: Result of script.
#

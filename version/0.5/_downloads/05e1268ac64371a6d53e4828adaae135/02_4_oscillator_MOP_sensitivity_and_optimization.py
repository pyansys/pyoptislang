"""
.. _ref_oscillator_oscillator_MOP_sensitivity_and_optimization:

Oscillator sensitivity and optimization on MOP
----------------------------------------------

This example demonstrates how to create an optimization on MOP flow.

It uses the ``oscillator_sensitivity_mop.py`` file to create a
sensitivity flow for an oscillator and then uses the
``oscillator_optimization_on_mop.py`` file to optimize the MOP
(Metamodel of Optimal Prognosis) flow. It then runs these flows.
Lastly, it explains how you can optionally save a copy of the project
to a desired location.
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

paths1 = examples.get_files("oscillator_sensitivity_mop")
paths2 = examples.get_files("oscillator_optimization_on_mop")

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
# .. image:: ../../_static/02_4_oscillator_MOP_sensitivity_and_optimization.png
#  :width: 600
#  :alt: Result of script.
#

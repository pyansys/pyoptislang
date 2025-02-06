
===============
Troubleshooting
===============

This page explains how to resolve the most common issues encountered 
with the ``ansys-optislang-core`` package. To get more
information about an error, use the ``loglevel`` parameter when
launching optiSLang:

.. code:: python

    from ansys.optislang.core import Optislang

    osl = Optislang(loglevel="DEBUG")
    osl.dispose()


Timeout error when launching optiSLang
--------------------------------------
The default timeout for launching optiSLang is 20 seconds. You can use
the ``ini_timeout`` parameter to increase the timeout when launching
optiSLang:

.. code:: python

    from ansys.optislang.core import Optislang

    osl = Optislang(ini_timeout=30)
    osl.dispose()

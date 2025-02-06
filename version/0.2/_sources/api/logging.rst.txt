Logging
=======
To make the logging of events consistent, PyOptiSLang has a specific
logging architecture with global and local logging instances.

For these two types of loggers, this is the default log message format:

.. code:: pycon

    >>> from ansys.optislang.core import Optislang
    >>> osl = Optislang(loglevel="INFO")
    >>> osl.log.info("This is an useful message")

.. code:: bash

    ===============================================================================
        NEW SESSION - 08/26/2022, 10:02:25
    ===============================================================================

    LEVEL - MODULE - CLASS - FUNCTION - MESSAGE
    INFO -  osl_process - optiSLang_2827215940360 -  __init__ - optiSLang executable has been found for version 222 on path: C:\Program Files\ANSYS Inc\v222\optiSLang\optislang.com
    INFO -  tcp_osl_server - optiSLang_2827215940360 -  __listen_port - optiSLang server port has been received: 5310
    INFO -  tcp_osl_server - optiSLang_2827215940360 -  connect - Connection has been established to host 127.0.0.1 and port 5310.
    INFO -  tmp1 - optiSLang_2827215940360 -  <module> - This is an useful message

Because both types of loggers are based in the Python ``logging`` module, you can use any 
of the tools provided in this module to extend or modify these loggers.

Logging API
-----------
These classes are specific to the :mod:`ansys.optislang.core.logging <ansys.optislang.core.logging>` module:

.. currentmodule:: ansys.optislang.core.logging

.. autosummary::
    :toctree: _autosummary
    :template: class.rst

    OslLogger

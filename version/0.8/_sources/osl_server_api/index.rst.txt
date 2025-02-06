.. _ref_index_osl_server_api:

==============================
optiSLang server API reference
==============================
This section provides descriptions of classes, functions, and attributes
for the direct optiSLang server API exposed through PyOptiSLang.

Currently the :py:class:`ansys.optislang.core.tcp_osl_server.TcpOslServer <ansys.optislang.core.tcp_osl_server.TcpOslServer>` class
is the only actual optiSLang server interface implementation and can be used for raw communication with optiSLang.
It provides explicit methods for accessing specific optiSLang API endpoints. Additionally, the generic
:py:mod:`ansys.optislang.core.tcp_osl_server.TcpOslServer.send_command <ansys.optislang.core.tcp_osl_server.TcpOslServer.send_command>` method
can be used in conjunction with the convenience functions from the :ref:`ansys.optislang.core.server_queries <ref_osl_server_api_queries>` and
:ref:`ansys.optislang.core.server_commands <ref_osl_server_api_commands>` modules.

Use the search feature or click links to view API documentation.

.. toctree::
   :maxdepth: 4
   :hidden:

   optislang_server
   optislang_tcp_server
   optislang_server_queries
   optislang_server_commands

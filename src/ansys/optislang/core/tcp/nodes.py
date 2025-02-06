# Copyright (C) 2022 - 2025 ANSYS, Inc. and/or its affiliates.
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

"""Contains base classes for a nodes and slots."""
from __future__ import annotations

from collections import OrderedDict
import csv
from io import StringIO
import json
import logging
from pathlib import Path
import time
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Tuple, Type, Union, cast

from deprecated.sphinx import deprecated

from ansys.optislang.core.errors import OslCommandError
from ansys.optislang.core.io import File, FileOutputFormat, RegisteredFile, RegisteredFileUsage
from ansys.optislang.core.node_types import AddinType, NodeType, get_node_type_from_str
from ansys.optislang.core.nodes import (
    ACTOR_COMMANDS_RETURN_STATES,
    PROJECT_COMMANDS_RETURN_STATES,
    DesignFlow,
    Edge,
    ExecutionOption,
    InnerInputSlot,
    InnerOutputSlot,
    InputSlot,
    IntegrationNode,
    Node,
    NodeClassType,
    OutputSlot,
    ParametricSystem,
    ProxySolverNode,
    RootSystem,
    Slot,
    SlotType,
    System,
)
from ansys.optislang.core.project_parametric import (
    ConstraintCriterion,
    Design,
    DesignStatus,
    DesignVariable,
    LimitStateCriterion,
    ObjectiveCriterion,
    VariableCriterion,
)
from ansys.optislang.core.tcp import server_commands as commands
from ansys.optislang.core.tcp.managers import (
    TcpCriteriaManagerProxy,
    TcpParameterManagerProxy,
    TcpResponseManagerProxy,
)
from ansys.optislang.core.tcp.osl_server import TcpOslServer

if TYPE_CHECKING:
    from ansys.optislang.core.project_parametric import Criterion


# region Nodes
class TcpNodeProxy(Node):
    """Provides for creating and operating on nodes."""

    def __init__(
        self,
        uid: str,
        osl_server: TcpOslServer,
        type_: NodeType,
        logger=None,
    ) -> None:
        """Create a ``TcpNodeProxy`` instance.

        Parameters
        ----------
        uid: str
            Unique ID of the node.
        osl_server: TcpOslServer
            Object providing access to the optiSLang server.
        type_: NodeType
            Instance of the ``NodeType`` class.
        logger: Any, optional
            Object for logging. If ``None``, standard logging object is used. Defaults to ``None``.
        """
        self._osl_server = osl_server
        self.__uid = uid
        if not isinstance(type_, NodeType):
            raise TypeError(f"Unsupported type of type_: ``{type(type_)}``.")
        self.__type = type_
        self._logger = logging.getLogger(__name__) if logger is None else logger

    def __str__(self):
        """Return formatted string."""
        type_ = self.type.id
        return f"Node type: {type_} Name: {self.get_name()} Uid: {self.uid}"

    @property
    def uid(self) -> str:
        """Unique ID of the node.

        Returns
        -------
        str
            Unique ID of the node.
        """
        return self.__uid

    @property
    def type(self) -> NodeType:
        """Type of the node.

        Returns
        -------
        NodeType
            Instance of the ``NodeType`` class.
        """
        return self.__type

    def control(
        self,
        command: str,
        hid: Optional[str] = None,
        wait_for_completion: bool = True,
        timeout: Union[float, int] = 100,
    ) -> Optional[bool]:
        """Control the node state.

        Parameters
        ----------
        command: str
            Command to execute. Options are ``"start"``, ``"restart"``, ``"stop_gently"``,
            ``"stop"``, and ``"reset"``.
        hid: Optional[str], optional
            Hid entry. The default is ``None``.
        wait_for_completion: bool, optional
            Whether to wait for completion. The default is ``True``.
        timeout: Union[float, int], optional
            Time limit for monitoring the status of the command. The default is ``100 s``.

        Returns
        -------
        Optional[bool]
            ``True`` when successful, ``False`` when failed.
        """
        if hid is None:  # Run command against all designs
            hids = self.get_states_ids()
            if len(hids) == 0:
                raise RuntimeError(
                    "There are no hids available because the node has not been started yet."
                    f" The {command} command cannot be executed."
                )
        else:  # Run command against the given design
            hids = (hid,)

        for hid in hids:
            response = self._osl_server.send_command(
                getattr(commands, command)(actor_uid=self.uid, hid=hid)
            )
            if response[0]["status"] != "success":
                raise Exception(f"{command} command execution failed.")

        if wait_for_completion:
            time_stamp = time.time()
            while True:
                print(
                    f"Project: {self.get_name()} | "
                    f"State: {self.get_status()} | "
                    f"Time: {round(time.time() - time_stamp)}s"
                )
                if self.get_status() == ACTOR_COMMANDS_RETURN_STATES[command]:
                    print(f"{command} command successfully executed.")
                    status = True
                    break
                if (time.time() - time_stamp) > timeout:
                    print("Timeout limit reached. Skip monitoring of command {command}.")
                    status = False
                    break
                time.sleep(3)
            return status
        else:
            return None

    def delete(self) -> None:
        """Delete current node and it's children from active project.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        self._osl_server.remove_node(self.uid)

    def exists(self) -> bool:
        """Get info whether node exists in active project.

        Returns
        -------
        bool
            Whether current node exists in active project.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        try:
            self._osl_server.get_actor_info(
                self.uid,
                include_log_messages=False,
                include_integrations_registered_locations=False,
            )
            return True
        except Exception as e:
            if isinstance(e, OslCommandError) and "No such actor" in str(e):
                return False
            else:
                raise

    def get_ancestors(self) -> Tuple[TcpNodeProxy, ...]:
        """Get tuple of ordered ancestors starting from root system at position 0.

        Returns
        -------
        Tuple[TcpNodeProxy, ...]
            Tuple of ordered ancestors, starting from root system at position.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        if isinstance(self, TcpRootSystemProxy):
            self._logger.warning(
                "``TcpRootSystemProxy`` doesn't have any ancestors, empty tuple will be returned."
            )
            return ()
        project_tree = self._osl_server.get_full_project_tree_with_properties()
        parent_tree = project_tree["projects"][0]["system"]
        ancestors_line_dicts = [
            {
                "type": parent_tree["type"],
                "name": parent_tree["name"],
                "uid": parent_tree["uid"],
                "kind": "root_system",
                "is_parametric_system": True,
            },
        ]
        ancestors_line_dicts = self._find_ancestor_line(
            tree=parent_tree,
            ancestor_line=ancestors_line_dicts,
            node_uid=self.uid,
            current_depth=1,
            was_found=[],
        )
        return create_nodes_from_properties_dicts(
            osl_server=self._osl_server,
            properties_dicts_list=ancestors_line_dicts,
            logger=self._logger,
        )

    def get_execution_options(self) -> ExecutionOption:
        """Get execution options.

        Returns
        -------
        ExecutionOption
            Execution options of the ``Node``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return ExecutionOption(self.get_property("ExecutionOptions"))

    def get_connections(
        self, slot_type: Optional[SlotType] = None, slot_name: Optional[str] = None
    ) -> Tuple[Edge, ...]:
        """Get connections of a given direction and slot.

        Parameters
        ----------
        slot_type: Optional[SlotType], optional
            Slot type, by default ``None``
        slot_name : Optional[str], optional
            Slot name, by default ``None``.

        Returns
        -------
        Tuple[Edge, ...]
            Tuple of connections of given direction and slot.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expire
        """
        project_tree = self._osl_server.get_full_project_tree_with_properties()
        connections = project_tree.get("projects", [{}])[0].get("connections")
        filtered_connections = self._filter_connections(
            connections=connections,
            uid=self.uid,
            slot_type=slot_type,
            slot_name=slot_name,
        )
        edges = []
        for connection in filtered_connections:
            edges.append(
                create_edge_from_dict(
                    osl_server=self._osl_server,
                    project_tree=project_tree["projects"][0]["system"],
                    connection=connection,
                    node=self,
                    logger=self._logger,
                )
            )
        return tuple(edges)

    def get_input_slots(self, name: Optional[str] = None) -> Tuple[TcpInputSlotProxy, ...]:
        """Get current node's input slots.

        Parameters
        ----------
        name : Optional[str], optional
            Slot name, by default ``None``.

        Returns
        -------
        Tuple[TcpInputSlotProxy, ...]
            Tuple of current node's input slots optionally filtered by name.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return cast(Tuple[TcpInputSlotProxy, ...], self._get_slots(type_=SlotType.INPUT, name=name))

    def get_name(self) -> str:
        """Get the name of the node.

        Returns
        -------
        str
            Name of the node.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        actor_info = self._osl_server.get_actor_info(
            uid=self.__uid,
            include_log_messages=False,
            include_integrations_registered_locations=False,
        )
        return actor_info["name"]

    def get_output_slots(self, name: Optional[str] = None) -> Tuple[TcpOutputSlotProxy, ...]:
        """Get current node's output slots.

        Parameters
        ----------
        name : Optional[str], optional
            Slot name, by default ``None``.

        Returns
        -------
        Tuple[TcpInputSlotProxy, ...]
            Tuple of current node's output slots optionally filtered by name.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return cast(
            Tuple[TcpOutputSlotProxy, ...], self._get_slots(type_=SlotType.OUTPUT, name=name)
        )

    def get_parent(self) -> TcpNodeProxy:
        """Get the instance of the parent node.

        Returns
        -------
        TcpNodeProxy
            Instance of the parent node.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self.get_ancestors()[-1]

    def get_parent_name(self) -> str:
        """Get the name of the parent node.

        Returns
        -------
        str
            Name of the parent node.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self.get_parent().get_name()

    def get_properties(self) -> dict:
        """Get the raw server output with the node properties.

        Returns
        -------
        dict
            Dictionary with the node properties.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self._osl_server.get_actor_properties(uid=self.uid)

    def get_property(self, name: str) -> Any:
        """Get property from properties dictionary.

        Parameters
        ----------
        name
            Name of property to be returned.

        Returns
        -------
        Any
            Value of given property, ``None`` if property doesn't exits.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self.get_properties().get(name, None)

    def get_registered_files(self) -> Tuple[RegisteredFile, ...]:
        """Get node's registered files.

        Returns
        -------
        Tuple[RegisteredFile, ...]
            Tuple of registered files.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        registered_files_uids = self._get_info()["registered_files"]
        if not registered_files_uids:
            return ()
        project_registered_files = self._osl_server.get_basic_project_info()["projects"][0][
            "registered_files"
        ]
        return tuple(
            [
                RegisteredFile(
                    path=Path(file["local_location"]["split_path"]["head"])
                    / file["local_location"]["split_path"]["tail"],
                    id=file["ident"],
                    comment=file["comment"],
                    tag=file["tag"],
                    usage=file["usage"],
                )
                for file in project_registered_files
                if file["tag"] in registered_files_uids
            ]
        )

    def get_result_files(self) -> Tuple[RegisteredFile, ...]:
        """Get node's result files.

        Returns
        -------
        Tuple[RegisteredFile, ...]
            Tuple of result files.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return tuple(
            filter(
                lambda file: file.usage == RegisteredFileUsage.OUTPUT_FILE,
                self.get_registered_files(),
            )
        )

    def get_states_ids(self) -> Tuple[str, ...]:
        """Get available actor states ids.

        Returns
        -------
        Tuple[str, ...]
            Actor states ids.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        states = self._osl_server.get_actor_states(self.uid)
        if not states.get("states", None):
            return tuple([])
        return tuple([state["hid"] for state in states["states"]])

    def get_status(self) -> str:
        """Get the status of the node.

        Returns
        -------
        str
            Status of the node.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        actor_info = self._osl_server.get_actor_info(
            uid=self.__uid,
            include_log_messages=False,
            include_integrations_registered_locations=False,
        )
        return actor_info["status"]

    @deprecated(version="0.6.0", reason="Use :py:attr:`TcpNodeProxy.type` instead.")
    def get_type(self) -> NodeType:
        """Get the type of the node.

        Returns
        -------
        NodeType
            Type of the node.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        actor_info = self._osl_server.get_actor_info(
            uid=self.__uid,
            include_log_messages=False,
            include_integrations_registered_locations=False,
        )
        return get_node_type_from_str(node_id=actor_info["type"])

    def set_execution_options(self, value: ExecutionOption) -> None:
        """Set execution options.

        Parameters
        ----------
        value : ExecutionOption
            Execution options of the ``Node``. More execution options can be
            combined using the bitwise operations.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.

        Examples
        --------
        Combination of more execution options using the bitwise operation.

        >>> ...
        >>> node.set_execution_options(
                ExecutionOption.ACTIVE | ExecutionOption.STARTING_POINT
            )
        """
        return self.set_property("ExecutionOptions", value.value)

    def set_property(self, name: str, value: Any) -> None:
        """Set node's property.

        Parameters
        ----------
        name : str
            Property name.
        value : Any
            Property value.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        self._osl_server.set_actor_property(actor_uid=self.uid, name=name, value=value)

    def create_input_slot(self, slot_name: str, type_hint: Optional[str] = None) -> None:
        """Create dynamic input slot.

        Parameters
        ----------
        slot_name : str
            Name of the slot to be created. By default ``None``.
        type_hint: Optional[str], optional
            Type of the slot. By default ``None``.
            Available types:

            * ``Undefined``, undefined type
            * ``Bool``
            * ``Integer``
            * ``Unsigned Integer``
            * ``Unsigned Integer Vector``
            * ``Real``
            * ``String``
            * ``String List``
            * ``Variant``
            * ``Path``
            * ``Parameter``
            * ``Parameter Set``
            * ``Parameter Manager``
            * ``Design``
            * ``Designpoint``
            * ``Design Container``
            * ``Bool Vector``
            * ``Criterion``
            * ``Criterion Sequence``
            * ``Designentry``
            * ``Runinfo Meta``
            * ``Runinfo``
            * ``Designpoints``

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        self._osl_server.create_input_slot(
            actor_uid=self.uid, slot_name=slot_name, type_hint=type_hint
        )

    def create_output_slot(self, slot_name: str, type_hint: Optional[str] = None) -> None:
        """Create dynamic output slot.

        Parameters
        ----------
        slot_name : str
            Name of the slot to be created.
        type_hint: Optional[str], optional
            Type of the slot. By default ``None``.
            Available types:

            * ``Undefined``, undefined type
            * ``Bool``
            * ``Integer``
            * ``Unsigned Integer``
            * ``Unsigned Integer Vector``
            * ``Real``
            * ``String``
            * ``String List``
            * ``Variant``
            * ``Path``
            * ``Parameter``
            * ``Parameter Set``
            * ``Parameter Manager``
            * ``Design``
            * ``Designpoint``
            * ``Design Container``
            * ``Bool Vector``
            * ``Criterion``
            * ``Criterion Sequence``
            * ``Designentry``
            * ``Runinfo Meta``
            * ``Runinfo``
            * ``Designpoints``

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        self._osl_server.create_output_slot(
            actor_uid=self.uid, slot_name=slot_name, type_hint=type_hint
        )

    def set_name(self, new_name: str) -> None:
        """Rename node.

        .. note:: Method is supported for Ansys optiSLang version >= 25.2 only.

        Parameters
        ----------
        new_name: str
            New node name.

        Raises
        ------
        NotImplementedError
            Raised when unsupported optiSLang server is used.
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        if (
            self._osl_server.osl_version.major == 25 and self._osl_server.osl_version.minor >= 2
        ) or self._osl_server.osl_version.major > 25:
            self._osl_server.rename_node(actor_uid=self.uid, new_name=new_name)
        else:
            raise NotImplementedError("Method is supported for Ansys optiSLang version >= 25.2.")

    def _filter_connections(
        self,
        connections: List[dict],
        uid: str,
        slot_type: Optional[SlotType] = None,
        slot_name: Optional[str] = None,
    ) -> List[Dict[Any, Any]]:
        """Filter list of connections by given node uid, slot type and optionally slot name.

        Parameters
        ----------
        connections : List[dict]
            List of connections.
        uid: str
            Node uid.
        slot_type: Optional[SlotType], optional
            Type of the slot, by default ``None``.
        slot_name: Optional[str], optional
            Name of the slot, by default ``None``.

        Returns
        -------
        Tuple[dict]
            Tuple of filtered connections dictionaries.
        """
        filtered_connections: List[Dict[Any, Any]] = []

        # skip for combination of inner slot with TcpNodeProxy or it's subclasses
        if not (
            isinstance(self.__class__, TcpSystemProxy) or issubclass(self.__class__, TcpSystemProxy)
        ) and isinstance(slot_type, SlotType):
            if slot_type in [SlotType.INNER_INPUT, SlotType.INNER_OUTPUT]:
                return filtered_connections

        # prepare keys for tcp server output dictionary
        if isinstance(slot_type, SlotType):
            direction = SlotType.to_dir_str(slot_type)
            uid_keys = [direction + "_uuid"]
            slot_name_keys = [direction + "_slot"]
            slot_type_key = [direction + "_slot_is_inner"]
            slot_type_is_inner = slot_type in [SlotType.INNER_INPUT, SlotType.INNER_OUTPUT]
        else:
            uid_keys = ["receiving_uuid", "sending_uuid"]
            slot_name_keys = ["receiving_slot", "sending_slot"]
        for connection in connections:
            # filter connections, that do not contain current node
            if uid not in [connection[key] for key in uid_keys]:
                continue
            # filter slots, that do not contain given name
            if slot_name is not None and slot_name not in [
                connection[key] for key in slot_name_keys
            ]:
                continue
            # filter connections by slot type (only for system and subclasses), since nodes
            # do not have inner input slots and this combination was excluded at the beginning
            if (
                isinstance(self.__class__, TcpSystemProxy)
                or issubclass(self.__class__, TcpSystemProxy)
            ) and isinstance(slot_type, SlotType):
                # `[receiving_slot, sending_slot]_is_inner` key included in connection dict
                if slot_type_key in connection.keys():
                    if not connection[slot_type_key] == slot_type_is_inner:
                        continue
                # `[receiving_slot, sending_slot]_is_inner` key not included in connection dict
                else:
                    info = self._osl_server.get_actor_info(
                        connection[uid_keys[0]],
                        include_log_messages=False,
                        include_integrations_registered_locations=False,
                    )
                    if True in [
                        item["name"] == connection[slot_name_keys[0]]
                        for item in info[slot_type.name.lower() + "_slots"]
                    ]:
                        connection[slot_name_keys[0] + "_is_inner"] = slot_type_is_inner
                    else:
                        continue
            filtered_connections.append(connection)
        return filtered_connections

    def _get_info(self) -> dict:
        """Get the raw server output with the node info.

        Returns
        -------
        dict
            Dictionary with the node info.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self._osl_server.get_actor_info(self.uid)

    def _get_parent_dict(self) -> dict:
        """Get the unique ID of the parent node.

        Returns
        -------
        dict
            Dictionary with necessary information for creating instance of parent node.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        project_tree = self._osl_server.get_full_project_tree_with_properties()
        root_system_uid = project_tree["projects"][0]["system"]["uid"]
        parent_tree = project_tree["projects"][0]["system"]
        return self._find_parent_node_info(
            tree=parent_tree,
            parent_info=root_system_uid,
            node_uid=self.uid,
        )

    def _get_slots(
        self, type_: Optional[SlotType] = None, name: Optional[str] = None
    ) -> Tuple[TcpSlotProxy, ...]:
        """Get current node's slots of given type and name.

        Parameters
        ----------
        type_: Optional[SlotType], optional
            Type of slots to be returned, by default ``None``.
        name : Optional[str], optional
            Slot name, by default ``None``.

        Returns
        -------
        Tuple[TcpSlotProxy, ...]
            Tuple of current node's slots of given type.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        info = self._get_info()
        if isinstance(type_, SlotType):
            keys = [type_.name.lower() + "_slots"]
        else:
            keys = [slot_type.name.lower() + "_slots" for slot_type in SlotType]
        slots_dicts_mapping = {}
        for key in keys:
            slots_dicts_mapping[key] = info.get(key, [])
        slots_list = []
        for slot_type, slots_dicts in slots_dicts_mapping.items():
            for slot_dict in slots_dicts:
                if name is not None and name != slot_dict["name"]:
                    continue
                slots_list.append(
                    TcpSlotProxy.create_slot(
                        osl_server=self._osl_server,
                        node=self,
                        name=slot_dict["name"],
                        type_=SlotType.from_str(string=slot_type[0:-6]),
                        type_hint=slot_dict["type"],
                    )
                )
        return tuple(slots_list)

    def _get_status_info(self) -> Tuple[dict, ...]:
        """Get node's status info for each state.

        Returns
        -------
        Tuple[dict, ...]
            Tuple with status info dictionary for each state.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        hids = self.get_states_ids()
        return tuple([self._osl_server.get_actor_status_info(self.uid, hid) for hid in hids])

    @deprecated(version="0.6.0", reason="Not used anymore.")
    def _is_parametric_system(self, uid: str) -> bool:
        """Check if the system is parametric.

        Parameters
        ----------
        uid : str
            Unique ID of the system.

        Returns
        -------
        bool
            ``True`` when the system is parametric, ``False`` otherwise.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        props = self._osl_server.get_actor_properties(uid=uid)
        return "ParameterManager" in props

    @staticmethod
    def _find_ancestor_line(
        tree: dict,
        ancestor_line: List[dict],
        node_uid: str,
        current_depth: int,
        was_found: list,
    ) -> List[dict]:
        """Get ancestor line starting from root system.

        Parameters
        ----------
        tree: dict
            Dictionary with children nodes.
        ancestor_line: List[dict]
            List of dictionaries with necessary information for node creation.
        node_uid: str
            Unique ID of the node for which to search for the parent.
        current_depth: int
            Current depth of the search.
        was_found: list
            Empty list, until node_uid is located.

        Returns
        -------
        str
            Unique ID of the parent node.

        Raises
        ------
        RuntimeError
            Raised when node was not located in structure tree.
        """
        for node in tree["nodes"]:
            if len(was_found) == 1:
                break
            if node["uid"] == node_uid:
                was_found.append("True")
                break
            if node["kind"] == "system":
                ancestor_line.append(
                    {
                        "type": node["type"],
                        "name": node["name"],
                        "uid": node["uid"],
                        "kind": node["kind"],
                        "is_parametric_system": "ParameterManager" in node.get("properties", {}),
                    }
                )
                TcpNodeProxy._find_ancestor_line(
                    tree=node,
                    ancestor_line=ancestor_line,
                    node_uid=node_uid,
                    current_depth=current_depth + 1,
                    was_found=was_found,
                )
                if not was_found:
                    ancestor_line.pop(-1)
        return ancestor_line

    @staticmethod
    def _find_nodes_with_name(
        name: str,
        tree: dict,
        properties_dicts_list: List[dict],
        current_depth: int,
        max_search_depth: int = 1,
    ) -> List[dict]:
        """Find nodes with the specified name.

        Parameters
        ----------
        name : str
            Node name.
        tree : dict
            Tree to search for nodes with the specified name.
        properties_dicts_list : dict
            Dictionary with properties.
        current_depth: int
            Current depth of the search.
        max_search_depth: int, optional
            Maximum depth of the search. The default is ``1``. Set to ``-1``
            to search throughout the full depth.

        Returns
        -------
        List[dict]
            List of dictionaries with necessary information for creation of a node.
        """
        for node in tree["nodes"]:
            if node["name"] == name:
                properties_dicts_list.append(
                    {
                        "type": node["type"],
                        "name": node["name"],
                        "uid": node["uid"],
                        "parent_uid": tree["uid"],
                        "parent_name": tree["name"],
                        "kind": node["kind"],
                        "is_parametric_system": node.get("properties", {}).get(
                            "ParameterManager", False
                        ),
                    }
                )
            if node["kind"] == "system" and (
                current_depth < max_search_depth or max_search_depth == -1
            ):
                TcpNodeProxy._find_nodes_with_name(
                    name=name,
                    tree=node,
                    properties_dicts_list=properties_dicts_list,
                    current_depth=current_depth + 1,
                    max_search_depth=max_search_depth,
                )
        return properties_dicts_list

    @staticmethod
    def _find_node_with_uid(
        uid: str,
        tree: dict,
        properties_dicts_list: List[dict],
        current_depth: int,
        max_search_depth: int = 1,
    ) -> List[dict]:
        """Find a node with a specified unique ID.

        Parameters
        ----------
        uid : str
            Unique ID of the node.
        tree : dict
            Tree to search for nodes with the specified unique ID.
        properties_dicts_list : List[dict]
            Dictionary with properties.
        current_depth: int
            Current depth of the search.
        max_search_depth: int, optional
            Maximum depth of the search. The default is ``1``. Set to ``-1``
            to search throughout the full depth.

        Returns
        -------
        List[dict]
            List of dictionaries with the necessary information for creation of a node.
        """
        for node in tree["nodes"]:
            if len(properties_dicts_list) != 0:
                break
            if node["uid"] == uid:
                properties_dicts_list.append(
                    {
                        "type": node["type"],
                        "name": node["name"],
                        "uid": node["uid"],
                        "parent_uid": tree["uid"],
                        "parent_name": tree["name"],
                        "kind": node["kind"],
                        "is_parametric_system": "ParameterManager" in node.get("properties", {}),
                    }
                )
                break
            if node["kind"] == "system" and (
                current_depth < max_search_depth or max_search_depth == -1
            ):
                TcpNodeProxy._find_node_with_uid(
                    uid=uid,
                    tree=node,
                    properties_dicts_list=properties_dicts_list,
                    current_depth=current_depth + 1,
                    max_search_depth=max_search_depth,
                )
        return properties_dicts_list

    @staticmethod
    def _find_parent_node_info(tree: dict, parent_info: dict, node_uid: str) -> dict:
        """Get dictionary with necessary information for parent node creation.

        Parameters
        ----------
        tree: dict
            Dictionary with children nodes.
        parent_info: str
            Dictionary with necessary information for parent node creation.
        node_uid: str
            Unique ID of the node for which to search for the parent.

        Returns
        -------
        dict
            Dictionary with necessary information for parent node creation.

        Raises
        ------
        RuntimeError
            Raised when node was not located in structure tree.
        """
        for node in tree["nodes"]:
            if parent_info.get("child_node_was_found"):
                return parent_info
            if node["uid"] == node_uid:
                parent_info["child_node_was_found"] = True
            if node["kind"] == "system":
                new_parent_info = {
                    "type": node["type"],
                    "name": node["name"],
                    "uid": node["uid"],
                    "kind": node["kind"],
                    "is_parametric_system": "ParameterManager" in node.get("properties", {}),
                }
                TcpNodeProxy._find_parent_node_info(
                    tree=node,
                    parent_info=new_parent_info,
                    node_uid=node_uid,
                )

        # FIXME
        # Raise to satisfy type checker
        raise RuntimeError


class TcpIntegrationNodeProxy(TcpNodeProxy, IntegrationNode):
    """Provides for creating and operating on integration nodes."""

    def __init__(
        self,
        uid: str,
        osl_server: TcpOslServer,
        type_: NodeType,
        logger=None,
    ) -> None:
        """Create an ``TcpIntegrationNodeProxy`` instance.

        Parameters
        ----------
        uid: str
            Unique ID.
        osl_server: TcpOslServer
            Object providing access to the optiSLang server.
        type_: NodeType
            Instance of the ``NodeType`` class.
        logger: Any, optional
            Object for logging. If ``None``, standard logging object is used. Defaults to ``None``.
        """
        super().__init__(
            uid=uid,
            osl_server=osl_server,
            type_=type_,
            logger=logger,
        )

    def get_available_input_locations(self) -> Tuple:
        """Get available input locations for the current node.

        Returns
        -------
        Tuple
            Available input locations.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: test
        return tuple(self._osl_server.get_available_input_locations(self.uid))

    def get_available_output_locations(self) -> Tuple:
        """Get available output locations for the current node.

        Returns
        -------
        Tuple
            Available output locations.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: test
        return tuple(self._osl_server.get_available_output_locations(self.uid))

    def get_internal_variables(self, include_reference_values: bool = True) -> Tuple:
        """Get internal variables.

        Parameters
        ----------
        include_reference_values: bool
            Whether reference values are to be included. By default ``True``.

        Returns
        -------
        Tuple
            Registered internal variables.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return tuple(
            self._osl_server.get_actor_internal_variables(
                uid=self.uid, include_reference_values=include_reference_values
            )
        )

    def get_registered_input_slots(self, include_reference_values: bool = True) -> Tuple:
        """Get registered input slots.

        Parameters
        ----------
        include_reference_values: bool
            Whether reference values are to be included. By default ``True``.

        Returns
        -------
        Tuple
            Registered input slots.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return tuple(
            self._osl_server.get_actor_registered_input_slots(
                uid=self.uid, include_reference_values=include_reference_values
            )
        )

    def get_registered_output_slots(self, include_reference_values: bool = True) -> Tuple:
        """Get registered output slots.

        Parameters
        ----------
        include_reference_values: bool
            Whether reference values are to be included. By default ``True``.

        Returns
        -------
        Tuple
            Registered output slots.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return tuple(
            self._osl_server.get_actor_registered_output_slots(
                uid=self.uid, include_reference_values=include_reference_values
            )
        )

    def get_registered_parameters(self, include_reference_values: bool = True) -> Tuple:
        """Get registered parameters.

        Parameters
        ----------
        include_reference_values: bool
            Whether reference values are to be included. By default ``True``.

        Returns
        -------
        Tuple
            Registered parameters.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return tuple(
            self._osl_server.get_actor_registered_parameters(
                uid=self.uid, include_reference_values=include_reference_values
            )
        )

    def get_registered_responses(self, include_reference_values: bool = True) -> Tuple:
        """Get registered responses.

        Parameters
        ----------
        include_reference_values: Optional[bool], optional
            Whether reference values are to be included. By default ``True``.

        Returns
        -------
        Tuple
            Registered responses.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return tuple(
            self._osl_server.get_actor_registered_responses(
                uid=self.uid, include_reference_values=include_reference_values
            )
        )

    def load(self, args: Optional[Dict[str, Any]] = None) -> None:
        """Explicitly load the node.

        Some optiSLang nodes support/need an explicit LOAD prior to being able to register
        or to make registering more convenient.

        Parameters
        ----------
        args: Optional[Dict[str, any]], optional
            Additional arguments, by default ``None``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: test
        self._osl_server.load(uid=self.uid, args=args)

    def register_location_as_input_slot(
        self,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:
        """Register the given location as an input slot.

        Parameters
        ----------
        location : Any
            Location to be registered.
        name : Optional[str], optional
            Name of the registered input slot, by default ``None``.
        reference_value : Optional[Any], optional
            Reference value of the registered input slot, by default ``None``.

        Returns
        -------
        str
            Name of the actual created input slot.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self._osl_server.register_location_as_input_slot(
            uid=self.uid, location=location, name=name, reference_value=reference_value
        )

    def register_location_as_internal_variable(
        self,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:
        """Register the given location as an internal variable.

        Parameters
        ----------
        location : Any
            Location to be registered.
        name : Optional[str], optional
            Name of the registered internal variable, by default ``None``.
        reference_value : Optional[Any], optional
            Reference value of the registered internal variable, by default ``None``.

        Returns
        -------
        str
            Name of the actual created internal variable.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self._osl_server.register_location_as_internal_variable(
            uid=self.uid, location=location, name=name, reference_value=reference_value
        )

    def register_location_as_output_slot(
        self,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:
        """Register the given location as an output slot.

        Parameters
        ----------
        location : Any
            Location to be registered.
        name : Optional[str], optional
            Name of the registered output slot, by default ``None``.
        reference_value : Optional[Any], optional
            Reference value of the registered output slot, by default ``None``.

        Returns
        -------
        str
            Name of the actual created output slot.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self._osl_server.register_location_as_output_slot(
            uid=self.uid, location=location, name=name, reference_value=reference_value
        )

    def register_location_as_parameter(
        self,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:
        """Register the given location as a parameter.

        Parameters
        ----------
        location : Any
            Location to be registered.
        name : Optional[str], optional
            Name of the registered parameter, by default ``None``.
        reference_value : Optional[Any], optional
            Reference value of the registered parameter, by default ``None``.

        Returns
        -------
        str
            Name of the actual created parameter.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self._osl_server.register_location_as_parameter(
            uid=self.uid, location=location, name=name, reference_value=reference_value
        )

    def register_location_as_response(
        self,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:
        """Register the given location as a response.

        Parameters
        ----------
        location : Any
            Location to be registered.
        name : Optional[str], optional
            Name of the registered response, by default ``None``.
        reference_value : Optional[Any], optional
            Reference value of the registered response, by default ``None``.

        Returns
        -------
        str
            Name of the actual created response.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self._osl_server.register_location_as_response(
            uid=self.uid, location=location, name=name, reference_value=reference_value
        )

    def register_locations_as_parameter(self) -> None:
        """Register all available locations as parameter initially.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: test
        self._osl_server.register_locations_as_parameter(uid=self.uid)

    def register_locations_as_response(self) -> None:
        """Register all available locations as response initially.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: test
        self._osl_server.register_locations_as_response(uid=self.uid)

    def re_register_locations_as_parameter(self) -> None:
        """Adjust all input locations with the already registered parameters.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: test
        self._osl_server.re_register_locations_as_parameter(uid=self.uid)

    def re_register_locations_as_response(self) -> None:
        """Adjust all input locations with the already registered responses.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: test
        self._osl_server.re_register_locations_as_response(uid=self.uid)


class TcpProxySolverNodeProxy(TcpIntegrationNodeProxy, ProxySolverNode):
    """Provides for creating and operating on integration nodes."""

    def __init__(
        self,
        uid: str,
        osl_server: TcpOslServer,
        type_: NodeType,
        logger=None,
    ) -> None:
        """Create an ``TcpProxySolverProxy`` instance.

        Parameters
        ----------
        uid: str
            Unique ID.
        osl_server: TcpOslServer
            Object providing access to the optiSLang server.
        type_: NodeType
            Instance of the ``NodeType`` class.
        logger: Any, optional
            Object for logging. If ``None``, standard logging object is used. Defaults to ``None``.
        """
        super().__init__(
            uid=uid,
            osl_server=osl_server,
            type_=type_,
            logger=logger,
        )

    def get_designs(self) -> List[dict]:
        """Get pending designs from parent node.

        Returns
        -------
        List[dict]
           List of pending designs.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self._osl_server.get_designs(self.uid)

    def set_designs(self, designs: Iterable[dict]) -> None:
        """Set calculated designs.

        Parameters
        ----------
        Iterable[dict]
            Iterable of calculated designs.
            Design format:
            {
                "hid": "0.1",
                "responses": [{"name": "res1", "value": 1.0}, {...}, ...],
            }

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        self._osl_server.set_designs(actor_uid=self.uid, designs=designs)


# endregion


# region Systems
class TcpSystemProxy(TcpNodeProxy, System):
    """Provides for creating and operating on a system."""

    def __init__(
        self,
        uid: str,
        osl_server: TcpOslServer,
        type_: NodeType,
        logger=None,
    ) -> None:
        """Create an ``TcpSystemProxy`` instance.

        Parameters
        ----------
        uid: str
            Unique ID.
        osl_server: TcpOslServer
            Object providing access to the optiSLang server.
        type_: NodeType
            Instance of the ``NodeType`` class.
        logger: Any, optional
            Object for logging. If ``None``, standard logging object is used. Defaults to ``None``.
        """
        super().__init__(
            uid=uid,
            osl_server=osl_server,
            type_=type_,
            logger=logger,
        )

    def create_node(
        self,
        type_: Union[NodeType, str],
        name: Optional[str] = None,
        design_flow: Union[DesignFlow, str] = DesignFlow.NONE,
    ) -> TcpNodeProxy:
        """Create a new node in current system in active project.

        Parameters
        ----------
        type_ : Union[NodeType, str]
            Type of created node.
        name : Optional[str], optional
            Name of created node, by default None.
        design_flow : Optional[Union[DesignFlow, str]], optional
            Design flow, by default ``None``.

        Returns
        -------
        TcpNodeProxy
            Instance of the created node.

        Raises
        ------
        TypeError
            Raised when unsupported type of ``type_`` is passed.
        ValueError
            Raised when unsupported value of ``type_`` is passed.
        """
        if isinstance(type_, str):
            type_ = get_node_type_from_str(node_id=type_)
        if not isinstance(type_, NodeType):
            raise TypeError(
                f"Invalid type of ``type_: {type(type_)}``, "
                "``NodeType`` or ``str`` was expected."
            )
        if type_.id == "RunnableSystem":
            raise ValueError("Creation of RootSystem is not supported.")

        (
            algorithm_type,
            integration_type,
            mop_node_type,
            node_type,
        ) = self._get_subtypes(addin_type=type_.subtype)

        if not isinstance(design_flow, (str, DesignFlow)):
            raise TypeError(f"Design flow type: `{type(design_flow)}` is not supported.")
        if isinstance(design_flow, str):
            design_flow = DesignFlow.from_str(design_flow)

        uid = self._osl_server.create_node(
            type_=type_.id,
            name=name,
            algorithm_type=algorithm_type,
            integration_type=integration_type,
            mop_node_type=mop_node_type,
            node_type=node_type,
            parent_uid=self.uid,
            design_flow=design_flow.name.lower(),
        )
        info = self._osl_server.get_actor_info(
            uid=uid, include_log_messages=False, include_integrations_registered_locations=False
        )
        info["is_parametric_system"] = "estimated_designs" in info.keys()
        return create_nodes_from_properties_dicts(
            osl_server=self._osl_server, properties_dicts_list=[info], logger=self._logger
        )[0]

    def delete_children_nodes(self) -> None:
        """Delete all children nodes from the active project.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        nodes = self.get_nodes()
        for node in nodes:
            node.delete()

    def find_node_by_uid(self, uid: str, search_depth: int = 1) -> Optional[TcpNodeProxy]:
        """Find a node in the system with a specified unique ID.

        This method searches only in the descendant nodes for the current system.

        Parameters
        ----------
        uid : str
            Unique ID of the node.
        search_depth: int, optional
            Depth of the node subtree to search. The default is ``1``, which corresponds
            to direct children nodes of the current system. Set to ``-1`` to search throughout
            the full depth.

        Returns
        -------
        Optional[TcpNodeProxy]
            ``TcpNodeProxy`` with the specified unique ID. If this ID isn't located in any
            descendant node, ``None`` is returned.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        TypeError
            Raised when an unknown type of component is found.
        """
        project_tree = self._osl_server.get_full_project_tree_with_properties()
        if self.uid == project_tree["projects"][0]["system"]["uid"]:
            system_tree = project_tree["projects"][0]["system"]
        else:
            located_tree = self._find_subtree(
                tree=project_tree["projects"][0]["system"],
                uid=self.uid,
                nodes_tree=[],
            )
            if len(located_tree) == 1:
                system_tree = located_tree[0]
            else:
                raise RuntimeError(f"Current system `{self.uid}` wasn't found.")

        properties_dicts_list = self._find_node_with_uid(
            uid=uid,
            tree=system_tree,
            properties_dicts_list=[],
            current_depth=1,
            max_search_depth=search_depth,
        )

        if len(properties_dicts_list) == 0:
            self._logger.error(f"Node `{uid}` was not found in the current system.")
            return None

        return create_nodes_from_properties_dicts(
            osl_server=self._osl_server,
            properties_dicts_list=properties_dicts_list,
            logger=self._logger,
        )[0]

    def find_nodes_by_name(self, name: str, search_depth: int = 1) -> Tuple[TcpNodeProxy, ...]:
        """Find nodes in the system with a specified name.

        This method searches only in the descendant nodes for the current system.

        Parameters
        ----------
        name : str
            Name of the node.
        search_depth: int, optional
            Depth of the node subtree to search. The default is ``1``, which corresponds
            to direct children nodes of the current system. Set to ``-1`` to search throughout
            the full depth.

        Returns
        -------
        Tuple[TcpNodeProxy, ...]
            Tuple of nodes with the specified name.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        TypeError
            Raised when an unknown type of component is found.
        """
        project_tree = self._osl_server.get_full_project_tree_with_properties()
        if self.uid == project_tree["projects"][0]["system"]["uid"]:
            system_tree = project_tree["projects"][0]["system"]
        else:
            located_tree = self._find_subtree(
                tree=project_tree["projects"][0]["system"],
                uid=self.uid,
                nodes_tree=[],
            )
            if len(located_tree) == 1:
                system_tree = located_tree[0]
            else:
                raise RuntimeError(f"Current system `{self.uid}` wasn't found.")

        properties_dicts_list = self._find_nodes_with_name(
            name=name,
            tree=system_tree,
            properties_dicts_list=[],
            current_depth=1,
            max_search_depth=search_depth,
        )

        if len(properties_dicts_list) == 0:
            self._logger.error(f"Node `{name}` not found in the current system.")
            return tuple()

        return create_nodes_from_properties_dicts(
            osl_server=self._osl_server,
            properties_dicts_list=properties_dicts_list,
            logger=self._logger,
        )

    def get_nodes(self) -> Tuple[TcpNodeProxy, ...]:
        """Get the direct children nodes.

        Returns
        -------
        Tuple[TcpNodeProxy, ...]
            Current system nodes.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return create_nodes_from_properties_dicts(
            osl_server=self._osl_server,
            properties_dicts_list=self._get_nodes_dicts(),
            logger=self._logger,
        )

    def _get_nodes_dicts(self) -> Tuple[dict, ...]:
        """Get data for children nodes.

        Returns
        -------
        Tuple[dict, ...]
            Tuple of dictionaries with data for children nodes.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        RuntimeError
            Raised when the system wasn't located in the project tree.
        """
        project_tree = self._osl_server.get_full_project_tree_with_properties()
        if self.uid == project_tree["projects"][0]["system"]["uid"]:
            system_tree = project_tree["projects"][0]["system"]
        else:
            located_tree = self._find_subtree(
                tree=project_tree["projects"][0]["system"],
                uid=self.uid,
                nodes_tree=[],
            )
            if len(located_tree) == 1:
                system_tree = located_tree[0]
            else:
                raise RuntimeError(f"Current system `{self.uid}` wasn't found.")

        children_dicts_list = []
        for node in system_tree["nodes"]:
            children_dicts_list.append(
                {
                    "type": node["type"],
                    "name": node["name"],
                    "uid": node["uid"],
                    "kind": node["kind"],
                    "is_parametric_system": "ParameterManager" in node.get("properties", {}),
                }
            )
        return tuple(children_dicts_list)

    @staticmethod
    def _find_subtree(tree: dict, uid: str, nodes_tree: List[dict]) -> dict:
        """Find the subtree with a root node matching a specified unique ID.

        Parameters
        ----------
        tree: dict
            Dictionary with the parent structure.
        uid: str
            Unique ID of the subtree root node.
        nodes_tree: List[dict]
            List with tree of searched node.

        Returns
        -------
        dict
            Dictionary representing the subtree found.
        """
        for node in tree["nodes"]:
            if len(nodes_tree) != 0:
                break
            if node["uid"] == uid:
                nodes_tree.append(node)
            if node["kind"] == "system":
                TcpSystemProxy._find_subtree(tree=node, uid=uid, nodes_tree=nodes_tree)
        return nodes_tree

    @staticmethod
    def _get_subtypes(
        addin_type: AddinType,
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Get subtypes in tcp server input format.

        Parameters
        ----------
        addin_type: AddinType
            Node's subtype.

        Returns
        -------
        Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]
            algorithm_type, integration_type, mop_node_type, node_type
        """
        if not isinstance(addin_type, AddinType):
            raise TypeError(f"Unsupported value of addin_type: ``{type(addin_type)}``.")

        algorithm_type, integration_type, mop_node_type, node_type = None, None, None, None
        if addin_type == AddinType.BUILT_IN:
            pass
        elif addin_type == AddinType.INTEGRATION_PLUGIN:
            integration_type = "integration_plugin"
        elif addin_type == AddinType.PYTHON_BASED_INTEGRATION_PLUGIN:
            integration_type = "python_based_integration_plugin"
        elif addin_type == AddinType.PYTHON_BASED_ALGORITHM_PLUGIN:
            algorithm_type = "python_based_algorithm_plugin"
        elif addin_type == AddinType.ALGORITHM_PLUGIN:
            algorithm_type = "algorithm_plugin"
        elif addin_type == AddinType.PYTHON_BASED_MOP_NODE_PLUGIN:
            mop_node_type = "python_based_mop_node_plugin"
        elif addin_type == AddinType.PYTHON_BASED_NODE_PLUGIN:
            node_type = "python_based_node_plugin"
        else:
            raise ValueError(f"Unsupported value of addin_type: ``{addin_type}``.")

        return algorithm_type, integration_type, mop_node_type, node_type


# endregion


# region ParametricSystems
class TcpParametricSystemProxy(TcpSystemProxy, ParametricSystem):
    """Provides for creating and operationg on parametric system."""

    def __init__(
        self,
        uid: str,
        osl_server: TcpOslServer,
        type_: NodeType,
        logger=None,
    ) -> None:
        """Create a parametric system.

        Parameters
        ----------
        uid: str
            Unique ID.
        osl_server: TcpOslServer
            Object providing access to the optiSLang server.
        type_: NodeType
            Instance of the ``NodeType`` class.
        logger: Any, optional
            Object for logging. If ``None``, standard logging object is used. Defaults to ``None``.
        """
        super().__init__(
            uid=uid,
            osl_server=osl_server,
            type_=type_,
            logger=logger,
        )
        self.__criteria_manager = TcpCriteriaManagerProxy(uid, osl_server)
        self.__parameter_manager = TcpParameterManagerProxy(uid, osl_server)
        self.__response_manager = TcpResponseManagerProxy(uid, osl_server)

    @property
    def criteria_manager(self) -> TcpCriteriaManagerProxy:
        """Criteria manager of the current system.

        Returns
        -------
        TcpCriteriaManagerProxy
            Instance of the ``TcpCriteriaManagerProxy`` class.
        """
        return self.__criteria_manager

    @property
    def parameter_manager(self) -> TcpParameterManagerProxy:
        """Parameter manager of the current system.

        Returns
        -------
        TcpParameterManagerProxy
            Instance of the ``TcpParameterManagerProxy`` class.
        """
        return self.__parameter_manager

    @property
    def response_manager(self) -> TcpResponseManagerProxy:
        """Response manager of the current system.

        Returns
        -------
        TcpResponseManagerProxy
            Instance of the ``TcpResponseManagerProxy`` class.
        """
        return self.__response_manager

    def get_inner_input_slots(
        self, name: Optional[str] = None
    ) -> Tuple[TcpInnerInputSlotProxy, ...]:
        """Get current node's inner input slots.

        Parameters
        ----------
        name : Optional[str], optional
            Slot name, by default ``None``.

        Returns
        -------
        Tuple[TcpInnerInputSlotProxy, ...]
            Tuple of current node's inner input slots optionally filtered by name.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return cast(
            Tuple[TcpInnerInputSlotProxy, ...],
            self._get_slots(type_=SlotType.INNER_INPUT, name=name),
        )

    def get_inner_output_slots(
        self, name: Optional[str] = None
    ) -> Tuple[TcpInnerOutputSlotProxy, ...]:
        """Get current node's inner output slots.

        Parameters
        ----------
        name : Optional[str], optional
            Slot name, by default ``None``.

        Returns
        -------
        Tuple[TcpInnerOutputSlotProxy, ...]
            Tuple of current node's inner output slots optionally filtered by name.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return cast(
            Tuple[TcpInnerOutputSlotProxy, ...],
            self._get_slots(type_=SlotType.INNER_OUTPUT, name=name),
        )

    def get_omdb_files(self) -> Tuple[File]:
        """Get paths to omdb files.

        This method is supported only when the client runs on the same file
        system as the server, i.e., the server is not remote.

        Returns
        -------
        Tuple[File]
            Tuple with File objects containing path.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        RuntimeError
            Raised when the server is remote.
        """
        if self._osl_server.is_remote:
            raise RuntimeError(
                "Paths to omdb files cannot be provided when connected to the remote server."
            )

        statuses_info = self._get_status_info()
        wdirs = [Path(status_info["working dir"]) for status_info in statuses_info]
        omdb_files = []
        for wdir in wdirs:
            omdb_files.extend([File(path) for path in wdir.glob("*.omdb")])
        return tuple(omdb_files)

    def save_designs_as_json(self, hid: str, file_path: Union[Path, str]) -> File:
        """Save designs for a given state to JSON file.

        Parameters
        ----------
        hid : str
            Actor's state.
        file_path : Union[Path, str]
            Path to the file.

        Returns
        -------
        File
            Object representing saved file.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        TypeError
            Raised when the `hid` is `None`
            -or-
            `file_path` is `None` or unsupported type.
        ValueError
            Raised when ``hid`` does not exist.
        """
        return self.__save_designs_as(hid, file_path, FileOutputFormat.JSON)

    def save_designs_as_csv(self, hid: str, file_path: Union[Path, str]) -> File:
        """Save designs for a given state to CSV file.

        Parameters
        ----------
        hid : str
            Actor's state.
        file_path : Union[Path, str]
            Path to the file.

        Returns
        -------
        File
            Object representing saved file.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        TypeError
            Raised when the `hid` is `None`
            -or-
            `file_path` is `None` or unsupported type.
        ValueError
            Raised when ``hid`` does not exist.
        """
        return self.__save_designs_as(hid, file_path, FileOutputFormat.CSV)

    def __save_designs_as(self, hid: str, file_path: Union[Path, str], format: FileOutputFormat):
        """Save designs for a given state.

        Parameters
        ----------
        hid : str
            Actor's state.
        file_path : Union[Path, str]
            Path to the file.
        format : FileOutputFormat
            Format of the file.

        Returns
        -------
        File
            Object representing saved file.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        TypeError
            Raised when the `hid` is `None`
            -or-
            `file_path` is `None` or unsupported type.
        ValueError
            Raised when ``format`` is not unsupported
            -or-
            ``hid`` does not exist.
        """
        if hid is None:
            raise TypeError("Actor's state cannot be `None`.")
        if file_path is None:
            raise TypeError("Path to the file cannot be `None`.")
        if isinstance(file_path, str):
            file_path = Path(file_path)
        if not isinstance(file_path, Path):
            raise TypeError(
                "Type of the `file_path` argument is not supported: `file_path` = "
                f"`{type(file_path)}`."
            )

        designs = self._get_designs_dicts()
        if not designs.get(hid):
            raise ValueError(f"Design for given `hid` argument not available: `hid` = `{hid}.")

        if format == FileOutputFormat.JSON:
            file_output = json.dumps(designs[hid])
            newline = None
        elif format == FileOutputFormat.CSV:
            file_output = self.__convert_design_dict_to_csv(designs[hid])
            newline = ""
        else:
            raise ValueError(f"Output file format `{format}` is not supported.")

        with open(file_path, "w", newline=newline) as f:
            f.write(file_output)
        return File(file_path)

    @deprecated(
        version="0.9.0",
        reason="Use :py:meth:`TcpParametricSystemProxy.save_designs_as_json` or "
        ":py:meth:`TcpParametricSystemProxy.save_designs_as_csv` instead.",
    )
    def save_designs_as(
        self,
        hid: str,
        file_name: str,
        format: FileOutputFormat = FileOutputFormat.JSON,
        dir: Optional[Union[Path, str]] = None,
    ) -> File:
        """Save designs for a given state.

        Parameters
        ----------
        hid : str
            Actor's state.
        file_name : str
            Name of the file.
        format : FileOutputFormat, optional
            Format of the file, by default ``FileOutputFormat.JSON``.
        dir : Optional[Union[Path, str]], optional
            Directory, where file should be saved, by default ``None``.
            Project's working directory is used by default.

        Returns
        -------
        File
            Object representing saved file.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        TypeError
            Raised when incorrect type of ``dir`` is passed.
        ValueError
            Raised when unsupported value of ``format`` or non-existing ``hid``
            is passed.
        """
        if dir is not None and isinstance(dir, str):
            dir = Path(dir)
        elif dir is None:
            dir_str = (
                self._osl_server.get_basic_project_info()
                .get("projects", [{}])[0]
                .get("working_dir", None)
            )
            if dir_str is None:
                raise RuntimeError("Projects working directory is not available.")
            dir = Path(dir_str)

        if not isinstance(dir, Path):
            raise TypeError(f"Unsupported type of dir: `{type(dir)}`.")

        designs = self._get_designs_dicts()
        if not designs.get(hid):
            raise ValueError(f"Design for given hid: `{hid}` not available.")

        if format == FileOutputFormat.JSON:
            output_file = json.dumps(designs[hid])
            newline = None
        elif format == FileOutputFormat.CSV:
            output_file = self.__convert_design_dict_to_csv(designs[hid])
            newline = ""
        else:
            raise ValueError(f"Output type `{format}` is not supported.")

        output_file_path = dir / (file_name + format.to_str())
        with open(output_file_path, "w", newline=newline) as f:
            f.write(output_file)
        return File(output_file_path)

    def _get_designs_dicts(self) -> OrderedDict:
        """Get parametric system's designs.

        Returns
        -------
        OrderedDict
            Ordered dictionary of designs, key is hid and value
            is list of corresponding designs.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        statuses_info = self._get_status_info()
        if not statuses_info:
            return {}
        designs = {}
        # TODO: sort by hid? -> delete / use OrderedDict
        for status_info in statuses_info:
            designs[status_info["hid"]] = status_info["designs"]
            for idx, design in enumerate(designs[status_info["hid"]]["values"]):
                self.__append_status_info_to_design(design, status_info["design_status"][idx])
        for i in range(2, len(statuses_info[0]["designs"]["values"][0]["hid"].split("."))):
            designs = self.__sort_dict_by_key_hid(
                designs, max(1, len(statuses_info[0]["designs"]["values"][0]["hid"].split(".")) - i)
            )
        for hid, design in designs.items():
            # sort by design number, stripped from hid prefix
            # (0.10, 0.9 ..., 0.1) -> (0.1, ..., 0.9, 0.10)
            design["values"] = self.__sort_list_of_dicts_by_hid(
                design["values"], len(hid.split("."))
            )
        return designs

    @staticmethod
    def __append_status_info_to_design(design: dict, status_info: dict) -> None:
        if design["hid"] != status_info["id"]:
            raise ValueError(f'{design["hid"]} != {status_info["id"]}')
        to_append = {
            key: status_info[key] for key in ("feasible", "status", "pareto_design", "directory")
        }
        design.update(to_append)

    @staticmethod
    def __convert_design_dict_to_csv(designs: dict) -> str:
        csv_buffer = StringIO()
        try:
            csv_writer = csv.writer(csv_buffer)
            header = ["Design"]
            header.append("Feasible")
            header.append("Status")
            header.append("Pareto")
            header.extend(designs["constraint_names"])
            header.extend(designs["limit_state_names"])
            header.extend(designs["objective_names"])
            header.extend(designs["parameter_names"])
            header.extend(designs["response_names"])
            csv_writer.writerow(header)
            for design in designs["values"]:
                line = [design["hid"]]
                line.append(design["feasible"])
                line.append(design["status"])
                line.append(design["pareto_design"])
                line.extend(design["constraint_values"])
                line.extend(design["limit_state_values"])
                line.extend(design["objective_values"])
                line.extend(design["parameter_values"])
                line.extend(design["response_values"])
                csv_writer.writerow(line)
            return csv_buffer.getvalue()
        finally:
            if csv_buffer is not None:
                csv_buffer.close()

    @staticmethod
    def __sort_list_of_dicts_by_hid(unsorted_list: List[dict], sort_by_position: int) -> List[dict]:
        sort_key = lambda x: int(x["hid"].split(".")[sort_by_position])
        return sorted(unsorted_list, key=sort_key)

    @staticmethod
    def __sort_dict_by_key_hid(unsorted_dict: dict, sort_by_position: int) -> dict:
        sort_key = lambda item: int(item[0].split(".")[sort_by_position])
        return OrderedDict(sorted(unsorted_dict.items(), key=sort_key))


# endregion


# region RootSystem
class TcpRootSystemProxy(TcpParametricSystemProxy, RootSystem):
    """Provides for creating and operating on a project system."""

    def __init__(
        self,
        uid: str,
        osl_server: TcpOslServer,
        logger=None,
    ) -> None:
        """Create an instance of ``TcpRootSystemProxy`` class.

        Parameters
        ----------
        uid: str
            Unique ID.
        osl_server: TcpOslServer
            Object providing access to the optiSLang server.
        logger: Any, optional
            Object for logging. If ``None``, standard logging object is used. Defaults to ``None``.
        """
        super().__init__(
            uid=uid,
            osl_server=osl_server,
            type_=NodeType(id="RunnableSystem", subtype=AddinType.BUILT_IN),
            logger=logger,
        )

    def control(
        self,
        command: str,
        hid: Optional[str] = None,
        wait_for_completion: bool = True,
        timeout: Union[float, int] = 100,
    ) -> Optional[bool]:
        """Control the root system state.

        Parameters
        ----------
        command: str
            Command to execute. Options are ``"start"``, ``"restart"``, ``"stop_gently"``,
            ``"stop"``, and ``"reset"``.
        hid: Optional[str], optional
            Hid, by default ``None``.
        wait_for_completion: bool, optional
            Whether to wait for completion. The default is ``True``.
        timeout: Union[float, int], optional
            Time limit for monitoring the status of the command. The default is ``100 s``.

        Returns
        -------
        Optional[bool]
            ``True`` when successful, ``False`` when failed.
        """
        response = self._osl_server.send_command(getattr(commands, command)())
        if response[0]["status"] != "success":
            raise Exception(f"{command} command execution failed.")

        if wait_for_completion:
            time_stamp = time.time()
            while True:
                print(
                    f"Project: {self.get_name()} | "
                    f"State: {self.get_status()} | "
                    f"Time: {round(time.time() - time_stamp)}s"
                )
                if self.get_status() == PROJECT_COMMANDS_RETURN_STATES[command]:
                    print(f"{command} command successfully executed.")
                    status = True
                    break
                if (time.time() - time_stamp) > timeout:
                    print("Timeout limit reached. Skip monitoring of command {command}.")
                    status = False
                    break
                time.sleep(3)
            return status
        else:
            return None

    def delete(self) -> None:
        """Delete current node and it's children from active project.

        Raises
        ------
        NotImplementedError
            Raised always.
        """
        raise NotImplementedError("``RootSystem`` cannot be deleted.")

    def evaluate_design(self, design: Design) -> Design:
        """Evaluate a design.

        Parameters
        ----------
        design: Design
            Instance of a ``Design`` class with defined parameters.

        Returns
        -------
        Design
            Evaluated design.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        evaluate_dict = {}
        for parameter in design.parameters:
            evaluate_dict[parameter.name] = parameter.value

        output_dict = self._osl_server.evaluate_design(evaluate_dict=evaluate_dict)
        return self.__create_evaluated_design(
            input_design=design, evaluate_dict=evaluate_dict, results=output_dict[0]
        )

    def get_missing_parameters_names(self, design: Design) -> Tuple[str, ...]:
        """Get the names of the parameters that are missing in a design.

        This method compare design parameters with the root system's parameters.

        Parameters
        ----------
        design: TcpDesign
            Instance of the ``Design`` class with defined parameters.

        Returns
        -------
        Tuple[str, ...]
            Names of the parameters that are missing in the instance of ``Design`` class.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self.__get_sorted_difference_of_sets(
            first=self.parameter_manager.get_parameters_names(),
            second=design.parameters_names,
        )

    def get_reference_design(self) -> Design:
        """Get the design with reference values of the parameters.

        Returns
        -------
        TcpDesign
            Instance of the ``TcpDesign`` class with defined parameters and reference values.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        parameters = self.parameter_manager.get_parameters()
        responses = self.response_manager.get_responses()
        criteria = self.criteria_manager.get_criteria()
        sorted_criteria = self.__categorize_criteria(criteria=criteria)
        return Design(
            parameters=parameters,
            constraints=sorted_criteria.get("constraints", []),
            limit_states=sorted_criteria.get("limit_states", []),
            objectives=sorted_criteria.get("objectives", []),
            variables=sorted_criteria.get("variables", []),
            responses=responses,
        )

    def get_undefined_parameters_names(self, design: Design) -> Tuple[str, ...]:
        """Get the names of the parameters that are not defined in the root system.

        This method compare design parameters with the root system's parameters.

        Parameters
        ----------
        design: TcpDesign
            Instance of the ``Design`` class with defined parameters.

        Returns
        -------
        Tuple[str, ...]
            Names of the parameters that are not defined in the root system.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self.__get_sorted_difference_of_sets(
            first=design.parameters_names,
            second=self.parameter_manager.get_parameters_names(),
        )

    def __create_evaluated_design(
        self, input_design: Design, evaluate_dict: Dict, results: Dict
    ) -> Design:
        """Create a new instance of ``Design`` with results.

        Parameters
        ----------
        input_design: Design
            Design that was evaluated.
        evaluate_dict: dict
            Dictionary used for evaluation.
        results: Dict
            Output from the evaluation of the input design.

        Returns
        -------
        Design
            Instance of the ``Design`` class with results.
        """
        id = results["result_design"]["hid"]
        feasibility = results["result_design"]["feasible"]
        status = DesignStatus.from_str(results["result_design"]["status"])

        # constraint
        constraints = []
        for position, constraint in enumerate(results["result_design"]["constraint_names"]):
            constraints.append(
                DesignVariable(
                    name=constraint,
                    value=results["result_design"]["constraint_values"][position],
                )
            )
        # limit state
        limit_states = []
        for position, limit_state in enumerate(results["result_design"]["limit_state_names"]):
            limit_states.append(
                DesignVariable(
                    name=limit_state,
                    value=results["result_design"]["limit_state_values"][position],
                )
            )
        # objective
        objectives = []
        for position, objective in enumerate(results["result_design"]["objective_names"]):
            objectives.append(
                DesignVariable(
                    name=objective,
                    value=results["result_design"]["objective_values"][position],
                )
            )
        # responses
        responses = []
        for position, response in enumerate(results["result_design"]["response_names"]):
            responses.append(
                DesignVariable(
                    name=response,
                    value=results["result_design"]["response_values"][position],
                )
            )
        # variables
        variables = []
        for position, variable in enumerate(results["result_design"]["variable_names"]):
            variables.append(
                DesignVariable(
                    name=variable,
                    value=results["result_design"]["variable_values"][position],
                )
            )

        # create instance of design with new values
        output_design = Design(
            parameters=input_design.parameters,
            constraints=constraints,
            limit_states=limit_states,
            objectives=objectives,
            variables=variables,
            responses=responses,
            feasibility=feasibility,
            design_id=id,
            status=status,
        )

        # compare input and output values
        input_design_parameters = input_design.parameters_names
        output_parameters = results["result_design"]["parameter_names"]
        missing_parameters = self.__get_sorted_difference_of_sets(
            output_parameters, input_design_parameters
        )
        undefined_parameters = self.__get_sorted_difference_of_sets(
            input_design_parameters, output_parameters
        )
        unused = self.__compare_input_w_processed_parameters_values(evaluate_dict, results)

        if undefined_parameters:
            self._logger.debug(f"Parameters ``{undefined_parameters}`` weren't used.")
        if missing_parameters:
            self._logger.warning(
                f"Parameters ``{missing_parameters}`` were missing, "
                "reference values were used for evaluation and list of parameters will be updated."
            )
        if unused:
            self._logger.warning(
                "Values of parameters were changed:"
                f"{[par[0] + ': ' + str(par[1]) + ' -> ' + str(par[2]) for par in unused]}"
            )

        # update design with missing parameters
        # (parameters not defined in input design, but used for evaluation)
        for parameter in missing_parameters:
            position = results["result_design"]["parameter_names"].index(parameter)
            output_design.set_parameter_by_name(
                parameter,
                results["result_design"]["parameter_values"][position],
                False,
            )

        return output_design

    @staticmethod
    def __categorize_criteria(criteria: Tuple[Criterion, ...]) -> Dict[str, List[Criterion]]:
        """Get criteria sorted by its kinds.

        Parameters
        ----------
        criteria : Tuple[Criterion]
           Tuple of unsorted criteria.

        Returns
        -------
        Dict[str, Criterion]
            Dictionary of criteria sorted by its kinds.

        Raises
        ------
        TypeError
            Raised when an invalid type of criterion is passed.
        """
        constraints = []
        limit_states = []
        objectives = []
        variables = []
        for criterion in criteria:
            if isinstance(criterion, ConstraintCriterion):
                constraints.append(criterion)
            elif isinstance(criterion, LimitStateCriterion):
                limit_states.append(criterion)
            elif isinstance(criterion, ObjectiveCriterion):
                objectives.append(criterion)
            elif isinstance(criterion, VariableCriterion):
                variables.append(criterion)
            else:
                raise TypeError(f"Invalid type of criterion: `{type(criterion)}`.")
        return {
            "constraints": constraints,
            "limit_states": limit_states,
            "objectives": objectives,
            "variables": variables,
        }

    @staticmethod
    def __compare_input_w_processed_parameters_values(
        input: dict, processed: dict
    ) -> Tuple[Tuple[str, Union[float, str, bool], Union[float, str, bool]]]:
        """Compare input values of parameters before and after it's processed by server.

        Parameters
        ----------
        input: Dict[str: Union[float, str, bool]]
            Dictionary with parameter's names and values.
        processed: dict
            Server output.

        Returns
        -------
        Tuple[Tuple[str, Union[float, str, bool], Union[float, str, bool]]]
            Tuple of parameters with different values before and after processing by server.
                Tuple[0]: name
                Tuple[1]: input value
                Tuple[2]: processed value
        """
        differences = []
        for index, parameter_name in enumerate(processed["result_design"]["parameter_names"]):
            input_value = input.get(parameter_name)
            output_value = processed["result_design"]["parameter_values"][index]
            if input_value and input_value != output_value:
                differences.append((parameter_name, input_value, output_value))
        return tuple(differences)

    @staticmethod
    def __get_sorted_difference_of_sets(
        first: Iterable[str], second: Iterable[str]
    ) -> Tuple[str, ...]:
        """Get the sorted asymmetric difference of two string sets.

        This method executes the difference of two string sets: ``first - second``.

        Parameters
        ----------
        first: Iterable[str]
            Iterable of strings.
        second: Iterable[str]
            Iterable of string.

        Returns
        -------
        Tuple[str, ...]
            Tuple with the sorted difference.
        """
        diff = list(set(first) - set(second))
        diff.sort()
        return tuple(diff)


# endregion


# region Slots
class TcpSlotProxy(Slot):
    """Provides for creating and operating on slots."""

    def __init__(
        self,
        osl_server: TcpOslServer,
        node: TcpNodeProxy,
        name: str,
        type_: SlotType,
        type_hint: Optional[str] = None,
    ) -> None:
        """Create an ``TcpSlotProxy`` instance.

        Parameters
        ----------
        osl_server: TcpOslServer
            Object providing access to the optiSLang server.
        node : TcpNodeProxy
            Node to which the slot belongs.
        name : str
            Slot name.
        type_ : SlotType
            Slot type.
        type_hint : Optional[str], optional
            Data type of the slot, by default None.
        """
        self._osl_server = osl_server
        self.__node = node
        self.__name = name
        self.__type = type_
        self.__type_hint = type_hint

    def __str__(self):
        """Return formatted string."""
        return f"Slot type: {self.type.name} Name: {self.name}"

    @property
    def name(self) -> str:
        """Get slot name.

        Returns
        -------
        str
            Slot name.
        """
        return self.__name

    @name.setter
    def name(self, name: str) -> None:
        """Set slot name.

        .. note:: Setting slot names it only supported for dynamic slots.

        .. note:: Method is supported for Ansys optiSLang version >= 25.2 only.

        Parameters
        ----------
        name: str
            Slot name.

        Raises
        ------
        NotImplementedError
            Raised when unsupported optiSLang server is used.
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        if (
            self._osl_server.osl_version.major == 25 and self._osl_server.osl_version.minor >= 2
        ) or self._osl_server.osl_version.major > 25:
            self._osl_server.rename_slot(
                actor_uid=self.__node.uid,
                new_name=name,
                slot_name=self.__name,
            )
            self.__name = name
        else:
            raise NotImplementedError("Method is supported for Ansys optiSLang version >= 25.2.")

    @property
    def node(self) -> TcpNodeProxy:
        """Get node to which the slot belongs.

        Returns
        -------
        TcpNodeProxy
            Node to which the slot belongs.
        """
        return self.__node

    @property
    def type(self) -> SlotType:
        """Get slot type.

        Returns
        -------
        SlotType
            Type of current slot.
        """
        return self.__type

    @property
    def type_hint(self) -> Optional[str]:
        """Get type hint.

        Returns
        -------
        Optional[str]
            Data type of the current slot, ``None`` if not specified.
        """
        return self.__type_hint

    def get_connections(self) -> Tuple[Edge, ...]:
        """Get connections for the current slot.

        Returns
        -------
        Tuple[Edge]
            Tuple with connections of the current slot.
        """
        return self.node.get_connections(slot_type=self.type, slot_name=self.name)

    def get_type_hint(self) -> str:
        """Get slot's expected data type.

        Returns
        -------
        str
            Type hint.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        info = self.node._get_info()
        key = self.type.name.lower() + "_slots"
        slots_dict_list = info[key]
        for slot in slots_dict_list:
            if self.name == slot["name"]:
                self.__type_hint = slot["type"]
                if self.__type_hint:
                    return self.__type_hint
        raise NameError(f"Current slot: ``{self.name}`` wasn't found in node: ``{self.node.uid}``.")

    @staticmethod
    def create_slot(
        osl_server: TcpOslServer,
        node: TcpNodeProxy,
        name: str,
        type_: SlotType,
        type_hint: Optional[str] = None,
    ) -> TcpSlotProxy:
        """Create instance of new slot.

        Parameters
        ----------
        osl_server: TcpOslServer
            Object providing access to the optiSLang server.
        node : TcpNodeProxy
            Node to which slot belongs to.
        name : str
            Slot name.
        type_ : SlotType
            Slot type.
        type_hint : Optional[str], optional
            Slot's expected data type, by default ``None``.
            Available data types:

            * ``Undefined``, undefined type
            * ``Bool``
            * ``Integer``
            * ``Unsigned Integer``
            * ``Unsigned Integer Vector``
            * ``Real``
            * ``String``
            * ``String List``
            * ``Variant``
            * ``Path``
            * ``Parameter``
            * ``Parameter Set``
            * ``Parameter Manager``
            * ``Design``
            * ``Designpoint``
            * ``Design Container``
            * ``Bool Vector``
            * ``Criterion``
            * ``Criterion Sequence``
            * ``Designentry``
            * ``Runinfo Meta``
            * ``Runinfo``
            * ``Designpoints``

        Returns
        -------
        TcpSlotProxy
            Instance of TcpInputSlotProxy, TcpOutputSlotProxy, TcpInnerInputSlotProxy
            or TcpInnerOutputSlotProxy class.
        """
        if type_ == SlotType.INPUT:
            return TcpInputSlotProxy(
                osl_server=osl_server, node=node, name=name, type_=type_, type_hint=type_hint
            )
        elif type_ == SlotType.INNER_INPUT:
            return TcpInnerInputSlotProxy(
                osl_server=osl_server, node=node, name=name, type_=type_, type_hint=type_hint
            )
        elif type_ == SlotType.OUTPUT:
            return TcpOutputSlotProxy(
                osl_server=osl_server, node=node, name=name, type_=type_, type_hint=type_hint
            )
        elif type_ == SlotType.INNER_OUTPUT:
            return TcpInnerOutputSlotProxy(
                osl_server=osl_server, node=node, name=name, type_=type_, type_hint=type_hint
            )
        else:
            raise TypeError(
                f"Type of ``type_`` = ``SlotType`` was expected, but ``{type(type_)}`` was given."
            )

    @staticmethod
    def _create_connection_script(from_slot: TcpSlotProxy, to_slot: TcpSlotProxy) -> str:
        """Create optiSLang python script for slot connection.

        Parameters
        ----------
        from_slot : TcpSlotProxy
            Sending slot.
        to_slot : TcpSlotProxy
            Receiving slot.

        Returns
        -------
        str
            Python script for slot connection.
        """
        # TODO: Remove this, after server command `connect_nodes` is fixed (works for inner slots).
        if isinstance(from_slot.node, TcpRootSystemProxy):
            from_actor_script = "from_actor = project.get_root_system()\n"
        else:
            from_actor_script = TcpSlotProxy._create_find_actor_script(
                node=from_slot.node, name="from_actor"
            )

        if isinstance(to_slot.node, TcpRootSystemProxy):
            to_actor_script = "to_actor = project.get_root_system()"
        else:
            to_actor_script = TcpSlotProxy._create_find_actor_script(
                node=to_slot.node, name="to_actor"
            )

        final_script = (
            f"{from_actor_script}\n"
            f"{to_actor_script}\n"
            f"connect(from_actor=from_actor, from_slot='{from_slot.name}', "
            f"to_actor=to_actor, to_slot='{to_slot.name}')\n"
        )
        return final_script

    @staticmethod
    def _create_find_actor_script(node: TcpNodeProxy, name: str):
        """Create optiSLang python script to find actor.

        Parameters
        ----------
        node : TcpNodeProxy
            Node to be found.
        name : str
            Name used to store actor.

        Returns
        -------
        str
            Python script for finding given node.
        """
        actor_ancestors = node.get_ancestors()
        actor_ancestors_uids = [ancestor.uid for ancestor in actor_ancestors]
        actor_script = f"{name}_children_0 = get_children()\n"
        idx = 0
        if len(actor_ancestors) > 1:
            for idx in range(len(actor_ancestors_uids[0:-1])):
                actor_script += f"for child in {name}_children_{idx}:\n"
                actor_script += (
                    f"   if str(child.uuid)=='{actor_ancestors_uids[idx+1]}':\n"
                    f"      {name}_children_{idx+1} = child.get_children()\n"
                )
            idx += 1
        actor_script += f"for child in {name}_children_{idx}:\n"
        actor_script += f"   if str(child.uuid)=='{node.uid}': {name} = child\n"
        return actor_script


class TcpInputSlotProxy(TcpSlotProxy, InputSlot):
    """Provides for creating and operating on input slots."""

    def __init__(
        self,
        osl_server: TcpOslServer,
        node: TcpNodeProxy,
        name: str,
        type_: SlotType,
        type_hint: Optional[str] = None,
    ) -> None:
        """Create an ``TcpInputSlotProxy`` instance.

        Parameters
        ----------
        osl_server: TcpOslServer
            Object providing access to the optiSLang server.
        node : TcpNodeProxy
            Node to which the slot belongs.
        name : str
            Slot name.
        type_ : SlotType
            Slot type.
        type_hint : Optional[str], optional
            Data type of the slot, by default None.
        """
        super().__init__(
            osl_server=osl_server,
            node=node,
            name=name,
            type_=type_,
            type_hint=type_hint,
        )

    def connect_from(self, from_slot: TcpSlotProxy, skip_rename_slot: bool = False) -> Edge:
        """Connect slot from another slot.

        Parameters
        ----------
        from_slot: TcpSlotProxy
            Sending (output) slot.
        skip_rename_slot: bool, optional
            Skip automatic slot rename for untyped slots.
            Defaults to False.

            .. note:: Argument has effect for Ansys optiSLang version >= 25.2 only.

        Returns
        -------
        Edge
            Object determining connection.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        if not isinstance(from_slot, InnerOutputSlot) or self._osl_server.osl_version.major >= 24:
            self._osl_server.connect_nodes(
                from_actor_uid=from_slot.node.uid,
                from_slot=from_slot.name,
                to_actor_uid=self.node.uid,
                to_slot=self.name,
                skip_rename_slot=skip_rename_slot,
            )
        else:
            python_script = self._create_connection_script(from_slot=from_slot, to_slot=self)
            self._osl_server.run_python_script(script=python_script)
        return Edge(from_slot=from_slot, to_slot=self)

    def disconnect(self) -> None:
        """Remove all connections for the current slot.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        self._osl_server.disconnect_slot(
            uid=self.node.uid, slot_name=self.name, direction="sdInputs"
        )


class TcpOutputSlotProxy(TcpSlotProxy, OutputSlot):
    """Provides for creating and operating on output slots."""

    def __init__(
        self,
        osl_server: TcpOslServer,
        node: TcpNodeProxy,
        name: str,
        type_: SlotType,
        type_hint: Optional[str] = None,
    ) -> None:
        """Create an ``OutputSlotProxy`` instance.

        Parameters
        ----------
        osl_server: TcpOslServer
            Object providing access to the optiSLang server.
        node : TcpNodeProxy
            Node to which the slot belongs.
        name : str
            Slot name.
        type_ : SlotType
            Slot type.
        type_hint : Optional[str], optional
            Data type of the slot, by default None.
        """
        super().__init__(
            osl_server=osl_server,
            node=node,
            name=name,
            type_=type_,
            type_hint=type_hint,
        )

    def connect_to(self, to_slot: TcpSlotProxy, skip_rename_slot: bool = False) -> Edge:
        """Connect slot to another slot.

        Parameters
        ----------
        to_slot: TcpSlotProxy
            Receiving (input) slot
        skip_rename_slot: bool, optional
            Skip automatic slot rename for untyped slots.
            Defaults to False.

            .. note:: Argument has effect for Ansys optiSLang version >= 25.2 only.

        Returns
        -------
        Edge
            Object determining connection.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        if not isinstance(to_slot, InnerInputSlot) or self._osl_server.osl_version.major >= 24:
            self._osl_server.connect_nodes(
                from_actor_uid=self.node.uid,
                from_slot=self.name,
                to_actor_uid=to_slot.node.uid,
                to_slot=to_slot.name,
                skip_rename_slot=skip_rename_slot,
            )
        else:
            python_script = self._create_connection_script(from_slot=self, to_slot=to_slot)
            self._osl_server.run_python_script(script=python_script)
        return Edge(from_slot=self, to_slot=to_slot)

    def disconnect(self) -> None:
        """Remove all connections for the current slot.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        self._osl_server.disconnect_slot(
            uid=self.node.uid, slot_name=self.name, direction="sdOutputs"
        )


class TcpInnerInputSlotProxy(TcpSlotProxy, InnerInputSlot):
    """Provides for creating and operating on inner input slots."""

    def __init__(
        self,
        osl_server: TcpOslServer,
        node: TcpNodeProxy,
        name: str,
        type_: SlotType,
        type_hint: Optional[str] = None,
    ) -> None:
        """Create a ``InnerInputSlotProxy`` instance.

        Parameters
        ----------
        osl_server: TcpOslServer
            Object providing access to the optiSLang server.
        node : TcpNodeProxy
            Node to which the slot belongs.
        name : str
            Slot name.
        type_ : SlotType
            Slot type.
        type_hint : Optional[str], optional
            Data type of the slot, by default None.
        """
        super().__init__(
            osl_server=osl_server,
            node=node,
            name=name,
            type_=type_,
            type_hint=type_hint,
        )

    def connect_from(self, from_slot: TcpSlotProxy, skip_rename_slot: bool = False) -> Edge:
        """Connect slot from another slot.

        Parameters
        ----------
        from_slot: TcpSlotProxy
            Sending (output) slot
        skip_rename_slot: bool, optional
            Skip automatic slot rename for untyped slots.
            Defaults to False.

            .. note:: Argument has effect for Ansys optiSLang version >= 25.2 only.

        Returns
        -------
        Edge
            Object determining connection.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        if self._osl_server.osl_version.major >= 24:
            self._osl_server.connect_nodes(
                from_actor_uid=from_slot.node.uid,
                from_slot=from_slot.name,
                to_actor_uid=self.node.uid,
                to_slot=self.name,
                skip_rename_slot=skip_rename_slot,
            )
        else:
            python_script = self._create_connection_script(from_slot=from_slot, to_slot=self)
            self._osl_server.run_python_script(script=python_script)
        return Edge(from_slot=from_slot, to_slot=self)


class TcpInnerOutputSlotProxy(TcpSlotProxy, InnerOutputSlot):
    """Provides for creating and operating on inner output slots."""

    def __init__(
        self,
        osl_server: TcpOslServer,
        node: TcpNodeProxy,
        name: str,
        type_: SlotType,
        type_hint: Optional[str] = None,
    ) -> None:
        """Create a ``InnerOutputSlotProxy`` instance.

        Parameters
        ----------
        osl_server: TcpOslServer
            Object providing access to the optiSLang server.
        node : TcpNodeProxy
            Node to which the slot belongs.
        name : str
            Slot name.
        type_ : SlotType
            Slot type.
        type_hint : Optional[str], optional
            Data type of the slot, by default None.
        """
        super().__init__(
            osl_server=osl_server,
            node=node,
            name=name,
            type_=type_,
            type_hint=type_hint,
        )

    def connect_to(self, to_slot: TcpSlotProxy, skip_rename_slot: bool = False) -> Edge:
        """Connect slot to another slot.

        Parameters
        ----------
        to_slot: TcpSlotProxy
            Receiving (input) slot
        skip_rename_slot: bool, optional
            Skip automatic slot rename for untyped slots.
            Defaults to False.

            .. note:: Argument has effect for Ansys optiSLang version >= 25.2 only.

        Returns
        -------
        Edge
            Object determining connection.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        if self._osl_server.osl_version.major >= 24:
            self._osl_server.connect_nodes(
                from_actor_uid=self.node.uid,
                from_slot=self.name,
                to_actor_uid=to_slot.node.uid,
                to_slot=to_slot.name,
                skip_rename_slot=skip_rename_slot,
            )
        else:
            python_script = self._create_connection_script(from_slot=self, to_slot=to_slot)
            self._osl_server.run_python_script(script=python_script)
        return Edge(from_slot=self, to_slot=to_slot)


# endregion


# region Factory methods
_NODE_CLASS_TYPE_TO_TCP_MAPPING: Dict[str, Type[TcpNodeProxy]] = {
    NodeClassType.NODE.name: TcpNodeProxy,
    NodeClassType.INTEGRATION_NODE.name: TcpIntegrationNodeProxy,
    NodeClassType.SYSTEM.name: TcpSystemProxy,
    NodeClassType.PARAMETRIC_SYSTEM.name: TcpParametricSystemProxy,
    NodeClassType.PROXY_SOLVER.name: TcpProxySolverNodeProxy,
    NodeClassType.ROOT_SYSTEM.name: TcpRootSystemProxy,
}


def create_edge_from_dict(
    osl_server: TcpOslServer,
    project_tree: dict,
    connection: dict,
    node: Optional[TcpNodeProxy] = None,
    logger: Optional[Any] = None,
) -> Edge:
    """Create edge from project tree and connection dictionary.

    Parameters
    ----------
    osl_server: TcpOslServer
        Object providing access to the optiSLang server.
    project_tree : dict
        Dictionary with project structure.
    connection : dict
        Dictionary describing connection.
    node: Optional[TcpNodeProxy], optional
        Node from which slot is created, by default ``None``.
    logger: Optional[Any], optional
        Object for logging. If ``None``, standard logging object is used. Defaults to ``None``.

    Returns
    -------
    Edge
        Instance of the Edge class.
    """
    rec_slot_name = connection["receiving_slot"]
    rec_slot_type = connection.get("receiving_slot_is_inner", None)
    rec_slot_type = (
        SlotType.INNER_INPUT
        if connection.get("receiving_slot_is_inner", None)
        else SlotType.INPUT if connection.get("receiving_slot_is_inner") is False else None
    )
    if rec_slot_type is None:
        info = osl_server.get_actor_info(
            connection["receiving_uuid"],
            include_log_messages=False,
            include_integrations_registered_locations=False,
        )
        if True in [item["name"] == rec_slot_name for item in info["input_slots"]]:
            rec_slot_type = SlotType.INPUT
        elif True in [item["name"] == rec_slot_name for item in info.get("inner_input_slots", [])]:
            rec_slot_type = SlotType.INNER_INPUT
        else:
            raise ValueError(f"Slot ``{rec_slot_name}`` doesn't exist for given node.")
    rec_slot = create_slot_from_project_tree(
        osl_server=osl_server,
        project_tree=project_tree,
        uid=connection["receiving_uuid"],
        slot_name=rec_slot_name,
        slot_type=rec_slot_type,
        node=node,
        logger=logger,
    )

    sen_slot_name = connection["sending_slot"]
    sen_slot_type = connection.get("sending_slot_is_inner", None)
    sen_slot_type = (
        SlotType.INNER_OUTPUT
        if connection.get("sending_slot_is_inner", None)
        else SlotType.OUTPUT if connection.get("sending_slot_is_inner") is False else None
    )
    if sen_slot_type is None:
        info = osl_server.get_actor_info(
            connection["sending_uuid"],
            include_log_messages=False,
            include_integrations_registered_locations=False,
        )
        if True in [item["name"] == sen_slot_name for item in info["output_slots"]]:
            sen_slot_type = SlotType.OUTPUT
        elif True in [item["name"] == sen_slot_name for item in info.get("inner_output_slots", [])]:
            sen_slot_type = SlotType.INNER_OUTPUT
        else:
            raise ValueError(f"Slot ``{rec_slot_name}`` doesn't exist for given node.")
    sen_slot = create_slot_from_project_tree(
        osl_server=osl_server,
        project_tree=project_tree,
        uid=connection["sending_uuid"],
        slot_name=sen_slot_name,
        slot_type=sen_slot_type,
        node=node,
        logger=logger,
    )

    return Edge(from_slot=sen_slot, to_slot=rec_slot)


def create_nodes_from_properties_dicts(
    osl_server: TcpOslServer, properties_dicts_list: Iterable[dict], logger=None
) -> Tuple[TcpNodeProxy, ...]:
    """Create nodes from a dictionary of properties.

    Parameters
    ----------
    osl_server: TcpOslServer
        Object providing access to the optiSLang server.
    properties_dicts_list : Iterable[dict]
        Dictionary of node properties.
    logger: Any, optional
        Object for logging. If ``None``, standard logging object is used. Defaults to ``None``.

    Returns
    -------
    Tuple[TcpNodeProxy, ...]
        Tuple of nodes.

    Raises
    ------
    TypeError
        Raised when an unknown type of component is found.
    """
    nodes_list = []
    for node in properties_dicts_list:
        type_ = get_node_type_from_str(node_id=node["type"])
        if type_.osl_class_type is not None:
            class_to_be_constructed = _NODE_CLASS_TYPE_TO_TCP_MAPPING[type_.osl_class_type.name]
        else:
            class_to_be_constructed = _NODE_CLASS_TYPE_TO_TCP_MAPPING[
                _get_node_class_type(node_dict=node, type_=type_).name
            ]
        nodes_list.append(
            _create_node_instance(
                class_to_be_constructed=class_to_be_constructed,
                node=node,
                type_=type_,
                osl_server=osl_server,
                logger=logger,
            )
        )
    return tuple(nodes_list)


def create_slot_from_project_tree(
    osl_server: TcpOslServer,
    project_tree: dict,
    uid: str,
    slot_name: str,
    slot_type: SlotType,
    node: Optional[TcpNodeProxy] = None,
    logger: Optional[Any] = None,
) -> TcpSlotProxy:
    """Create slot from project tree.

    Parameters
    ----------
    osl_server: TcpOslServer
        Object providing access to the optiSLang server.
    project_tree : dict
        Project tree
    uid: str
        Uid of node to be created.
    slot_name: str
        Slot name.
    slot_type: SlotType
        Slot type.
    node: Optional[TcpNodeProxy], optional
        Node from which slot is created, by default ``None``.
    logger: Optional[Any], optional
        Object for logging. If ``None``, standard logging object is used. Defaults to ``None``.

    Returns
    -------
    TcpSlotProxy
        Instance of the ``TcpSlotProxy`` class.
    """
    if node is None or uid != node.uid:
        if uid == project_tree["uid"]:
            node = TcpRootSystemProxy(uid=uid, osl_server=osl_server, logger=logger)
        else:
            node_dict = TcpNodeProxy._find_node_with_uid(
                uid=uid,
                tree=project_tree,
                properties_dicts_list=[],
                current_depth=1,
                max_search_depth=-1,
            )
            node = create_nodes_from_properties_dicts(
                osl_server=osl_server,
                properties_dicts_list=node_dict,
                logger=logger,
            )[0]
    return TcpSlotProxy.create_slot(
        osl_server=osl_server, node=node, name=slot_name, type_=slot_type
    )


def _get_node_class_type(node_dict: dict, type_: NodeType) -> NodeClassType:
    """Get node class type from the given inputs.

    Parameters
    ----------
    node_dict : dict
        Dictionary with info
    type_ : NodeType
        Type of the node.

    Returns
    -------
    NodeClassType
        Type of the resulting node class for the given inputs.
    """
    # TODO: test
    if node_dict["kind"] == "actor":
        if (
            type_.subtype == AddinType.PYTHON_BASED_INTEGRATION_PLUGIN
            or type_.subtype == AddinType.INTEGRATION_PLUGIN
        ):
            return NodeClassType.INTEGRATION_NODE
        return NodeClassType.NODE

    if node_dict["kind"] == "system":
        if node_dict["is_parametric_system"]:
            return NodeClassType.PARAMETRIC_SYSTEM
        return NodeClassType.SYSTEM

    if node_dict["kind"] == "root_system":
        return NodeClassType.ROOT_SYSTEM

    raise TypeError(
        f'Unknown kind of component: "{node_dict["kind"]}", '
        '"node", "system" or "root_system" were expected.'
    )


def _create_node_instance(
    class_to_be_constructed: Type[TcpNodeProxy],
    node: dict,
    type_: NodeType,
    osl_server: TcpOslServer,
    logger=None,
) -> TcpNodeProxy:
    if type_.id == "RunnableSystem":
        return TcpRootSystemProxy(
            uid=node["uid"],
            osl_server=osl_server,
            logger=logger,
        )
    else:
        return class_to_be_constructed(
            uid=node["uid"],
            osl_server=osl_server,
            type_=type_,
            logger=logger,
        )


# endregion

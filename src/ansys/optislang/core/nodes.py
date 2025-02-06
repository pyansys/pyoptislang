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

"""Contains abstract base classes ``Node``, ``System``, ``ParametricSystem`` and ``RootSystem``."""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, Flag
from typing import TYPE_CHECKING, Any, Optional, Tuple, Union

from deprecated.sphinx import deprecated

from ansys.optislang.core.io import File, FileOutputFormat, RegisteredFile
from ansys.optislang.core.utils import enum_from_str

if TYPE_CHECKING:
    from pathlib import Path

    from ansys.optislang.core.managers import CriteriaManager, ParameterManager, ResponseManager
    from ansys.optislang.core.node_types import NodeType
    from ansys.optislang.core.project_parametric import Design

PROJECT_COMMANDS_RETURN_STATES = {
    "start": "PROCESSING",
    "restart": "PROCESSING",
    "stop": "STOPPED",
    "stop_gently": "GENTLY_STOPPED",
    "reset": "FINISHED",
}


ACTOR_COMMANDS_RETURN_STATES = {
    "start": "Running",
    "restart": "Running",
    "stop": "Aborted",
    "stop_gently": "Gently stopped",
    "reset": "Finished",
}


class DesignFlow(Enum):
    """Provides design flow options."""

    NONE = 0
    RECEIVE = 1
    SEND = 2
    RECEIVE_SEND = 3

    @classmethod
    def from_str(cls, string: str) -> DesignFlow:
        """Convert string to an instance of the ``DesignFlow`` class.

        Parameters
        ----------
        string: str
            String to be converted.

        Returns
        -------
        DesignFlow
            Instance of the ``DesignFlow`` class.

        Raises
        ------
        TypeError
            Raised when an invalid type of ``string`` is given.
        ValueError
            Raised when an invalid value of ``string`` is given.
        """
        return enum_from_str(string=string, enum_class=cls, replace=(" ", "_"))


class ExecutionOption(Flag):
    """Provides actor execution options."""

    INACTIVE = 0
    ACTIVE = 1
    END_POINT = 2
    STARTING_POINT = 4
    SAVE_POINT = 8
    RECYCLE_RESULTS = 16


class NodeClassType(Enum):
    """Provides types of pyOSL classes."""

    NODE = 0
    SYSTEM = 1
    PARAMETRIC_SYSTEM = 2
    ROOT_SYSTEM = 3
    INTEGRATION_NODE = 4
    PROXY_SOLVER = 5

    @classmethod
    def from_str(cls, string: str) -> NodeClassType:
        """Convert string to an instance of the ``NodeClassType`` class.

        Parameters
        ----------
        string: str
            String to be converted.

        Returns
        -------
        NodeClassType
            Instance of the ``NodeClassType`` class.

        Raises
        ------
        TypeError
            Raised when an invalid type of ``string`` is given.
        ValueError
            Raised when an invalid value of ``string`` is given.
        """
        return enum_from_str(string=string, enum_class=cls, replace=(" ", "_"))


class SamplingType(Enum):
    """Provides sampling type options."""

    CENTERPOINT = 0
    FULLFACTORIAL = 1
    AXIAL = 2
    STARPOINTS = 3
    KOSHAL = 4
    CENTRALCOMPOSITE = 5
    MIXEDTERMS = 6
    LATINHYPER = 7
    LATINHYPERDETEMINISTIC = 8
    OPTIMIZEDLATINHYPER = 9
    ORTHOLATINHYPERDETEMINISTIC = 10
    SOBOLSEQUENCES = 11
    PLAINMONTECARLO = 12
    DOPTIMAL = 13
    DOPTIMALLINEAR = 14
    DOPTIMALQUADRATIC = 15
    DOPTIMALQUADRATICNOMIXED = 16
    KOSHALLINEAR = 17
    KOSHALQUADRATIC = 18
    FEKETE = 19
    BOXBEHNKEN = 20
    FULLCOMBINATORIAL = 21
    ADVANCEDLATINHYPER = 22

    @classmethod
    def from_str(cls, string: str) -> SamplingType:
        """Convert string to an instance of the ``SamplingType`` class.

        Parameters
        ----------
        string: str
            String to be converted.

        Returns
        -------
        SamplingType
            Instance of the ``SamplingType`` class.

        Raises
        ------
        TypeError
            Raised when an invalid type of ``string`` is given.
        """
        return enum_from_str(string=string, enum_class=cls, replace=(" ", "_"))


class SlotType(Enum):
    """Provides slot type options."""

    INPUT = 0
    OUTPUT = 1
    INNER_INPUT = 2
    INNER_OUTPUT = 3

    @classmethod
    def from_str(cls, string: str) -> SlotType:
        """Convert string to an instance of the ``SlotType`` class.

        Parameters
        ----------
        string: str
            String to be converted.

        Returns
        -------
        SlotType
            Instance of the ``SlotType`` class.

        Raises
        ------
        TypeError
            Raised when an invalid type of ``string`` is given.
        """
        return enum_from_str(string=string, enum_class=cls, replace=(" ", "_"))

    @staticmethod
    def to_dir_str(type_: SlotType) -> str:
        """Convert string to an instance of the ``SlotType`` class.

        Parameters
        ----------
        string: str
            String to be converted.

        Returns
        -------
        SlotType
            Instance of the ``SlotType`` class.

        Raises
        ------
        TypeError
            Raised when an invalid type of ``string`` is given.
        ValueError
            Raised when an invalid value of ``string`` is given.
        """
        if not isinstance(type_, SlotType):
            raise TypeError(f"Unsupported type of type_: ``{type(type_)}``.")
        if type_ in [SlotType.INPUT, SlotType.INNER_INPUT]:
            return "receiving"
        elif type_ in [SlotType.OUTPUT, SlotType.INNER_OUTPUT]:
            return "sending"
        else:
            raise ValueError(f"Unsupported value of type_: ``{type_}``.")


class Node(ABC):
    """Base class for classes which provide for creating and operating on nodes."""

    @abstractmethod
    def __init__(self):  # pragma: no cover
        """``Node`` class is an abstract base class and cannot be instantiated."""
        pass

    @property
    @abstractmethod
    def uid(self) -> str:  # pragma: no cover
        """Unique ID of the node.

        Returns
        -------
        str
            Unique ID of the node.
        """
        pass

    @property
    @abstractmethod
    def type(self) -> NodeType:  # pragma: no cover
        """Type of the node.

        Returns
        -------
        NodeType
            Instance of the ``NodeType`` class.
        """
        pass

    @abstractmethod
    def control(
        self,
        command: str,
        hid: Optional[str] = None,
        wait_for_completion: bool = True,
        timeout: Union[float, int] = 100,
    ) -> Optional[bool]:  # pragma: no cover
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
        pass

    @abstractmethod
    def delete(self) -> None:  # pragma: no cover
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
        pass

    @abstractmethod
    def exists(self) -> bool:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_ancestors(self) -> Tuple[Node, ...]:  # pragma: no cover
        """Get tuple of ordered ancestors starting from root system at position 0.

        Returns
        -------
        Tuple[Node, ...]
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
        pass

    @abstractmethod
    def get_execution_options(self) -> ExecutionOption:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_connections(
        self, slot_type: Optional[SlotType] = None, slot_name: Optional[str] = None
    ) -> Tuple[Edge, ...]:  # pragma: no cover
        """Get connections of a given direction and slot.

        Parameters
        ----------
        slot_type: Optional[SlotType], optional
            Slot type, by default ``None``.
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
        pass

    @abstractmethod
    def get_input_slots(self, name: Optional[str] = None) -> Tuple[InputSlot, ...]:
        """Get current node's input slots.

        Parameters
        ----------
        name : Optional[str], optional
            Slot name, by default ``None``.

        Returns
        -------
        Tuple[InputSlot, ...]
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
        pass

    @abstractmethod
    def get_name(self) -> str:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_output_slots(self, name: Optional[str] = None) -> Tuple[OutputSlot, ...]:
        """Get current node's output slots.

        Parameters
        ----------
        name : Optional[str], optional
            Slot name, by default ``None``.

        Returns
        -------
        Tuple[OutputSlot, ...]
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
        pass

    @abstractmethod
    def get_parent(self) -> Node:  # pragma: no cover
        """Get the instance of the parent node.

        Returns
        -------
        Node
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
        pass

    @abstractmethod
    def get_parent_name(self) -> str:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_property(self, name: str) -> Any:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_registered_files(self) -> Tuple[RegisteredFile, ...]:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_result_files(self) -> Tuple[RegisteredFile, ...]:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_states_ids(self) -> Tuple[str, ...]:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_status(self) -> str:  # pragma: no cover
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
        pass

    @abstractmethod
    def set_execution_options(self, value: ExecutionOption) -> None:  # pragma: no cover
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
        pass

    @abstractmethod
    def set_property(self, name: str, value: Any) -> None:  # pragma: no cover
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
        pass

    @abstractmethod
    def create_input_slot(
        self, slot_name: str, type_hint: Optional[str] = None  # pragma: no cover
    ) -> None:
        """Create dynamic input slot.

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
        pass

    @abstractmethod
    def create_output_slot(
        self, slot_name: str, type_hint: Optional[str] = None
    ) -> None:  # pragma: no cover
        """Create dynamic output slot.

        Parameters
        ----------
        slot_name : str
            Name of the slot to be created.d
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
        pass

    @abstractmethod
    def set_name(self, new_name: str) -> None:  # pragma: no cover
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
        pass


class IntegrationNode(Node):
    """Base class for classes which provide for creating and operating on an integration node."""

    @abstractmethod
    def __init__(self):  # pragma: no cover
        """``IntegrationNode`` class is an abstract base class and cannot be instantiated."""
        pass

    @abstractmethod
    def get_available_input_locations(self) -> Tuple:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_available_output_locations(self) -> Tuple:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_internal_variables(
        self, include_reference_values: bool = True
    ) -> Tuple:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_registered_input_slots(
        self, include_reference_values: bool = True
    ) -> Tuple:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_registered_output_slots(
        self, include_reference_values: bool = True
    ) -> Tuple:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_registered_parameters(
        self, include_reference_values: bool = True
    ) -> Tuple:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_registered_responses(
        self, include_reference_values: bool = True
    ) -> Tuple:  # pragma: no cover
        """Get registered responses.

        Parameters
        ----------
        include_reference_values: bool
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
        pass

    @abstractmethod
    def load(self, args: Optional[dict] = None) -> None:  # pragma: no cover
        """Explicitly load the node.

        Some optiSLang nodes support/need an explicit load prior to being able to register
        or to make registering more convenient.

        Parameters
        ----------
        args: Optional[dict], optional
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
        pass

    @abstractmethod
    def register_location_as_input_slot(
        self,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:  # pragma: no cover
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
        pass

    @abstractmethod
    def register_location_as_internal_variable(
        self,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:  # pragma: no cover
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
        pass

    @abstractmethod
    def register_location_as_output_slot(
        self,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:  # pragma: no cover
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
        pass

    @abstractmethod
    def register_location_as_parameter(
        self,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:  # pragma: no cover
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
        pass

    @abstractmethod
    def register_location_as_response(
        self,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:  # pragma: no cover
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
        pass

    @abstractmethod
    def register_locations_as_parameter(self) -> None:  # pragma: no cover
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
        pass

    @abstractmethod
    def register_locations_as_response(self) -> None:  # pragma: no cover
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
        pass

    @abstractmethod
    def re_register_locations_as_parameter(self) -> None:  # pragma: no cover
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
        pass

    @abstractmethod
    def re_register_locations_as_response(self) -> None:  # pragma: no cover
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
        pass


class ProxySolverNode(IntegrationNode):
    """Base class for classes which provide for creating and operating on an proxy solver node."""

    @abstractmethod
    def __init__(self):  # pragma: no cover
        """``ProxySolverNode`` class is an abstract base class and cannot be instantiated."""
        pass

    @abstractmethod
    def get_designs(self) -> Any:  # pragma: no cover
        """Get pending designs from parent node.

        Returns
        -------
        Any
            Pending designs.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        pass

    @abstractmethod
    def set_designs(self, designs: Any) -> None:  # pragma: no cover
        """Set calculated designs.

        Parameters
        ----------
        Any
            Calculated designs.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        pass


class System(Node):
    """Base class for classes which provide for creating and operating on a system."""

    @abstractmethod
    def __init__(self):  # pragma: no cover
        """``System`` class is an abstract base class and cannot be instantiated."""
        pass

    @abstractmethod
    def create_node(
        self,
        type_: NodeType,
        name: Optional[str] = None,
        design_flow: DesignFlow = DesignFlow.NONE,
    ) -> Node:  # pragma: no cover
        """Create a new node in current system in active project.

        Parameters
        ----------
        type_ : NodeType
            Type of created node.
        name : Optional[str], optional
            Name of created node, by default None.
        design_flow : Optional[DesignFlow], optional
            Design flow, by default None.

        Returns
        -------
        Node
            Instance of the created node.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        TypeError
            Raised when unsupported type of ``type_`` is given.
        ValueError
            Raised when unsupported value of ``type_`` is given.
        """
        pass

    @abstractmethod
    def delete_children_nodes(self) -> None:  # pragma: no cover
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
        pass

    @abstractmethod
    def find_node_by_uid(
        self, uid: str, search_depth: int = 1
    ) -> Optional[Node]:  # pragma: no cover
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
        Optional[Node]
            ``Node`` with the specified unique ID. If this ID isn't located in any
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
        pass

    @abstractmethod
    def find_nodes_by_name(
        self, name: str, search_depth: int = 1
    ) -> Tuple[Node, ...]:  # pragma: no cover
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
        Tuple[Node, ...]
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
        pass

    @abstractmethod
    def get_nodes(self) -> Tuple[Node, ...]:  # pragma: no cover
        """Get the direct children nodes.

        Returns
        -------
        Tuple[Node, ...]
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
        pass


class ParametricSystem(System):
    """Base class for classes which provide for creating and operating on a parametric system."""

    @abstractmethod
    def __init__(self):  # pragma: no cover
        """``ParametricSystem`` class is an abstract base class and cannot be instantiated."""
        pass

    @property
    @abstractmethod
    def criteria_manager(self) -> CriteriaManager:  # pragma: no cover
        """Criteria manager of the current system.

        Returns
        -------
        CriteriaManager
            Instance of the ``CriteriaManager`` class.
        """
        pass

    @property
    @abstractmethod
    def parameter_manager(self) -> ParameterManager:  # pragma: no cover
        """Parameter manager of the current system.

        Returns
        -------
        ParameterManager
            Instance of the ``ParameterManager`` class.
        """
        pass

    @property
    @abstractmethod
    def response_manager(self) -> ResponseManager:  # pragma: no cover
        """Response manager of the current system.

        Returns
        -------
        ResponseManager
            Instance of the ``ResponseManager`` class.
        """
        pass

    @abstractmethod
    def get_inner_input_slots(self, name: Optional[str] = None) -> Tuple[InnerInputSlot, ...]:
        """Get current node's inner input slots.

        Parameters
        ----------
        name : Optional[str], optional
            Slot name, by default ``None``.

        Returns
        -------
        Tuple[InnerInputSlot, ...]
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
        pass

    @abstractmethod
    def get_inner_output_slots(self, name: Optional[str] = None) -> Tuple[InnerOutputSlot, ...]:
        """Get current node's inner output slots.

        Parameters
        ----------
        name : Optional[str], optional
            Slot name, by default ``None``.

        Returns
        -------
        Tuple[InnerOutpuSlot, ...]
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
        pass

    @abstractmethod
    def get_omdb_files(self) -> Tuple[File]:  # pragma: no cover
        """Get paths to omdb files.

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
        """
        pass

    def save_designs_as_json(
        self, hid: str, file_path: Union[Path, str]
    ) -> File:  # pragma: no cover
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
        pass

    def save_designs_as_csv(
        self, hid: str, file_path: Union[Path, str]
    ) -> File:  # pragma: no cover
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
        pass

    @abstractmethod
    @deprecated(
        version="0.9.0",
        reason="Use :py:meth:`ParametricSystem.save_designs_as_json` or "
        ":py:meth:`ParametricSystem.save_designs_as_csv` instead.",
    )
    def save_designs_as(
        self,
        hid: str,
        file_name: str,
        format: FileOutputFormat = FileOutputFormat.JSON,
        dir: Optional[Union[Path, str]] = None,
    ) -> File:  # pragma: no cover
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
        pass


class RootSystem(ParametricSystem):
    """Base class for classes which provide for creating and operating on a project system."""

    @abstractmethod
    def __init__(self):  # pragma: no cover
        """``Rootsystem`` class is an abstract base class and cannot be instantiated."""
        pass

    @abstractmethod
    def control(
        self,
        command: str,
        hid: Optional[str] = None,
        wait_for_completion: bool = True,
        timeout: Union[float, int] = 100,
    ) -> Optional[bool]:  # pragma: no cover
        """Control the node state.

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
        pass

    @abstractmethod
    def evaluate_design(self, design: Design) -> Design:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_reference_design(self) -> Design:  # pragma: no cover
        """Get the design with reference values of the parameters.

        Returns
        -------
        Design
            Instance of the ``Design`` class with defined parameters and reference values.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        pass

    @abstractmethod
    def get_missing_parameters_names(self, design: Design) -> Tuple[str, ...]:  # pragma: no cover
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
        pass

    @abstractmethod
    def get_undefined_parameters_names(self, design: Design) -> Tuple[str, ...]:  # pragma: no cover
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
        pass


class Slot(ABC):
    """Provides for creating and operating on slots."""

    @abstractmethod
    def __init__(self):  # pragma: no cover
        """``Slot`` class is an abstract base class and cannot be instantiated."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:  # pragma: no cover
        """Get slot name.

        Returns
        -------
        str
            Slot name.
        """
        pass

    @name.setter
    def name(self, name: str) -> None:  # pragma: no cover
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

    @property
    @abstractmethod
    def node(self) -> Node:  # pragma: no cover
        """Get node to which the slot belongs.

        Returns
        -------
        Node
            Node to which the slot belongs.
        """
        pass

    @property
    @abstractmethod
    def type(self) -> SlotType:  # pragma: no cover
        """Get slot type.

        Returns
        -------
        SlotType
            Type of current slot.
        """
        pass

    @property
    @abstractmethod
    def type_hint(self) -> Optional[str]:  # pragma: no cover
        """Get type hint.

        Returns
        -------
        Optional[str]
            Data type of the current slot, ``None`` if not specified.
        """
        pass

    @abstractmethod
    def get_connections(self) -> Tuple[Edge, ...]:  # pragma: no cover
        """Get connections for the current slot.

        Returns
        -------
        Tuple[Edge]
            Tuple with connections of the current slot.
        """
        pass

    @abstractmethod
    def get_type_hint(self) -> str:  # pragma: no cover
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
        pass


class InputSlot(Slot):
    """Provides for creating and operating on input slots."""

    @abstractmethod
    def __init__(self):  # pragma: no cover
        """``InputSlot`` class is an abstract base class and cannot be instantiated."""
        pass

    @abstractmethod
    def connect_from(
        self, from_slot: Slot, skip_rename_slot: bool = False
    ) -> Edge:  # pragma: no cover
        """Connect slot from another slot.

        Parameters
        ----------
        from_slot: Slot
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
        pass

    @abstractmethod
    def disconnect(self) -> None:  # pragma: no cover
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
        pass


class OutputSlot(Slot):
    """Provides for creating and operating on output slots."""

    @abstractmethod
    def __init__(self):  # pragma: no cover
        """``OutputSlot`` class is an abstract base class and cannot be instantiated."""
        pass

    @abstractmethod
    def connect_to(self, to_slot: Slot, skip_rename_slot: bool = False) -> Edge:  # pragma: no cover
        """Connect slot to another slot.

        Parameters
        ----------
        to_slot: Slot
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
        pass

    @abstractmethod
    def disconnect(self) -> None:  # pragma: no cover
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
        pass


class InnerInputSlot(Slot):
    """Provides for creating and operating on inner input slots."""

    @abstractmethod
    def __init__(self):  # pragma: no cover
        """``InnerInputSlot`` class is an abstract base class and cannot be instantiated."""
        pass

    @abstractmethod
    def connect_from(
        self, from_slot: Slot, skip_rename_slot: bool = False
    ) -> Edge:  # pragma: no cover
        """Connect slot from another slot.

        Parameters
        ----------
        from_slot: Slot
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
        pass


class InnerOutputSlot(Slot):
    """Provides for creating and operating on inner output slots."""

    @abstractmethod
    def __init__(self):  # pragma: no cover
        """``InnerOutputSlot`` class is an abstract base class and cannot be instantiated."""
        pass

    @abstractmethod
    def connect_to(self, to_slot: Slot, skip_rename_slot: bool = False) -> Edge:  # pragma: no cover
        """Connect slot to another slot.

        Parameters
        ----------
        to_slot: Slot
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
        pass


class Edge:
    """Provides for creating and operating on connections."""

    def __init__(
        self,
        from_slot: Slot,
        to_slot: Slot,
    ) -> None:
        """Create an ``Edge`` instance.

        Parameters
        ----------
        from_slot: Slot
            Output slot.
        to_slot: Slot
            Input slot.
        """
        if from_slot.type not in [SlotType.INNER_OUTPUT, SlotType.OUTPUT]:
            raise ValueError(
                f"Invalid value of ``from_slot.type``: ``{from_slot.type}``."
                f"``{SlotType.OUTPUT}<or>{SlotType.INNER_OUTPUT}`` was expected."
            )
        self.__from_slot = from_slot
        if to_slot.type not in [SlotType.INNER_INPUT, SlotType.INPUT]:
            raise ValueError(
                f"Invalid value of ``to_slot.type``: ``{to_slot.type}``."
                f"``{SlotType.INPUT}<or>{SlotType.INNER_INPUT}`` was expected."
            )
        self.__to_slot = to_slot

    def __str__(self):
        """Return formatted string."""
        return (
            "From_slot:\n"
            f"   type: {self.from_slot.type.name}\n"
            f"   name: {self.from_slot.name}\n"
            "To_slot:\n"
            f"   type: {self.to_slot.type.name}\n"
            f"   name: {self.to_slot.name}\n"
        )

    @property
    def from_slot(self) -> Slot:
        """Get output slot."""
        return self.__from_slot

    @property
    def to_slot(self) -> Slot:
        """Get input slot."""
        return self.__to_slot

    def exists(self) -> bool:
        """Get info whether connection exists in active project.

        Returns
        -------
        bool
            Whether current connection exists in active project.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with the server.
        OslCommandError
            Raised when a command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        connections = self.from_slot.get_connections()
        for connection in connections:
            if (
                connection.to_slot.node.uid == self.to_slot.node.uid
                and connection.to_slot.name == self.to_slot.name
            ):
                return True
        return False

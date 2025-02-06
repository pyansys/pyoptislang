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

"""Contains classes for plain TCP/IP communication with server."""
from __future__ import annotations

import atexit
from datetime import datetime
import json
import logging
import os
from pathlib import Path
from queue import Queue
import re
import signal
import socket
import struct
import sys
import threading
import time
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
import uuid

from deprecated.sphinx import deprecated

from ansys.optislang.core import utils
from ansys.optislang.core.encoding import force_bytes, force_text
from ansys.optislang.core.errors import (
    ConnectionEstablishedError,
    ConnectionNotEstablishedError,
    EmptyResponseError,
    OslCommandError,
    OslCommunicationError,
    OslDisposedError,
    ResponseFormatError,
)
from ansys.optislang.core.osl_process import OslServerProcess, ServerNotification
from ansys.optislang.core.osl_server import OslServer, OslVersion
from ansys.optislang.core.tcp import server_commands as commands
from ansys.optislang.core.tcp import server_queries as queries


def _get_current_timeout(initial_timeout: Optional[float], start_time: float) -> Optional[float]:
    """Get actual timeout value.

    The function will raise a timeout exception if the timeout has expired.

    Parameters
    ----------
    initial_timeout : Optional[float]
        Initial timeout value. For non-zero value, the new timeout value is computed.
        If the timeout period value has elapsed, the timeout exception is raised.
        For zero value, the non-blocking mode is assumed and zero value is returned.
        For ``None``, the blocking mode is assumed and ``None`` is returned.
    start_time : float
        The time when the initial time out starts to count down. It is defined in seconds
        since the epoch as a floating point number.

    Returns
    -------
    Optional[float]
        Remaining timeout.

    Raises
    ------
    TimeoutError
        Raised when the timeout expires.
    """
    if initial_timeout != 0 and initial_timeout is not None:
        elapsed_time = time.time() - start_time
        remaining_timeout = initial_timeout - elapsed_time
        if remaining_timeout <= 0:
            raise TimeoutError("Timeout has expired.")
        return remaining_timeout
    else:
        return initial_timeout


class FunctionsAttributeRegister:
    """Class which stores attributes specific to individual functions."""

    def __init__(
        self, default_value: Any, validator: Optional[Callable[[Any], bool]] = None
    ) -> None:
        """Create a ``FunctionsAttributeRegister`` instance.

        Parameters
        ----------
        default_value : Any
            Default value of function's attribute.
        validator : Optional[Callable[[Any], bool]]
            Function to validate registered values and default value.
        """
        self.__default_value = default_value
        self.__register: Dict[str, Any] = {}
        self.__validator = validator

    @property
    def default_value(self) -> Any:
        """Default value of the attribute."""
        return self.__default_value

    @default_value.setter
    def default_value(self, value: Any) -> None:
        """Set default value of attribute.

        Parameters
        ----------
        default_value : Any
            Default value of attribute.

        Raises
        ------
        ValueError
            Raised when invalid value is passed.
        """
        self.__validate_value(value=value)
        self.__default_value = value

    def get_value(self, function: Union[Callable, str]) -> Any:
        """Get value of given function's attribute.

        Parameters
        ----------
        function : Union[Callable, str]
            Function for which the attribute value is requested.

        Returns
        -------
        Any
            Attribute value registered for the given function or default value if not registered.
        """
        if callable(function):
            function = function.__name__
        if self.is_registered(function=function):
            return self.__register.get(function)
        else:
            return self.default_value

    def is_registered(self, function: Union[Callable, str]) -> bool:
        """Get info whether attribute is registered for given function.

        Parameters
        ----------
        function : Union[Callable, str]
            Function for which the info about attribute registration is requested.

        Returns
        -------
        bool
            Info whether attribute is registered.
        """
        if callable(function):
            function = function.__name__
        return function in self.__register.keys()

    def register(self, function: Union[Callable, str], value: Any) -> None:
        """Register given value for given function.

        Parameters
        ----------
        function : Union[Callable, str]
            Function for which the attribute value is to be registered.
        value : Any
            Attribute value to be registered for the given function.

        Raises
        ------
        ValueError
            Raised when invalid value is passed.
        """
        if callable(function):
            function = function.__name__
        self.__validate_value(value=value)
        self.__register[function] = value

    def unregister(self, function: Union[Callable, str]) -> None:
        """Remove given function from the register.

        Parameters
        ----------
        function : Union[Callable, str]
            Function to be removed from the register.
        """
        if callable(function):
            function = function = function.__name__
        self.__register.pop(function, None)

    def unregister_all(self) -> None:
        """Remove all functions from the register."""
        self.__register.clear()

    def __validate_value(self, value: Any) -> None:
        """Validate given value.

        Parameters
        ----------
        value: Any
            Value to be validated using instance's validator.

        Raises
        ------
        ValueError
            Raised when invalid value is passed.
        """
        if self.__validator is not None and not self.__validator(value):
            raise ValueError(f"Invalid value `{value}` was passed.")


class TcpClient:
    r"""Client of the plain TCP/IP communication.

    Parameters
    ----------
    socket: Optional[socket.SocketType], optional
        Client socket. Defaults to ``None``.
    logger: Any, optional
        Object for logging. If ``None``, standard logging object is used. Defaults to ``None``.

    Examples
    --------
    Connect to the plain TCP/IP server with IP address of localhost and port 49690. Send
    the following message:
    '{ "What": "SYSTEMS_STATUS_INFO" }'

    >>> from ansys.optislang.core.tcp import TcpClient
    >>> client = TcpClient()
    >>> client.connect('127.0.0.1', 49690)
    >>> client.send_msg('{ "What": "SYSTEMS_STATUS_INFO" }')
    """

    _BUFFER_SIZE = pow(2, 16)
    # Response size in bytes. Value is assumed to be binary 64Bit unsigned integer.
    _RESPONSE_SIZE_BYTES = 8

    def __init__(self, socket: Optional[socket.SocketType] = None, logger=None) -> None:
        """Initialize a new instance of the ``TcpClient`` class."""
        self.__socket = socket

        if logger is None:
            self._logger = logging.getLogger(__name__)
        else:
            self._logger = logger

    @property
    def remote_address(self) -> Union[Tuple[str, int], None]:
        """Get the remote address of the connection.

        Returns
        -------
        Tuple(str, int), None
            Remote host address which consists of IP address and port number, if connection is
            established; ``None`` otherwise.
        """
        if self.__socket is None:
            return None

        return self.__socket.getpeername()

    @property
    def local_address(self) -> Union[Tuple[str, int], None]:
        """Get the local address of the connection.

        Returns
        -------
        Tuple(str, int), None
            Local host address which consists of IP address and port number, if connection is
            established; ``None`` otherwise.
        """
        if self.__socket is None:
            return None

        return self.__socket.getsockname()

    @property
    def is_connected(self) -> bool:
        """Determine whether the connection has been established.

        Returns
        -------
        bool
            True if the connection has been established; False otherwise.
        """
        return self.__socket is not None

    def connect(self, host: str, port: int, timeout: Optional[float] = 2) -> None:
        """Connect to the plain TCP/IP server.

        Parameters
        ----------
        host : str
            A string representation of an IPv4/v6 address or domain name.
        port : int
            A numeric port number.
        timeout : Optional[float], optional
            Timeout in seconds to establish a connection. If a non-zero value is given,
            the function will raise a timeout exception if the timeout period value has elapsed
            before the operation has completed. If zero is given, the non-blocking mode is used.
            If ``None`` is given, the blocking mode is used. Defaults to 2 s.

        Raises
        ------
        ConnectionEstablishedError
            Raised when the connection is already established.
        ConnectionRefusedError
            Raised when the connection cannot be established.
        """
        if self.__socket is not None:
            raise ConnectionEstablishedError("Connection is already established.")

        start_time = time.time()

        for af, socktype, proto, canonname, sa in socket.getaddrinfo(
            host, port, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE
        ):
            try:
                self.__socket = socket.socket(af, socktype, proto)
            except OSError:
                self.__socket = None
                continue
            self.__socket.settimeout(_get_current_timeout(timeout, start_time))
            try:
                self.__socket.connect(sa)
            except OSError:
                self.__socket.close()
                self.__socket = None
                continue
            break

        if self.__socket is None:
            raise ConnectionRefusedError(
                f"Connection could not be established to host {host} and port {port}."
            )

        self._logger.debug("Connection has been established to host %s and port %d.", host, port)

    def disconnect(self) -> None:
        """Disconnect from the server."""
        if self.__socket is not None:
            self.__socket.close()
            self.__socket = None

    def send_msg(self, msg: str, timeout: Optional[float] = 5) -> None:
        """Send message to the server.

        Parameters
        ----------
        msg : str
            Message to send.
        timeout : Optional[float], optional
            Timeout in seconds to send a message. If a non-zero value is given,
            the function will raise a timeout exception if the timeout period value has elapsed
            before the operation has completed. If zero is given, the non-blocking mode is used.
            If ``None`` is given, the blocking mode is used. Defaults to 5 s.

        Raises
        ------
        ConnectionNotEstablishedError
            Raised when the connection has not been established before function call.
        TimeoutError
            Raised when the timeout period value has elapsed before the operation has completed.
        OSError
            Raised when an error occurs while sending data.
        """
        if self.__socket is None:
            raise ConnectionNotEstablishedError(
                "Cannot send message. Connection is not established."
            )

        self._logger.debug("Sending message to %s. Message: %s", self.__socket.getpeername(), msg)
        data = force_bytes(msg)
        data_len = len(data)

        header = struct.pack("!QQ", data_len, data_len)

        self.__socket.settimeout(timeout)
        self.__socket.sendall(header + data)

    def send_file(self, file_path: Union[str, Path], timeout: Optional[float] = 5) -> None:
        """Send content of the file to the server.

        Parameters
        ----------
        file_path : Union[str, pathlib.Path]
            Path to the file whose content is to be sent to the server.
        timeout : Optional[float], optional
            Timeout in seconds to send the buffer of the read part of the file. If a non-zero value
            is given, the function will raise a timeout exception if the timeout period value
            has elapsed before the operation has completed. If zero is given, the non-blocking mode
            is used. If ``None`` is given, the blocking mode is used. Defaults to 5 s.
        Raises
        ------
        ConnectionNotEstablishedError
            Raised when the connection has not been established before function call.
        FileNotFoundError
            Raised when the specified file does exist.
        TimeoutError
            Raised when the timeout period value has elapsed before the operation has completed.
        OSError
            Raised when an error occurs while sending data.
        """
        if self.__socket is None:
            raise ConnectionNotEstablishedError("Cannot send file. Connection is not established.")
        if not os.path.isfile(file_path):
            raise FileNotFoundError(
                "Cannot send file. The file does not exist. File path: %s", file_path
            )

        self._logger.debug(
            "Sending file to %s. File path: %s", self.__socket.getpeername(), file_path
        )
        file_size = os.path.getsize(file_path)

        header = struct.pack("!QQ", file_size, file_size)

        with open(file_path, "rb") as file:
            self.__socket.settimeout(timeout)
            self.__socket.sendall(header)
            load = file.read(self._BUFFER_SIZE)
            while load:
                self.__socket.send(load)
                load = file.read(self._BUFFER_SIZE)

    def receive_msg(self, timeout: Optional[float] = 5) -> str:
        """Receive message from the server.

        Parameters
        ----------
        timeout : Optional[float], optional
            Timeout in seconds to receive a message. The function will raise a timeout exception
            if the timeout period value has elapsed before the operation has completed. If ``None``
            is given, the blocking mode is used. Defaults to 5 s.

        Returns
        -------
        str
            Received message from the server.

        Raises
        ------
        ConnectionNotEstablishedError
            Raised when the connection has not been established before function call.
        EmptyResponseError
            Raised when the empty message is received.
        ResponseFormatError
            Raised when the format of the received message is not valid.
        TimeoutError
            Raised when the timeout period value has elapsed before the operation has completed.
        ValueError
            Raised if the timeout value is a number not greater than zero.
        """
        if self.__socket is None:
            raise ConnectionNotEstablishedError(
                "Cannot receive message. Connection is not established."
            )

        if isinstance(timeout, float) and timeout <= 0:
            raise ValueError("Timeout value must be greater than zero or None.")

        start_time = time.time()

        msg_len = self._recv_response_length(timeout)
        if msg_len == 0:
            raise EmptyResponseError("The empty message has been received.")

        remain_timeout = _get_current_timeout(timeout, start_time)
        data = self._receive_bytes(msg_len, remain_timeout)
        if len(data) != msg_len:
            raise ResponseFormatError("Received data does not match declared data size.")

        return force_text(data)

    def receive_file(self, file_path: Union[str, Path], timeout: Optional[float] = 5) -> None:
        """Receive file from the server.

        Parameters
        ----------
        file_path : Union[str, pathlib.Path]
            Path where the received file is to be saved.
        timeout : Optional[float], optional
            Timeout in seconds to receive a buffer of the file part. The function will raise
            a timeout exception if the timeout period value has elapsed before the operation
            has completed. If ``None`` is given, the blocking mode is used. Defaults to 5 s.

        Raises
        ------
        ConnectionNotEstablishedError
            Raised when the connection has not been established before function call.
        EmptyResponseError
            Raised when the empty message is received.
        ResponseFormatError
            Raised when the format of the received data is not valid.
        TimeoutError
            Raised when the timeout period value has elapsed before the operation has completed.
        ValueError
            Raised if the timeout value is a number not greater than zero.
        OSError
            Raised when the file cannot be opened.
        """
        if self.__socket is None:
            raise ConnectionNotEstablishedError(
                "Cannot receive file. Connection is not established."
            )

        start_time = time.time()

        file_len = self._recv_response_length(timeout)
        if file_len == 0:
            raise EmptyResponseError("The empty file has been received.")

        remain_timeout = _get_current_timeout(timeout, start_time)
        self._fetch_file(file_len, file_path, remain_timeout)
        if os.path.getsize(file_path) != file_len:
            raise ResponseFormatError("Received data does not match declared data size.")

    def _recv_response_length(self, timeout: Optional[float]) -> int:
        """Receive length of the response.

        Parameters
        ----------
        timeout : Optional[float]
            Timeout in seconds to receive the response length. The function will raise a timeout
            exception if the timeout period value has elapsed before the operation has completed.
            If ``None`` is given, the blocking mode is used.

        Returns
        -------
        int
            Length of the response to be received.

        Raises
        ------
        TimeoutError
            Raised when the timeout period value has elapsed before the operation has completed.
        ResponseFormatError
            Raised when the response length specification is invalid.
        ValueError
            Raised if the timeout value is a number not greater than zero.
        """
        if isinstance(timeout, float) and timeout <= 0:
            raise ValueError("Timeout value must be greater than zero or None.")

        if self.__socket is None:
            raise ConnectionNotEstablishedError("Socket not set.")

        self.__socket.settimeout(timeout)

        response_len = -1
        bytes_to_receive = self._RESPONSE_SIZE_BYTES

        # read from socket until response size (twice) has been received
        response_len_1 = struct.unpack("!Q", self._receive_bytes(bytes_to_receive, timeout))[0]
        response_len_2 = struct.unpack("!Q", self._receive_bytes(bytes_to_receive, timeout))[0]

        if response_len_1 != response_len_2:
            raise ResponseFormatError(
                "Server response format unrecognized. Response sizes do not match."
            )

        response_len = response_len_1

        return response_len

    def _receive_bytes(self, count: int, timeout: Optional[float]) -> bytes:
        """Receive specified number of bytes from the server.

        Parameters
        ----------
        count : int
            Number of bytes to be received from the server.
        timeout : Optional[float]
            Timeout in seconds to receive specified number of bytes. The function will raise
            a timeout exception if the timeout period value has elapsed before the operation
            has completed. If ``None`` is given, the blocking mode is used.

        Returns
        -------
        bytes
            Received bytes.

        Raises
        ------
        TimeoutError
            Raised when the timeout period value has elapsed before the operation has completed.
        ValueError
            Raised when the number of bytes is not greater than zero.
            -or-
            Raised if the timeout value is a number not greater than zero.
        """
        if count <= 0:
            raise ValueError("Number of bytes must be greater than zero.")
        if isinstance(timeout, float) and timeout <= 0:
            raise ValueError("Timeout value must be greater than zero or None.")

        if self.__socket is None:
            raise ConnectionNotEstablishedError("Socket not set.")

        start_time = time.time()

        received = b""
        received_len = 0
        while received_len < count:
            remain = count - received_len
            if remain > self._BUFFER_SIZE:
                buff = self._BUFFER_SIZE
            else:
                buff = remain

            self.__socket.settimeout(_get_current_timeout(timeout, start_time))
            chunk = self.__socket.recv(buff)
            if not chunk:
                break
            received += chunk
            received_len += len(chunk)
        return received

    def _fetch_file(
        self, file_len: int, file_path: Union[str, Path], timeout: Optional[float]
    ) -> None:
        """Write received bytes from the server to the file.

        Parameters
        ----------
        file_len : int
            Number of bytes to be written.
        file_path : Union[str, pathlib.Path]
            Path to the file to which the received data is to be written.
        timeout : Optional[float]
            Timeout in seconds to receive bytes from the server and write them to the file.
            The function will raise a timeout exception if the timeout period value has
            elapsed before the operation has completed. If ``None`` is given, the blocking mode
            is used.

        Raises
        ------
        TimeoutError
            Raised when the timeout period value has elapsed before the operation has completed.
        OSError
            Raised when the file cannot be opened.
        ValueError
            Raised if the timeout value is a number not greater than zero.
        """
        if isinstance(timeout, float) and timeout <= 0:
            raise ValueError("Timeout value must be greater than zero or None.")

        if self.__socket is None:
            raise ConnectionNotEstablishedError("Socket not set.")

        start_time = time.time()

        with open(file_path, "wb") as file:
            data_len = 0
            while data_len < file_len:
                remain = file_len - data_len
                if remain > self._BUFFER_SIZE:
                    buff = self._BUFFER_SIZE
                else:
                    buff = remain

                self.__socket.settimeout(_get_current_timeout(timeout, start_time))
                chunk = self.__socket.recv(buff)
                if not chunk:
                    break
                file.write(chunk)
                data_len += len(chunk)


class TcpOslListener:
    """Listener of optiSLang server.

    Parameters
    ----------
        port_range: Tuple
            Range of ports for listener.
        timeout: float
            Timeout in seconds to receive a message. Timeout exception will be raised
            if the timeout period value has elapsed before the operation has completed. If ``None``
            is given, the blocking mode is used.
        name: str
            Name of listener.
        host: Optional[str], optional
            Local IPv6 address, by default ``None``.
        uid: Optional[str], optional
            Unique ID of listener, should be used only if listener is used for optiSLangs port
            when started locally, by default ``None``.
        logger: Optional[Any], optional
            Preferably OslLogger should be given. If not given, default logging.Logger is used.
        notifications: Optional[Iterable[ServerNotification]], optional
            Notifications to subscribe to.
            Either ["ALL"] or Sequence picked from below options:
            Server: [ "SERVER_UP", "SERVER_DOWN" ] (always be sent by default).
            Logging: [ "LOG_INFO", "LOG_WARNING", "LOG_ERROR", "LOG_DEBUG" ].
            Project: [ "EXECUTION_STARTED", "PROCESSING_STARTED", "EXECUTION_FINISHED",
                "NOTHING_PROCESSED", "CHECK_FAILED", "EXEC_FAILED" ].
            Nodes: [ "ACTOR_STATE_CHANGED", "ACTOR_ACTIVE_CHANGED", "ACTOR_NAME_CHANGED",
                "ACTOR_CONTENTS_CHANGED", "ACTOR_DATA_CHANGED" ].
            Defaults to ``None``.

    Raises
    ------
    ValueError
        Raised when port_range != 2 or first number is higher.
    TypeError
        Raised when port_range not type Tuple[int, int]
    TimeoutError
        Raised when the timeout float value expires.

    Examples
    --------
    Create listener

    >>> from ansys.optislang.core.tcp_osl_server import TcpOslListener
    >>> general_listener = TcpOslListener(
    >>>     port_range = (49152, 65535),
    >>>     timeout = 30,
    >>>     name = 'GeneralListener',
    >>>     host = '127.0.0.1',
    >>>     uid = str(uuid.uuid4()),
    >>>     logger = logging.getLogger(__name__),
    >>> )
    """

    def __init__(
        self,
        port_range: Tuple,
        timeout: float,
        name: str,
        host: Optional[str] = None,
        uid: Optional[str] = None,
        logger: Optional[Any] = None,
        notifications: Optional[List[ServerNotification]] = None,
    ):
        """Initialize a new instance of the ``TcpOslListener`` class."""
        self.__uid = uid
        self.__name = name
        self.__timeout = timeout
        self.__listener_socket: Optional[socket.socket] = None
        self.__thread: Optional[threading.Thread] = None
        self.__callbacks: List[Tuple[Callable, Any]] = []
        self.__run_listening_thread = False
        self.__refresh_listener_registration = False
        self.__notifications = notifications

        if logger is None:
            self._logger = logging.getLogger(__name__)
        else:
            self._logger = logger

        if len(port_range) != 2:
            raise ValueError(f"Port ranges length must be 2 but: len = {len(port_range)}")
        if isinstance(port_range, (int, int)):
            raise TypeError(
                "Port range not type Tuple[int, int] but:"
                f"[{type(port_range[0])}, {port_range[1]}]."
            )
        if port_range[0] > port_range[1]:
            raise ValueError("First number is higher.")

        self.__init_listener_socket(host=host if host is not None else "", port_range=port_range)

    def is_initialized(self) -> bool:
        """Return True if listener was initialized."""
        return self.__listener_socket is not None

    def dispose(self) -> None:
        """Delete listeners socket if exists."""
        if self.__listener_socket is not None:
            self.__listener_socket.close()

    @property
    def uid(self) -> Optional[str]:
        """Instance unique identifier."""
        return self.__uid

    @uid.setter
    def uid(self, uid) -> None:
        self.__uid = uid

    @property
    def name(self) -> str:
        """Instance name used for naming self.__thread."""
        return self.__name

    @property
    def timeout(self) -> Optional[float]:
        """Timeout in seconds to receive a message."""
        return self.__timeout

    @timeout.setter
    def timeout(self, timeout) -> None:
        self.__timeout = timeout

    @property
    def host_addresses(self) -> List[str]:
        """Local IP addresses associated with self.__listener_socket."""
        addresses = utils.get_localhost_addresses()
        # Explicitly add localhost  to workaround potential networking issues
        addresses.append("127.0.0.1")
        return addresses

    @property
    def port(self) -> int:
        """Port number associated with self.__listener_socket."""
        return self.__listener_socket.getsockname()[1]

    @property
    def refresh_listener_registration(self) -> bool:
        """Get refresh listeners registration status."""
        return self.__refresh_listener_registration

    @refresh_listener_registration.setter
    def refresh_listener_registration(self, refresh: bool) -> None:
        """Set refresh listeners registration status.

        Parameters
        ----------
        refresh: bool
            If True, listeners registration will be automatically renewed.
        """
        self.__refresh_listener_registration = refresh

    @property
    def notifications(self) -> Optional[List[ServerNotification]]:
        """Notifications to subscribe to."""
        return self.__notifications

    @notifications.setter
    def notifications(self, notifications: Optional[List[ServerNotification]]) -> None:
        self.__notifications = notifications

    def add_callback(self, callback: Callable, args) -> None:
        """Add callback (method) that will be called after push notification is received.

        Parameters
        ----------
        callback: Callable
            Method or any callable that will be called when listener receives message.
        args:
            Arguments to the callback.
        """
        self.__callbacks.append((callback, args))

    def clear_callbacks(self) -> None:
        """Remove all callbacks."""
        self.__callbacks.clear()

    def start_listening(self, timeout=None) -> None:
        """Start new thread listening optiSLang server port.

        Parameters
        ----------
        timeout: float, optional
            Listener socket timeout.
        """
        self.__thread = threading.Thread(
            target=self.__listen,
            name=f"PyOptiSLang.TcpOslListener.{self.name}",
            args=(timeout,),
            daemon=True,
        )
        self.__run_listening_thread = True
        self.__thread.start()

    def stop_listening(self) -> None:
        """Stop listening optiSLang server port."""
        self.__run_listening_thread = False
        self.__thread = None

    def __init_listener_socket(self, host: str, port_range: Tuple[int, int]) -> None:
        """Initialize listener.

        Parameters
        ----------
        host: str
            A string representation of an IPv4/v6 address or domain name.
        port_range : Tuple[int, int]
            Defines the port range for port listener. Defaults to ``None``.
        """
        self.__listener_socket = None
        for port in range(port_range[0], port_range[1] + 1):
            try:
                self.__listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.__listener_socket.bind((host, port))
                self.__listener_socket.listen(5)
                self._logger.debug("Listening on port: %d", port)
                break
            except IOError as ex:
                if self.__listener_socket is not None:
                    self.__listener_socket.close()
                    self.__listener_socket = None

    def __listen(self, timeout=None) -> None:
        """Listen to the optiSLang server.

        Parameters
        ----------
        timeout: float, optional
            Listener socket timeout.
        """
        if self.__listener_socket is None:
            raise ConnectionNotEstablishedError("Socket not set.")

        start_time = time.time()
        if timeout is None:
            timeout = self.__timeout

        while self.__run_listening_thread:
            client = None
            try:
                self.__listener_socket.settimeout(_get_current_timeout(timeout, start_time))
                clientsocket, address = self.__listener_socket.accept()
                self._logger.debug("Connection from %s has been established.", address)

                client = TcpClient(clientsocket)
                message = client.receive_msg(timeout)
                self._logger.debug("Received message from client: %s", message)

                response = json.loads(message)
                client.send_msg("")
                self.__execute_callbacks(response)

            except (TimeoutError, socket.timeout):
                self._logger.warning(f"Listener {self.uid} listening timed out.")
                response = {"type": "TimeoutError"}
                self.__execute_callbacks(response)
                break
            except Exception as ex:
                self._logger.warning(ex)
            finally:
                if client is not None:
                    client.disconnect()

    def __execute_callbacks(self, response) -> None:
        """Execute all callback."""
        for callback, args in self.__callbacks:
            callback(self, response, *args)

    def is_listening(self) -> bool:
        """Return True if listener is listening."""
        return self.is_initialized() and self.__thread is not None and self.__thread.is_alive()

    def join(self) -> None:
        """Wait until self.__thread is finished."""
        if not self.is_listening():
            raise RuntimeError("Listener is not listening.")
        if self.__thread is not None:
            self.__thread.join()

    def cleanup_notifications(self, timeout: float = 1) -> None:
        """Cleanup previously unprocessed push notifications.

        Parameters
        ----------
        timeout: float, optional
            Listener socket timeout. Default value ``0.2``.
        """
        while True:
            client = None
            try:
                self.__listener_socket.settimeout(timeout)
                clientsocket, address = self.__listener_socket.accept()
                client = TcpClient(clientsocket)
                message = client.receive_msg(timeout)
                data_dict = json.loads(message)
                self._logger.debug(f"CLEANUP: {data_dict}")
                client.send_msg("")
            except socket.timeout:
                self._logger.debug("No notifications were cleaned up.")
                break
            except Exception as ex:
                self._logger.warning(ex)
            finally:
                if client is not None:
                    client.disconnect()


class TcpOslServer(OslServer):
    """Class which provides access to optiSLang server using plain TCP/IP communication protocol.

    TcpOslServer class provides explicit methods for accessing specific optiSLang API endpoints.
    Additionally, the generic
    :py:mod:`send_command <ansys.optislang.core.tcp_osl_server.TcpOslServer.send_command>` method
    can be used in conjunction with the convenience functions from the
    :ref:`ansys.optislang.core.tcp.tcp_server_queries <ref_osl_server_api_queries>` and
    :ref:`ansys.optislang.core.tcp.tcp_server_commands <ref_osl_server_api_commands>` modules.

    For remote connection, it is assumed that the optiSLang server process is already running
    on remote (or local) host. In that case, the host and port must be specified and other
    parameters are ignored.

    Parameters
    ----------
    host : Optional[str], optional
        A string representation of an IPv4/v6 address or domain name of running optiSLang server.
        Defaults to ``None``.
    port : Optional[int], optional
        A numeric port number of running optiSLang server. Defaults to ``None``.
    executable : Optional[Union[str, pathlib.Path]], optional
        Path to the optiSLang executable file which supposed to be executed on localhost.
        It is ignored when the host and port parameters are specified. Defaults to ``None``.
    project_path : Optional[Union[str, pathlib.Path]], optional
        Path to the optiSLang project file which is supposed to be used by new local optiSLang
        server. It is ignored when the host and port parameters are specified.
        - If the project file exists, it is opened.
        - If the project file does not exist, a new project is created on the specified path.
        - If the path is None, a new project is created in the temporary directory.
        Defaults to ``None``.
    batch : bool, optional
        Determines whether to start optiSLang server in batch mode. Defaults to ``True``.

        ..note:: Cannot be used in combination with service mode.

    service: bool, optional
        Determines whether to start optiSLang server in service mode. If ``True``,
        ``batch`` argument is set to ``False``. Defaults to ``False``.

        ..note:: Cannot be used in combination with batch mode.

    port_range : Optional[Tuple[int, int]], optional
        Defines the port range for optiSLang server. Defaults to ``None``.
    no_run : Optional[bool], optional
        Determines whether not to run the specified project when started in batch mode.
        Defaults to ``None``.

        .. note:: Only supported in batch mode.

    no_save : bool, optional
        Determines whether not to save the specified project after all other actions are completed.
        It is ignored when the host and port parameters are specified. Defaults to ``False``.

        .. note:: Only supported in batch mode.

    force : bool, optional
        Determines whether to force opening/processing specified project when started in batch mode
        even if issues occur. Defaults to ``True``.

        .. note:: Only supported in batch mode.

    reset : bool, optional
        Determines whether to reset specified project after load. Defaults to ``False``.

        .. note:: Only supported in batch mode.

    auto_relocate : bool, optional
        Determines whether to automatically relocate missing file paths. Defaults to ``False``.

        .. note:: Only supported in batch mode.

    listener_id : Optional[str], optional
        Specific unique ID for the TCP listener. Defaults to ``None``.
    multi_listener : Optional[Iterable[Tuple[str, int, Optional[str]]]], optional
        Multiple remote listeners (plain TCP/IP based) to be registered at optiSLang server.
        Each listener is a combination of host, port and (optionally) listener ID.
        Defaults to ``None``.
    listeners_refresh_interval : int, optional
        Refresh interval for TCP listeners in seconds. Defaults to 10 s.
    listeners_default_timeout : int, optional
        Default timeout for TCP listeners in milliseconds. Defaults to 60000 ms.
    ini_timeout : float, optional
        Time in seconds to listen to the optiSLang server port. If the port is not listened
        for specified time, the optiSLang server is not started and RuntimeError is raised.
        It is ignored when the host and port parameters are specified. Defaults to 20 s.
    password : Optional[str], optional
        The server password. Use when communication with the server requires the request
        to contain a password entry. Defaults to ``None``.
    logger : Optional[Any], optional
        Object for logging. If ``None``, standard logging object is used. Defaults to ``None``.
    shutdown_on_finished: bool, optional
        Shut down when execution is finished and there are not any listeners registered.
        It is ignored when the host and port parameters are specified. Defaults to ``True``.

        .. note:: Only supported in batch mode.

    env_vars : Optional[Mapping[str, str]], optional
        Additional environmental variables (key and value) for the optiSLang server process.
        Defaults to ``None``.
    import_project_properties_file : Optional[Union[str, pathlib.Path]], optional
        Optional path to a project properties file to import. Defaults to ``None``.
    export_project_properties_file : Optional[Union[str, pathlib.Path]], optional
        Optional path to a project properties file to export. Defaults to ``None``.

        .. note:: Only supported in batch mode.

    import_placeholders_file : Optional[Union[str, pathlib.Path]], optional
        Optional path to a placeholders file to import. Defaults to ``None``.
    export_placeholders_file : Optional[Union[str, pathlib.Path]], optional
        Optional path to a placeholders file to export. Defaults to ``None``.

        .. note:: Only supported in batch mode.

    output_file : Optional[Union[str, pathlib.Path]], optional
        Optional path to an output file for writing project run results to. Defaults to ``None``.

        .. note:: Only supported in batch mode.

    dump_project_state : Optional[Union[str, pathlib.Path]], optional
        Optional path to a project state dump file to export. If a relative path is provided,
        it is considered to be relative to the project working directory. Defaults to ``None``.

        .. note:: Only supported in batch mode.

    opx_project_definition_file : Optional[Union[str, pathlib.Path]], optional
        Optional path to an OPX project definition file. Defaults to ``None``.

        .. note:: Only supported in batch mode.

    additional_args : Optional[Iterable[str]], optional
        Additional command line arguments used for execution of the optiSLang server process.
        Defaults to ``None``.

    Raises
    ------
    RuntimeError
        Port listener cannot be started.
        -or-
        optiSLang server port is not listened for specified timeout value.

    Examples
    --------
    Start local optiSLang server, get optiSLang version and shutdown the server.

    >>> from ansys.optislang.core.tcp_osl_server import TcpOslServer
    >>> osl_server = TcpOslServer()
    >>> osl_version = osl_server.osl_version_string
    >>> print(osl_version)
    >>> osl_server.dispose()

    Connect to the remote optiSLang server, get optiSLang version and shutdown the server.

    >>> from ansys.optislang.core.tcp_osl_server import TcpOslServer
    >>> host = "192.168.101.1"  # IP address of the remote host
    >>> port = 49200            # Port of the remote optiSLang server
    >>> osl_server = TcpOslServer(host, port)
    >>> osl_version = osl_server.osl_version_string
    >>> print(osl_version)
    >>> osl_server.dispose()
    """

    _LOCALHOST = "127.0.0.1"
    _PRIVATE_PORTS_RANGE = (49152, 65535)
    _SHUTDOWN_WAIT = 5  # wait for local server to shutdown in second
    _STOPPED_STATES = ["IDLE", "FINISHED", "STOPPED", "ABORTED"]
    _STOP_REQUESTS_PRIORITIES = {
        "STOP": 20,
        "STOP_GENTLY": 10,
    }
    _STOP_REQUESTED_STATES_PRIORITIES = {
        "ABORT_REQUESTED": 30,
        "STOP_REQUESTED": 20,
        "GENTLE_STOP_REQUESTED": 10,
    }
    _DEFAULT_PROJECT_FILE = "project.opf"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        executable: Optional[Union[str, Path]] = None,
        project_path: Optional[Union[str, Path]] = None,
        batch: bool = True,
        service: bool = False,
        port_range: Optional[Tuple[int, int]] = None,
        no_run: Optional[bool] = None,
        no_save: bool = False,
        force: bool = True,
        reset: bool = False,
        auto_relocate: bool = False,
        listener_id: Optional[str] = None,
        multi_listener: Optional[Iterable[Tuple[str, int, Optional[str]]]] = None,
        listeners_refresh_interval: int = 10,
        listeners_default_timeout: int = 60000,
        ini_timeout: float = 60,
        password: Optional[str] = None,
        logger: Optional[Any] = None,
        shutdown_on_finished: bool = True,
        env_vars: Optional[Mapping[str, str]] = None,
        import_project_properties_file: Optional[Union[str, Path]] = None,
        export_project_properties_file: Optional[Union[str, Path]] = None,
        import_placeholders_file: Optional[Union[str, Path]] = None,
        export_placeholders_file: Optional[Union[str, Path]] = None,
        output_file: Optional[Union[str, Path]] = None,
        dump_project_state: Optional[Union[str, Path]] = None,
        opx_project_definition_file: Optional[Union[str, Path]] = None,
        additional_args: Optional[Iterable[str]] = None,
    ) -> None:
        """Initialize a new instance of the ``TcpOslServer`` class."""
        self.__host = host
        self.__port = port
        self.__max_request_attempts_register = self.__get_default_max_request_attempts_register()
        self.__timeouts_register = self.__get_default_timeouts_register()

        self._logger = logging.getLogger(__name__) if logger is None else logger

        self.__executable = Path(executable) if executable is not None else None
        self.__project_path = Path(project_path) if project_path is not None else None
        self.__batch = batch
        self.__service = service
        self.__port_range = port_range
        self.__no_run = no_run
        self.__no_save = no_save
        self.__force = force
        self.__reset = reset
        self.__auto_relocate = auto_relocate
        self.__password = password
        self.__osl_process: Optional[OslServerProcess] = None
        self.__listeners: Dict[str, TcpOslListener] = {}
        self.__listeners_registration_thread: Optional[threading.Thread] = None
        self.__refresh_listeners_stopped = threading.Event()
        self.__listeners_refresh_interval = listeners_refresh_interval
        self.__listeners_default_timeout = listeners_default_timeout
        self.__disposed = False
        self.__env_vars = env_vars
        self.__listener_id = listener_id
        self.__multi_listener = multi_listener
        self.__import_project_properties_file = import_project_properties_file
        self.__export_project_properties_file = export_project_properties_file
        self.__import_placeholders_file = import_placeholders_file
        self.__export_placeholders_file = export_placeholders_file
        self.__output_file = output_file
        self.__dump_project_state = dump_project_state
        self.__opx_project_definition_file = opx_project_definition_file
        self.__additional_args = additional_args

        executed_in_main_thread = True

        if sys.version_info[0] >= 3 and sys.version_info[1] >= 4:
            executed_in_main_thread = threading.current_thread() is threading.main_thread()
        else:
            executed_in_main_thread = isinstance(threading.current_thread(), threading._MainThread)

        if executed_in_main_thread:
            signal.signal(signal.SIGINT, self.__signal_handler)

        atexit.register(self.dispose)

        if self.__host is None or self.__port is None:
            self.__host = self._LOCALHOST
            self.__shutdown_on_finished = shutdown_on_finished
            self._start_local(ini_timeout, shutdown_on_finished)
        else:
            self.__shutdown_on_finished = None
            listener = self.__create_listener(
                timeout=None,
                name="Main",
                uid=self.__listener_id,
                notifications=[
                    ServerNotification.SERVER_UP,
                    ServerNotification.SERVER_DOWN,
                ],
            )
            listener.uid = self.__register_listener(
                host_addresses=listener.host_addresses,
                port=listener.port,
                timeout=self.__listeners_default_timeout,
                notifications=listener.notifications,
            )
            listener.refresh_listener_registration = True
            self.__listeners["main_listener"] = listener
            self.__start_listeners_registration_thread()

        self.__osl_version = self._get_osl_version()
        self.__osl_version_string = self._get_osl_version_string()

        if self.__osl_version[0] is not None:
            if self.__osl_version[0] < 23:
                self._logger.warning(
                    f"The version of the used Ansys optiSLang ({self.__osl_version_string})"
                    " is not fully supported. Please use at least version 23.1."
                )

    @property
    def host(self) -> Optional[str]:
        """Get optiSLang server address or domain name.

        Get a string representation of an IPv4/v6 address or domain name
        of the running optiSLang server.

        Returns
        -------
        timeout: Optional[int]
            The IPv4/v6 address or domain name of the running optiSLang server, if applicable.
            Defaults to ``None``.
        """
        return self.__host

    @property
    def max_request_attempts_register(self) -> FunctionsAttributeRegister:
        """Register with maximum number of attempts to be executed for individual functions.

        If max_request_attempts for specific function is not specified, default value is used.
        """
        return self.__max_request_attempts_register

    @property
    def osl_version(self) -> OslVersion:
        """Version of used optiSLang.

        Returns
        -------
        OslVersion
            optiSLang version as typing.NamedTuple containing
            major, minor, maintenance and revision versions.
        """
        return self.__osl_version

    @property
    def osl_version_string(self) -> str:
        """Version of used optiSLang.

        Returns
        -------
        str
            optiSLang version.
        """
        return self.__osl_version_string

    @property
    def port(self) -> Optional[int]:
        """Get the port the osl server is listening on.

        Returns
        -------
        timeout: Optional[int]
            The port the osl server is listening on, if applicable.
            Defaults to ``None``.
        """
        return self.__port

    @property
    def timeout(self) -> Optional[float]:
        """Get default timeout value for execution of commands.

        Returns
        -------
        timeout: Optional[float]
            Timeout in seconds to perform commands.
        """
        return self.timeouts_register.default_value

    @timeout.setter
    def timeout(self, timeout: Optional[float] = 30) -> None:
        """Set default timeout value for execution of commands.

        Parameters
        ----------
        timeout: Optional[float]
            Timeout in seconds to perform commands, it must be greater than zero or ``None``.
            Certain functions will raise a timeout exception if the timeout period value has
            elapsed before the operation has completed.
            If ``None`` is given, functions will wait until they're finished (no timeout
            exception is raised). Defaults to ``30``.
        """
        self.timeouts_register.default_value = timeout

    @property
    def timeouts_register(self) -> FunctionsAttributeRegister:
        """Register with timeout for a single attempt of execution for individual functions.

        If timeout for specific function is not specified, default value is used.
        """
        return self.__timeouts_register

    def add_criterion(
        self, uid: str, criterion_type: str, expression: str, name: str, limit: Optional[str] = None
    ) -> None:
        """Create criterion for the system.

        Parameters
        ----------
        uid : str
            Actor uid.
        criterion_type: str
            Type of the criterion.
        expression: str
            Expression to be evaluated.
        name: str
            Criterion name.
        limit: Optional[str], optional
            Limit expression to be evaluated.

        Raises
        ------
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.add_criterion.__name__
        self.send_command(
            command=commands.add_criterion(
                actor_uid=uid,
                criterion_type=criterion_type,
                expression=expression,
                name=name,
                limit=limit,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def connect_nodes(
        self,
        from_actor_uid: str,
        from_slot: str,
        to_actor_uid: str,
        to_slot: str,
        skip_rename_slot: bool = False,
    ) -> None:
        """Connect 2 nodes.

        Parameters
        ----------
        from_actor_uid : str
            Uid of the sending actor.
        from_slot : str
            Slot of the sending actor.
        to_actor_uid : str
            Uid of the receiving actor.
        to_slot : str
            Slot of the receiving actor.
        skip_rename_slot: bool, optional
            Skip automatic slot rename for untyped slots.
            Defaults to False.

            .. note:: Argument has effect for Ansys optiSLang version >= 25.2 only.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.connect_nodes.__name__
        self.send_command(
            command=commands.connect_nodes(
                from_actor_uid=from_actor_uid,
                from_slot=from_slot,
                to_actor_uid=to_actor_uid,
                to_slot=to_slot,
                skip_rename_slot=skip_rename_slot,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def create_node(
        self,
        type_: str,
        name: Optional[str] = None,
        algorithm_type: Optional[str] = None,
        integration_type: Optional[str] = None,
        mop_node_type: Optional[str] = None,
        node_type: Optional[str] = None,
        parent_uid: Optional[str] = None,
        design_flow: Optional[str] = None,
    ) -> str:
        """Create a new node of given type.

        Parameters
        ----------
        type_ : str
            Type of the node.
        name : Optional[str], optional
            Node name, by default ``None``.
        algorithm_type : Optional[str], optional
            Algorithm type, e. g. 'algorithm_plugin', by default None.
        integration_type : Optional[str], optional
            Integration type, e. g. 'integration_plugin', by default None.
        mop_node_type : Optional[str], optional
            MOP node type, e. g. 'python_based_mop_node_plugin', by default None.
        node_type: Optional[str], optional
            Node type, e. g. 'python_based_node_plugin`, by default None.
        parent_uid : Optional[str], optional
            Parent uid, by default ``None``.
        design_flow : Optional[str], optional
            Design flow option, by default ``None``.

        Returns
        -------
        str
            Uid of the created node.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.create_node.__name__
        output: List[dict] = self.send_command(
            commands.create_node(
                type_=type_,
                name=name,
                algorithm_type=algorithm_type,
                integration_type=integration_type,
                mop_node_type=mop_node_type,
                node_type=node_type,
                parent_uid=parent_uid,
                design_flow=design_flow,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )
        if len(output) > 1:
            self._logger.error(f"``len(output) == {len(output)}``, but only 1 item was expected.")
        return output[0].get("result_data", {}).get("actor_uid")

    def create_input_slot(
        self, actor_uid: str, slot_name: str, type_hint: Optional[str] = None
    ) -> None:
        """Create dynamic input slot.

        Parameters
        ----------
        actor_uid : str
            Uid of the actor.
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
        current_func_name = self.create_input_slot.__name__
        self.send_command(
            command=commands.create_input_slot(
                actor_uid=actor_uid,
                slot_name=slot_name,
                type_hint=type_hint,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def create_output_slot(
        self, actor_uid: str, slot_name: str, type_hint: Optional[str] = None
    ) -> None:
        """Create dynamic output slot.

        Parameters
        ----------
        actor_uid : str
            Uid of the actor.
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
        current_func_name = self.create_output_slot.__name__
        self.send_command(
            command=commands.create_output_slot(
                actor_uid=actor_uid,
                slot_name=slot_name,
                type_hint=type_hint,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def disconnect_slot(self, uid: str, slot_name: str, direction: str) -> None:
        """Remove all connections for a given slot.

        Parameters
        ----------
        uid : str
            Node uid.
        slot_name : str
            Slot name.
        direction : str
            String specifying direction, either 'sdInputs' <or> 'sdOuputs'.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.disconnect_slot.__name__
        self.send_command(
            command=commands.disconnect_slot(
                actor_uid=uid,
                slot_name=slot_name,
                direction=direction,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def dispose(self) -> None:
        """Terminate all local threads and unregister listeners.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        if self.__disposed:
            return

        self.__stop_listeners_registration_thread()
        self.__unregister_all_listeners()
        self.__dispose_all_listeners()
        self.__disposed = True

    def evaluate_design(self, evaluate_dict: Dict[str, float]) -> List[dict]:
        """Evaluate requested design.

        Parameters
        ----------
        evaluate_dict: Dict[str, float]
            {'parName': value, ...}

        Returns
        -------
        List[dict]
            Output from optislang server.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.evaluate_design.__name__
        return self.send_command(
            command=commands.evaluate_design(evaluate_dict, self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_actor_info(
        self,
        uid: str,
        include_log_messages: bool = True,
        include_integrations_registered_locations: bool = True,
    ) -> Dict:
        """Get info about actor defined by uid.

        Parameters
        ----------
        uid : str
            Actor uid.
        include_log_messages: bool, optional
            Whether actor log messages are to be included.
        include_integrations_registered_locations: bool, optional
            Whether registered integration locations are to be included.

        Returns
        -------
        Dict
            Info about actor defined by uid.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_actor_info.__name__
        return self.send_command(
            command=queries.actor_info(
                uid=uid,
                include_log_messages=include_log_messages,
                include_integrations_registered_locations=include_integrations_registered_locations,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_actor_internal_variables(
        self, uid: str, include_reference_values: bool = True
    ) -> List[dict]:
        """Get currently registered internal variables for a certain (integration) actor.

        Parameters
        ----------
        uid : str
            Actor uid.
        include_reference_values: bool, optional
            Whether reference values are to be included.

        Returns
        -------
        List[dict]
            Actor's internal variables.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_actor_internal_variables.__name__
        return self.send_command(
            command=queries.actor_internal_variables(
                uid=uid, include_reference_values=include_reference_values, password=self.__password
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )["internal_variables"]

    def get_actor_properties(self, uid: str) -> Dict:
        """Get properties of actor defined by uid.

        Parameters
        ----------
        uid : str
            Actor uid.

        Returns
        -------
        Dict
            Properties of actor defined by uid.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_actor_properties.__name__
        return self.send_command(
            command=queries.actor_properties(uid=uid, password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )["properties"]

    def get_actor_registered_input_slots(
        self, uid: str, include_reference_values: bool = True
    ) -> List[dict]:
        """Get currently registered input slots for a certain (integration) actor.

        Parameters
        ----------
        uid : str
            Actor uid.
        include_reference_values: bool, optional
            Whether reference values are to be included.

        Returns
        -------
        List[dict]
            Actor's registered input slots.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_actor_registered_input_slots.__name__
        return self.send_command(
            command=queries.actor_registered_input_slots(
                uid=uid, include_reference_values=include_reference_values, password=self.__password
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )["registered_input_slots"]

    def get_actor_registered_output_slots(
        self, uid: str, include_reference_values: bool = True
    ) -> List[dict]:
        """Get currently registered output slots for a certain (integration) actor.

        Parameters
        ----------
        uid : str
            Actor uid.
        include_reference_values: bool, optional
            Whether reference values are to be included.

        Returns
        -------
        List[dict]
            Actor's registered output slots.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_actor_registered_output_slots.__name__
        return self.send_command(
            command=queries.actor_registered_output_slots(
                uid=uid, include_reference_values=include_reference_values, password=self.__password
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )["registered_output_slots"]

    def get_actor_registered_parameters(
        self, uid: str, include_reference_values: bool = True
    ) -> List[dict]:
        """Get currently registered parameters for a certain (integration) actor.

        Parameters
        ----------
        uid : str
            Actor uid.
        include_reference_values: bool, optional
            Whether reference values are to be included.

        Returns
        -------
        List[dict]
            Actor's registered parameters.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_actor_registered_parameters.__name__
        return self.send_command(
            command=queries.actor_registered_parameters(
                uid=uid, include_reference_values=include_reference_values, password=self.__password
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )["registered_parameters"]

    def get_actor_registered_responses(
        self, uid: str, include_reference_values: bool = True
    ) -> List[dict]:
        """Get currently registered responses for a certain (integration) actor.

        Parameters
        ----------
        uid : str
            Actor uid.
        include_reference_values: bool, optional
            Whether reference values are to be included.

        Returns
        -------
        List[dict]
            Actor's registered responses.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_actor_registered_responses.__name__
        return self.send_command(
            command=queries.actor_registered_responses(
                uid=uid, include_reference_values=include_reference_values, password=self.__password
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )["registered_responses"]

    def get_actor_states(
        self,
        uid: str,
        include_state_info: bool = False,
    ) -> Dict:
        """Get available actor states for a certain actor.

        These can be used in conjunction with "get_actor_status_info" to obtain actor status info
        for a specific state ID.

        Parameters
        ----------
        uid : str
            Actor uid.
        include_state_info: bool
            Include additional info for each state. Otherwise, only state IDs are returned.
        Returns
        -------
        Dict
            Info about actor defined by uid.
        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_actor_states.__name__
        return self.send_command(
            command=queries.actor_states(
                uid=uid,
                include_state_info=include_state_info,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_actor_status_info(
        self,
        uid: str,
        hid: str,
        include_designs: bool = True,
        include_design_values: bool = True,
        include_non_scalar_design_values: bool = False,
        include_algorithm_info: bool = False,
    ) -> Dict:
        """Get status info about actor defined by actor uid and state Hid.

        Parameters
        ----------
        uid : str
            Actor uid.
        hid: str
            State/Design hierarchical id.
        include_designs: bool
            Include (result) designs in status info response.
        include_design_values: bool
            Include values in (result) designs.
        include_non_scalar_design_values: bool
            Include non scalar values in (result) designs.
        include_algorithm_info: bool
            Include algorithm result info in status info response.
        Returns
        -------
        Dict
            Info about actor defined by uid.
        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_actor_status_info.__name__
        return self.send_command(
            command=queries.actor_status_info(
                uid=uid,
                hid=hid,
                include_designs=include_designs,
                include_design_values=include_design_values,
                include_non_scalar_design_values=include_non_scalar_design_values,
                include_algorithm_info=include_algorithm_info,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_actor_supports(self, uid: str, feature_name: str) -> bool:
        """Get supported features of actor defined by uid.

        Parameters
        ----------
        uid : str
            Actor uid.
        feature_name : str
            Name of the feature.

        Returns
        -------
        bool
            Whether the given feature is supported.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_actor_supports.__name__
        return self.send_command(
            command=queries.actor_supports(
                uid=uid, feature_name=feature_name, password=self.__password
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )[feature_name.lower()]

    def get_available_input_locations(self, uid: str) -> List[dict]:
        """Get available input locations for a certain (integration) actor, if supported.

        Parameters
        ----------
        uid : str
            Actor uid.

        Returns
        -------
        List[dict]
            Actor's available input locations.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_available_input_locations.__name__
        return self.send_command(
            command=queries.available_input_locations(uid=uid, password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )["available_input_locations"]

    def get_available_nodes(self) -> Dict[str, List[str]]:
        """Get available node types for current oSL server.

        Returns
        -------
        Dict[str, List[str]]
            Dictionary of available nodes types

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_available_nodes.__name__
        available_nodes = self.send_command(
            command=queries.available_nodes(self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )
        available_nodes.pop("message")
        available_nodes.pop("status")
        return available_nodes

    def get_available_output_locations(self, uid: str) -> List[dict]:
        """Get available output locations for a certain (integration) actor, if supported.

        Parameters
        ----------
        uid : str
            Actor uid.

        Returns
        -------
        List[dict]
            Actor's available output locations.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_available_output_locations.__name__
        return self.send_command(
            command=queries.available_output_locations(uid=uid, password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )["available_output_locations"]

    def get_basic_project_info(self) -> Dict:
        """Get basic project info, like name, location, global settings and status.

        Returns
        -------
        Dict
            Information data as dictionary.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_basic_project_info.__name__
        return self.send_command(
            command=queries.basic_project_info(self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_criteria(self, uid: str) -> List[dict]:
        """Get information about all existing criterion from the system.

        Parameters
        ----------
        uid : str
            Actor uid.
        Returns
        -------
        List[dict]
            Criteria information.
        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_criteria.__name__
        return (
            self.send_command(
                command=queries.get_criteria(uid=uid, password=self.__password),
                timeout=self.timeouts_register.get_value(current_func_name),
                max_request_attempts=self.max_request_attempts_register.get_value(
                    current_func_name
                ),
            )["criteria"]
            or []
        )

    def get_criterion(self, uid: str, name: str) -> Dict:
        """Get existing criterion from the system.

        Parameters
        ----------
        uid : str
            Actor uid.
        name: str
            Criterion name.
        Returns
        -------
        Dict
            Criterion information.
        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_criterion.__name__
        return self.send_command(
            command=queries.get_criterion(uid=uid, name=name, password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )["criteria"]

    def get_designs(self, uid: str) -> List[dict]:
        """Get pending designs from parent node.

        Parameters
        ----------
        uid : str
            Actor uid.

        Returns
        -------
        List[dict]
           List of pending designs.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_designs.__name__
        return self.send_command(
            command=queries.get_designs(
                uid=uid,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )["designs"]

    def get_doe_size(self, uid: str, sampling_type: str, num_discrete_levels: int) -> int:
        """Get the DOE size for given sampling type and number of levels for a specific actor.

        Parameters
        ----------
        uid : str
            Actor uid.
        sampling_type: str
            Sampling type.
        num_discrete_levels: int
            Number of discrete levels.
        Returns
        -------
        int
            DOE size.
        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_doe_size.__name__
        return self.send_command(
            command=queries.doe_size(
                uid=uid,
                sampling_type=sampling_type,
                num_discrete_levels=num_discrete_levels,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )["number_of_samples"]

    def get_full_project_status_info(
        self,
        include_designs: bool = True,
        include_design_values: bool = True,
        include_non_scalar_design_values: bool = False,
        include_algorithm_info: bool = False,
        include_log_messages: bool = True,
        include_integrations_registered_locations: bool = True,
    ) -> Dict:
        """Get full project status info.

        Parameters
        ----------
        include_designs: bool
            Include (result) designs in status info response.
        include_design_values: bool
            Include values in (result) designs.
        include_non_scalar_design_values: bool
            Include non scalar values in (result) designs.
        include_algorithm_info: bool
            Include algorithm result info in status info response.
        include_log_messages: bool, optional
            Whether actor log messages are to be included.
        include_integrations_registered_locations: bool, optional
            Whether registered integration locations are to be included.
        Returns
        -------
        Dict
            Full project status info.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_full_project_status_info.__name__
        return self.send_command(
            command=queries.full_project_status_info(
                include_designs=include_designs,
                include_design_values=include_design_values,
                include_non_scalar_design_values=include_non_scalar_design_values,
                include_algorithm_info=include_algorithm_info,
                include_log_messages=include_log_messages,
                include_integrations_registered_locations=include_integrations_registered_locations,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_full_project_tree(self) -> Dict:
        """Get full project tree.

        Returns
        -------
        Dict
            Dictionary of full project tree without properties.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_full_project_tree.__name__
        return self.send_command(
            command=queries.full_project_tree(password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_full_project_tree_with_properties(self) -> Dict:
        """Get full project tree with properties.

        Returns
        -------
        Dict
            Dictionary of project tree with properties.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_full_project_tree_with_properties.__name__
        return self.send_command(
            command=queries.full_project_tree_with_properties(password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_full_subtree_status_info(
        self,
        uid: str,
        include_designs: bool = True,
        include_design_values: bool = True,
        include_non_scalar_design_values: bool = False,
        include_algorithm_info: bool = False,
        include_log_messages: bool = True,
        include_integrations_registered_locations: bool = True,
    ) -> Dict:
        """Get full status info for a sub tree.

        Parameters
        ----------
        uid : str
            Actor uid.
        include_designs: bool
            Include (result) designs in status info response.
        include_design_values: bool
            Include values in (result) designs.
        include_non_scalar_design_values: bool
            Include non scalar values in (result) designs.
        include_algorithm_info: bool
            Include algorithm result info in status info response.
        include_log_messages: bool, optional
            Whether actor log messages are to be included.
        include_integrations_registered_locations: bool, optional
            Whether registered integration locations are to be included.

        Returns
        -------
        Dict
            Status info for the specified sub tree.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_full_subtree_status_info.__name__
        return self.send_command(
            command=queries.full_subtree_status_info(
                uid=uid,
                include_designs=include_designs,
                include_design_values=include_design_values,
                include_non_scalar_design_values=include_non_scalar_design_values,
                include_algorithm_info=include_algorithm_info,
                include_log_messages=include_log_messages,
                include_integrations_registered_locations=include_integrations_registered_locations,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    @deprecated(version="0.6.0", reason="Use :py:attr:`TcpOslServer.host` instead.")
    def get_host(self) -> Optional[str]:
        """Get optiSLang server address or domain name.

        Get a string representation of an IPv4/v6 address or domain name
        of the running optiSLang server.

        Returns
        -------
        timeout: Optional[str]
            The IPv4/v6 address or domain name of the running optiSLang server, if applicable.
            Defaults to ``None``.
        """
        return self.__host

    def get_hpc_licensing_forwarded_environment(self, uid: str) -> Dict:
        """Get hpc licensing forwarded environment for certain actor.

        Parameters
        ----------
        uid : str
            Actor uid.

        Returns
        -------
        Dict
            Dictionary with hpc licensing forwarded environment for certain actor.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_hpc_licensing_forwarded_environment.__name__
        return self.send_command(
            command=queries.hpc_licensing_forwarded_environment(uid=uid, password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_input_slot_value(
        self, uid: str, hid: str, slot_name: str, legacy_design_format: bool = False
    ) -> Dict:
        """Get input slot value of actor defined by uid.

        Parameters
        ----------
        uid : str
            Actor uid.
        hid: str
            State/Design hierarchical id.
        slot_name: str
            Slot name.
        legacy_design_format: bool, optional
            Whether to use legacy format for designs and design container type slots.
            Defaults to false.

            .. note:: Argument has effect for Ansys optiSLang version >= 25.2 only.

        Returns
        -------
        Dict
            Input slot value of the actor.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_input_slot_value.__name__
        return self.send_command(
            command=queries.input_slot_value(
                uid=uid,
                hid=hid,
                slot_name=slot_name,
                legacy_design_format=legacy_design_format,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_output_slot_value(
        self, uid: str, hid: str, slot_name: str, legacy_design_format: bool = False
    ) -> Dict:
        """Get output slot value of actor defined by uid.

        Parameters
        ----------
        uid : str
            Actor uid.
        hid: str
            State/Design hierarchical id.
        slot_name: str
            Slot name.
        legacy_design_format: bool, optional
            Whether to use legacy format for designs and design container type slots.
            Defaults to false.

            .. note:: Argument has effect for Ansys optiSLang version >= 25.2 only.

        Returns
        -------
        Dict
            Output slot value of the actor.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_output_slot_value.__name__
        return self.send_command(
            command=queries.output_slot_value(
                uid=uid,
                hid=hid,
                slot_name=slot_name,
                legacy_design_format=legacy_design_format,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    @deprecated(version="0.5.0", reason="Use :py:attr:`TcpOslServer.osl_version` instead.")
    def get_osl_version(self) -> OslVersion:
        """Get version of used optiSLang.

        Returns
        -------
        OslVersion
            optiSLang version as typing.NamedTuple containing
            major, minor, maintenance and revision versions.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        RuntimeError
            Raised when parsing version numbers from string fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self._get_osl_version()

    @deprecated(version="0.5.0", reason="Use :py:attr:`TcpOslServer.osl_version_string` instead.")
    def get_osl_version_string(self) -> str:
        """Get version of used optiSLang.

        Returns
        -------
        str
            optiSLang version.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self._get_osl_version_string()

    @deprecated(version="0.6.0", reason="Use :py:attr:`TcpOslServer.port` instead.")
    def get_port(self) -> Optional[int]:
        """Get the port the osl server is listening on.

        Returns
        -------
        timeout: Optional[int]
            The port the osl server is listening on, if applicable.
            Defaults to ``None``.
        """
        return self.__port

    @deprecated(
        version="0.6.0",
        reason=(
            "This functionality was moved to "
            ":py:class:`Project <ansys.optislang.core.project.Project>`."
        ),
    )
    def get_project_description(self) -> Optional[str]:
        """Get description of optiSLang project.

        Returns
        -------
        Optional[str]
            optiSLang project description. If no project is loaded in the optiSLang,
            returns ``None``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        project_info = self.get_basic_project_info()
        if len(project_info.get("projects", [])) == 0:
            return None
        return (
            project_info.get("projects", [{}])[0].get("settings", {}).get("short_description", None)
        )

    @deprecated(
        version="0.6.0",
        reason=(
            "This functionality was moved to "
            ":py:class:`Project <ansys.optislang.core.project.Project>`."
        ),
    )
    def get_project_location(self) -> Optional[Path]:
        """Get path to the optiSLang project file.

        Returns
        -------
        Optional[pathlib.Path]
            Path to the optiSLang project file. If no project is loaded in the optiSLang,
            returns ``None``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        project_info = self.get_basic_project_info()
        project_path = project_info.get("projects", [{}])[0].get("location", None)
        return None if not project_path else Path(project_path)

    @deprecated(
        version="0.6.0",
        reason=(
            "This functionality was moved to "
            ":py:class:`Project <ansys.optislang.core.project.Project>`."
        ),
    )
    def get_project_name(self) -> Optional[str]:
        """Get name of the optiSLang project.

        Returns
        -------
        Optional[str]
            Name of the optiSLang project. If no project is loaded in the optiSLang,
            returns ``None``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        project_info = self.get_basic_project_info()
        if len(project_info.get("projects", [])) == 0:
            return None
        return project_info.get("projects", [{}])[0].get("name", None)

    @deprecated(
        version="0.6.0",
        reason=(
            "This functionality was moved to "
            ":py:class:`Project <ansys.optislang.core.project.Project>`."
        ),
    )
    def get_project_status(self) -> Optional[str]:
        """Get status of the optiSLang project.

        Returns
        -------
        Optional[str]
            optiSLang project status. If no project is loaded in the optiSLang,
            returns ``None``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self.__get_project_status()

    @deprecated(
        version="0.6.0",
        reason=(
            "This functionality was moved to "
            ":py:class:`Project <ansys.optislang.core.project.Project>`."
        ),
    )
    def get_project_uid(self) -> str:
        """Get project uid.

        Returns
        -------
        str
            Project uid. If no project is loaded in the optiSLang, returns `None`.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        project_tree = self.get_full_project_tree_with_properties()
        project_uid = project_tree.get("projects", [{}])[0].get("system", {}).get("uid", None)
        return project_uid

    def get_project_tree_systems(self) -> Dict:
        """Get project tree systems without properties.

        Returns
        -------
        Dict
            Dictionary of project tree systems without properties.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_project_tree_systems.__name__
        return self.send_command(
            command=queries.project_tree_systems(password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_project_tree_systems_with_properties(self) -> Dict:
        """Get project tree systems with properties.

        Returns
        -------
        Dict
            Dictionary of project tree systems with properties.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_project_tree_systems_with_properties.__name__
        return self.send_command(
            command=queries.project_tree_systems_with_properties(password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_result_design(
        self,
        uid: str,
        design_id: str,
    ) -> Dict:
        """Get specific result design values defined by actor uid and design ID.

        Parameters
        ----------
        uid : str
            Actor uid.
        design_id: str
            Design ID.
        Returns
        -------
        Dict
            Result design values.
        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_result_design.__name__
        return self.send_command(
            command=queries.result_design(
                uid=uid,
                design_id=design_id,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_server_info(self) -> Dict:
        """Get information about the application, the server configuration and the open projects.

        Returns
        -------
        Dict
            Information data as dictionary.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_server_info.__name__
        return self.send_command(
            command=queries.server_info(self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def get_server_is_alive(self) -> bool:
        """Get info whether the server is alive.

        Returns
        -------
        bool
            Whether the server is alive.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_server_is_alive.__name__
        return (
            self.send_command(
                command=queries.server_is_alive(password=self.__password),
                timeout=self.timeouts_register.get_value(current_func_name),
                max_request_attempts=self.max_request_attempts_register.get_value(
                    current_func_name
                ),
            ).get("status")
            == "success"
        )

    def get_systems_status_info(
        self,
        include_designs: bool = True,
        include_design_values: bool = True,
        include_non_scalar_design_values: bool = False,
        include_algorithm_info: bool = False,
        include_log_messages: bool = True,
        include_integrations_registered_locations: bool = True,
    ) -> Dict:
        """Get project status info, including systems only.

        Parameters
        ----------
        include_designs: bool
            Include (result) designs in status info response.
        include_design_values: bool
            Include values in (result) designs.
        include_non_scalar_design_values: bool
            Include non scalar values in (result) designs.
        include_algorithm_info: bool
            Include algorithm result info in status info response.
        include_log_messages: bool, optional
            Whether actor log messages are to be included.
        include_integrations_registered_locations: bool, optional
            Whether registered integration locations are to be included.
        Returns
        -------
        Dict
            Project status info including systems only.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.get_systems_status_info.__name__
        return self.send_command(
            command=queries.systems_status_info(
                include_designs=include_designs,
                include_design_values=include_design_values,
                include_non_scalar_design_values=include_non_scalar_design_values,
                include_algorithm_info=include_algorithm_info,
                include_log_messages=include_log_messages,
                include_integrations_registered_locations=include_integrations_registered_locations,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    @deprecated(
        version="0.5.0",
        reason="Use :py:attr:`TcpOslServer.timeouts_register.default_value` instead.",
    )
    def get_timeout(self) -> Optional[float]:
        """Get current timeout value for execution of commands.

        Returns
        -------
        timeout: Optional[float]
            Timeout in seconds to perform commands.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        return self.timeouts_register.default_value

    @deprecated(
        version="0.6.0",
        reason=(
            "This functionality was moved to "
            ":py:class:`Project <ansys.optislang.core.project.Project>`."
        ),
    )
    def get_working_dir(self) -> Path:
        """Get path to the optiSLang project working directory.

        Returns
        -------
        pathlib.Path
            Path to the optiSLang project working directory. If no project is loaded
            in the optiSLang, returns ``None``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        project_info = self.get_basic_project_info()
        if len(project_info.get("projects", [])) == 0:
            return None
        return Path(project_info.get("projects", [{}])[0].get("working_dir", None))

    def load(self, uid: str, args: Optional[Dict[str, Any]] = None) -> None:
        """Explicit load of node.

        Parameters
        ----------
        uid: str
            Actor uid.
        args: Optional[Dict[str, any]], optional
            Additional arguments, by default ``None``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: create unit test
        current_func_name = self.load.__name__
        self.send_command(
            command=commands.load(
                actor_uid=uid,
                args=args,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def new(self) -> None:
        """Create a new project.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.new.__name__
        self.send_command(
            command=commands.new(password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def open(
        self,
        file_path: Union[str, Path],
        force: bool = True,
        restore: bool = False,
        reset: bool = False,
        project_properties_file: Optional[str] = None,
    ) -> None:
        """Open a new project.

        Parameters
        ----------
        file_path : Union[str, pathlib.Path]
            Path to the optiSLang project file to open.
        force : bool, optional
            Whether to force opening of project even if (non-critical) errors occur.
            Non-critical errors include:
            - Timestamp of (auto) save point newer than project timestamp
            - Project (file) incomplete
        restore : bool, optional
            Whether to restore project from last (auto) save point (if present).
        reset : bool, optional
            Whether to reset project after load.
        project_properties_file : Optional[str], optional
            Project properties file to import, by default ``None``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        file_path = self.__cast_to_path(file_path=file_path)
        self.__validate_path(file_path=file_path)

        current_func_name = self.open.__name__

        if self.__osl_version[0] < 24:
            self._logger.error(
                f"Command ``open`` doesn't work correctly in version {self.__osl_version_string}."
                " Please use at least version 24.1."
            )

        self.send_command(
            command=commands.open(
                path=str(file_path.as_posix()),
                do_force=force,
                do_restore=restore,
                do_reset=reset,
                password=self.__password,
                project_properties_file=project_properties_file,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def re_register_locations_as_parameter(self, uid: str) -> None:
        """Adjust all input locations with the already registered parameters.

        Parameters
        ----------
        uid: str
            Actor uid.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: create unit test
        current_func_name = self.re_register_locations_as_parameter.__name__
        self.send_command(
            command=commands.re_register_locations_as_parameter(
                actor_uid=uid,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def re_register_locations_as_response(self, uid: str) -> None:
        """Adjust all input locations with the already registered responses.

        Parameters
        ----------
        uid: str
            Actor uid.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: create unit test
        current_func_name = self.re_register_locations_as_response.__name__
        self.send_command(
            command=commands.re_register_locations_as_response(
                actor_uid=uid,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def register_location_as_input_slot(
        self,
        uid: str,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:
        """Register a certain (input) location as a input slot.

        Parameters
        ----------
        uid: str
            Actor uid.
        location: Any
            Specification of location, depends on actor type.
        name: Optional[str], optional
            Input slot name.
        reference_value: Optional[Any], optional
            Input slot reference value.

        Returns
        -------
        str
            Name of the actual created input slot.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.register_location_as_input_slot.__name__
        server_response = self.send_command(
            command=commands.register_location_as_input_slot(
                actor_uid=uid,
                location=location,
                name=name,
                reference_value=reference_value,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

        return server_response[0]["actual_name"]

    def register_location_as_internal_variable(
        self,
        uid: str,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:
        """Register a certain (output) location as an internal variable.

        Parameters
        ----------
        uid: str
            Actor uid.
        location: Any
            Specification of location, depends on actor type.
        name: Optional[str], optional
            Variable name.
        reference_value: Optional[Any], optional
            Variable reference value.

        Returns
        -------
        str
            Name of the actual created internal variable.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: create unit test
        current_func_name = self.register_location_as_internal_variable.__name__
        server_response = self.send_command(
            command=commands.register_location_as_internal_variable(
                actor_uid=uid,
                location=location,
                name=name,
                reference_value=reference_value,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

        return server_response[0]["actual_name"]

    def register_location_as_output_slot(
        self,
        uid: str,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:
        """Register a certain (output) location as a output slot.

        Parameters
        ----------
        uid: str
            Actor uid.
        location: Any
            Specification of location, depends on actor type.
        name: Optional[str], optional
            Output slot name.
        reference_value: Optional[Any], optional
            Output slot reference value.

        Returns
        -------
        str
            Name of the actual created output slot.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.register_location_as_output_slot.__name__
        server_response = self.send_command(
            command=commands.register_location_as_output_slot(
                actor_uid=uid,
                location=location,
                name=name,
                reference_value=reference_value,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

        return server_response[0]["actual_name"]

    def register_location_as_parameter(
        self,
        uid: str,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:
        """Register a certain (input) location as a parameter.

        Parameters
        ----------
        uid: str
            Actor uid.
        location: Any
            Specification of location, depends on actor type.
        name: Optional[str], optional
            Parameter name.
        reference_value: Optional[Any], optional
            Parameter reference value.

        Returns
        -------
        str
            Name of the actual created parameter.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.register_location_as_parameter.__name__
        server_response = self.send_command(
            command=commands.register_location_as_parameter(
                actor_uid=uid,
                location=location,
                name=name,
                reference_value=reference_value,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

        return server_response[0]["actual_name"]

    def register_locations_as_parameter(
        self,
        uid: str,
    ) -> None:
        """Register all input locations as parameters initially.

        Parameters
        ----------
        uid: str
            Actor uid.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: create unit test
        current_func_name = self.register_locations_as_parameter.__name__
        self.send_command(
            command=commands.register_locations_as_parameter(
                actor_uid=uid,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def register_location_as_response(
        self,
        uid: str,
        location: Any,
        name: Optional[str] = None,
        reference_value: Optional[Any] = None,
    ) -> str:
        """Register a certain (output) location as a response.

        Parameters
        ----------
        uid: str
            Actor uid.
        location: Any
            Specification of location, depends on actor type.
        name: Optional[str], optional
            Response name.
        reference_value: Optional[Any], optional
            Response reference value.

        Returns
        -------
        str
            Name of the actual created response.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.register_location_as_response.__name__
        server_response = self.send_command(
            command=commands.register_location_as_response(
                actor_uid=uid,
                location=location,
                name=name,
                reference_value=reference_value,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

        return server_response[0]["actual_name"]

    def register_locations_as_response(
        self,
        uid: str,
    ) -> None:
        """Registration of all input locations as responses initially.

        Parameters
        ----------
        uid: str
            Actor uid.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        # TODO: create unit test
        current_func_name = self.register_locations_as_response.__name__
        self.send_command(
            command=commands.register_locations_as_response(
                actor_uid=uid,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def remove_criteria(self, uid: str) -> None:
        """Remove all criteria from the system.

        Parameters
        ----------
        uid : str
            Actor uid.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.remove_criteria.__name__
        self.send_command(
            command=commands.remove_criteria(actor_uid=uid, password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def remove_criterion(self, uid: str, name: str) -> None:
        """Remove existing criterion from the system.

        Parameters
        ----------
        uid : str
            Actor uid.
        name: str
            Name of the criterion.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.remove_criterion.__name__
        self.send_command(
            command=commands.remove_criterion(actor_uid=uid, name=name, password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def remove_node(self, actor_uid: str) -> None:
        """Remove node specified by uid.

        Parameters
        ----------
        actor_uid : str
            Actor uid.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.remove_node.__name__
        self.send_command(
            command=commands.remove_node(actor_uid=actor_uid, password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def rename_node(self, actor_uid: str, new_name: str) -> None:
        """Rename node specified by uid.

        .. note:: Method is supported for Ansys optiSLang version >= 25.2 only.

        Parameters
        ----------
        actor_uid : str
            Actor uid.
        new_name: str
            New node name.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.rename_node.__name__
        self.send_command(
            command=commands.rename_node(
                actor_uid=actor_uid, new_name=new_name, password=self.__password
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def rename_slot(
        self,
        actor_uid: str,
        new_name: str,
        slot_uid: Optional[str] = None,
        slot_name: Optional[str] = None,
    ) -> None:
        """Rename node slot specified by uid or name.

        .. note:: Method is supported for Ansys optiSLang version >= 25.2 only.

        Parameters
        ----------
        actor_uid : str
            Actor uid.
        slot_uid: Optional[str], optional
            UID of the slot to rename. Defaults to ``None``.
            Either slot_uid or slot_name needs to be provided.
        slot_name: Optional[str], optional
            Name of the slot to rename. Defaults to ``None``.
            Either slot_uid or slot_name needs to be provided.
        new_name: str
            New slot name.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.rename_slot.__name__
        self.send_command(
            command=commands.rename_slot(
                actor_uid=actor_uid,
                new_name=new_name,
                slot_uid=slot_uid,
                slot_name=slot_name,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def reset(self, actor_uid: Optional[str] = None, hid: Optional[str] = None):
        """Reset complete project or a specific actor state.

        For a complete project reset, do not specify the actor_uid and hid entries.

        Parameters
        ----------
        actor_uid: Optional[str], optional
            Actor uid entry. A Hierarchical ID (hid) is required. By default ``None``.
        hid: Optional[str], optional
            Hid entry. The actor uid is required. By default ``None``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.reset.__name__
        self.send_command(
            command=commands.reset(actor_uid=actor_uid, hid=hid, password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def run_python_script(
        self,
        script: str,
        args: Union[Sequence[object], None] = None,
    ) -> Tuple[str, str]:
        """Load a Python script in a project context and execute it.

        Parameters
        ----------
        script : str
            Python commands to be executed on the server.
        args : Sequence[object], None, optional
            Sequence of arguments used in Python script. Defaults to ``None``.

        Returns
        -------
        Tuple[str, str]
            STDOUT and STDERR from executed Python script.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.run_python_script.__name__
        responses = self.send_command(
            command=commands.run_python_script(script, args, self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )
        std_out = ""
        std_err = ""
        for response in responses:
            std_out += response.get("std_out", "")
            std_err += response.get("std_err", "")

        return (std_out, std_err)

    def run_python_file(
        self,
        file_path: Union[str, Path],
        args: Union[Sequence[object], None] = None,
    ) -> Tuple[str, str]:
        """Read python script from the file, load it in a project context and execute it.

        Parameters
        ----------
        file_path : Union[str, pathlib.Path]
            Path to the Python script file which content is supposed to be executed on the server.
        args : Sequence[object], None, optional
            Sequence of arguments used in Python script. Defaults to ``None``.

        Returns
        -------
        Tuple[str, str]
            STDOUT and STDERR from executed Python script.

        Raises
        ------
        FileNotFoundError
            Raised when the specified Python script file does not exist.
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError("Python script file does not exist.")

        with open(file_path, "r") as file:
            script = file.read()

        return self.run_python_script(script, args)

    def save(self) -> None:
        """Save the changed data and settings of the current project.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.save.__name__
        self.send_command(
            command=commands.save(password=self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def save_as(
        self,
        file_path: Union[str, Path],
        force: bool = True,
        restore: bool = False,
        reset: bool = False,
    ) -> None:
        """Save and open the current project at a new location.

        Parameters
        ----------
        file_path : Union[str, pathlib.Path]
            Path where to save the project file.
        force : bool, optional
            Whether to force opening of project even if (non-critical) errors occur.
            Non-critical errors include:
            - Timestamp of (auto) save point newer than project timestamp
            - Project (file) incomplete
        restore : bool, optional
            Whether to restore project from last (auto) save point (if present).
        reset : bool, optional
            Whether to reset project after load.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        file_path = self.__cast_to_path(file_path=file_path)
        self.__validate_path(file_path=file_path)
        current_func_name = self.save_as.__name__

        self.send_command(
            command=commands.save_as(
                path=str(file_path.as_posix()),
                do_force=force,
                do_restore=restore,
                do_reset=reset,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def save_copy(self, file_path: Union[str, Path]) -> None:
        """Save the current project as a copy to a location.

        Parameters
        ----------
        file_path : Union[str, pathlib.Path]
            Path where to save the project copy.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        file_path = self.__cast_to_path(file_path=file_path)
        self.__validate_path(file_path=file_path)
        if self.__osl_version[0] < 24:
            self._logger.error(
                "Command ``save_copy`` doesn't work correctly in version"
                f" {self.__osl_version_string}. Please use at least version 24.1."
            )
        current_func_name = self.save_copy.__name__
        self.send_command(
            command=commands.save_copy(str(file_path.as_posix()), self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def send_command(self, command: str, **kwargs) -> Dict:
        """Send command or query to the optiSLang server.

        Parameters
        ----------
        command: str
            Command or query to be executed on optiSLang server.
        timeout: Optional[float], optional
            Timeout to execute command. If not provided,
            `TcpOslServer.timeouts_register.default_value` is used.
        max_request_attempts: int, optional
            Maximum number of attempts to execute command. If not provided,
            `TcpOslServer.max_request_attempts_register.default_value` is used.

        Returns
        -------
        Dict
            Response from the server.

        Raises
        ------
        RuntimeError
            Raised when the optiSLang server is not started.
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout expires.
        """
        timeout = (
            kwargs.get("timeout")
            if "timeout" in kwargs.keys()
            else self.timeouts_register.default_value
        )
        max_request_attempts = (
            kwargs.get("max_request_attempts")
            if "max_request_attempts" in kwargs.keys()
            else self.max_request_attempts_register.default_value
        )
        if self.__disposed:
            raise OslDisposedError("Cannot send command, instance was already disposed.")
        if self.__host is None or self.__port is None:
            raise RuntimeError("optiSLang server is not started.")

        self._logger.debug("Sending command or query to the server: %s", command)
        client = TcpClient(logger=self._logger)

        response_str = ""

        for request_attempt in range(1, max_request_attempts + 1):
            start_time = time.time()
            try:
                client.connect(
                    self.__host,
                    self.__port,
                    timeout=_get_current_timeout(timeout, start_time),
                )
                client.send_msg(command, timeout=_get_current_timeout(timeout, start_time))
                response_str = client.receive_msg(timeout=_get_current_timeout(timeout, start_time))
                break
            except TimeoutError:
                if request_attempt == max_request_attempts:
                    raise
                else:
                    pass
            except Exception as ex:
                raise OslCommunicationError(
                    "An error occurred while communicating with the optiSLang server."
                ) from ex
            finally:
                client.disconnect()

        self._logger.debug("Response received: %s", response_str)
        response = json.loads(response_str)

        if isinstance(response, list):
            for resp_elem in response:
                self.__check_command_response(resp_elem)
        else:
            self.__check_command_response(response)

        return response

    def set_actor_property(self, actor_uid: str, name: str, value: Any) -> None:
        """Set an actor property.

        Parameters
        ----------
        actor_uid : str
            Actor uid.
        name : str
            Property name.
        value : Any
            Property value.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.set_actor_property.__name__
        self.send_command(
            command=commands.set_actor_property(
                actor_uid=actor_uid, name=name, value=value, password=self.__password
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def set_criterion_property(
        self,
        uid: str,
        criterion_name: str,
        name: str,
        value: Any,
    ) -> None:
        """Set the properties of existing criterion for the system.

        Parameters
        ----------
        uid : str
            Actor uid.
        criterion_name: str
            Name of the criterion.
        name: str
            Property name.
        value: Any
            Property value.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.set_criterion_property.__name__
        self.send_command(
            command=commands.set_criterion_property(
                actor_uid=uid,
                criterion_name=criterion_name,
                name=name,
                value=value,
                password=self.__password,
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    def set_designs(self, actor_uid: str, designs: Iterable[dict]) -> None:
        """Set an actor property.

        Parameters
        ----------
        actor_uid : str
            Actor uid.
        designs : Iterable[dict]
            Iterable of calculated designs.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.set_designs.__name__
        self.send_command(
            command=commands.set_designs(
                actor_uid=actor_uid, designs=designs, password=self.__password
            ),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )

    @deprecated(
        version="0.5.0",
        reason="Use :py:attr:`TcpOslServer.timeouts_register.default_value` instead.",
    )
    def set_timeout(self, timeout: Optional[float] = None) -> None:
        """Set timeout value for execution of commands.

        Parameters
        ----------
        timeout: Optional[float]
            Timeout in seconds to perform commands, it must be greater than zero or ``None``.
            Another functions will raise a timeout exception if the timeout period value has
            elapsed before the operation has completed.
            If ``None`` is given, functions will wait until they're finished (no timeout
            exception is raised). Defaults to ``30``.

        Raises
        ------
        ValueError
            Raised when timeout <= 0.
        TypeError
            Raised when timeout not type of ``float`` or ``None``.
        """
        self.timeouts_register.default_value = timeout

    def shutdown(self, force: bool = False) -> None:
        """Shutdown the optiSLang server.

        Stop listening for incoming connections, discard pending requests, and shut down
        the server. Batch mode exclusive: Continue project run until execution finished.
        Terminate optiSLang.

        Parameters
        ----------
        force : bool, optional
            Determines whether to force shutdown the local optiSLang server. Has no effect when
            the connection is established to the remote optiSLang server. In all cases, it is tried
            to shutdown the optiSLang server process in a proper way. However, if the force
            parameter is ``True``, after a while, the process is forced to terminate and no
            exception is raised. Defaults to ``False``.

        Raises
        ------
        OslCommunicationError
            Raised when the parameter force is ``False`` and an error occurs while communicating
            with server.
        OslCommandError
            Raised when the parameter force is ``False`` and the command or query fails.
        TimeoutError
            Raised when the parameter force is ``False`` and the timeout float value expires.
        """
        self.__stop_listeners_registration_thread()
        self.__unregister_all_listeners()
        self.__dispose_all_listeners()

        try:
            current_func_name = self.shutdown.__name__
            self.send_command(
                command=commands.shutdown(force=force, password=self.__password),
                timeout=self.timeouts_register.get_value(current_func_name),
                max_request_attempts=self.max_request_attempts_register.get_value(
                    current_func_name
                ),
            )
        except Exception:
            if not force or self.__osl_process is None:
                raise

        # If desired actively force osl process to terminate
        if force and self.__osl_process is not None:
            self._force_shutdown_local_process()

    def start(self, wait_for_started: bool = True, wait_for_finished: bool = True) -> None:
        """Start project execution.

        Parameters
        ----------
        wait_for_started : bool, optional
            Determines whether this function call should wait on the optiSlang to start
            the command execution. I.e. don't continue on next line of python script
            after command was successfully sent to optiSLang but wait for execution of
            flow inside optiSLang to start.
            Defaults to ``True``.
        wait_for_finished : bool, optional
            Determines whether this function call should wait on the optiSlang to finish
            the command execution. I.e. don't continue on next line of python script
            after command was successfully sent to optiSLang but wait for execution of
            flow inside optiSLang to finish.
            This implicitly interprets wait_for_started as True.
            Defaults to ``True``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        successfully_started = False
        already_running = False
        current_func_name = self.start.__name__

        if self.__get_project_status() == "PROCESSING":
            already_running = True
            self._logger.debug("Status PROCESSING")

        if not already_running and (wait_for_started or wait_for_finished):
            exec_started_listener = self.__create_exec_started_listener(
                timeout=self.timeouts_register.get_value(self.__class__.start)
            )
            exec_started_listener.cleanup_notifications()
            wait_for_started_queue: Queue = Queue()
            exec_started_listener.add_callback(
                self.__class__.__terminate_listener_thread,
                (
                    [
                        ServerNotification.PROCESSING_STARTED.name,
                        ServerNotification.NOTHING_PROCESSED.name,
                    ],
                    wait_for_started_queue,
                    self._logger,
                ),
            )
            exec_started_listener.start_listening()
            self._logger.debug("Wait for started thread was created.")

        if wait_for_finished:
            exec_finished_listener = self.__create_exec_finished_listener(
                self.timeouts_register.get_value(self.__class__.start)
            )
            exec_finished_listener.cleanup_notifications()
            wait_for_finished_queue: Queue = Queue()
            exec_finished_listener.add_callback(
                self.__class__.__terminate_listener_thread,
                (
                    [
                        ServerNotification.EXECUTION_FINISHED.name,
                        ServerNotification.NOTHING_PROCESSED.name,
                    ],
                    wait_for_finished_queue,
                    self._logger,
                ),
            )
            exec_finished_listener.start_listening()
            self._logger.debug("Wait for finished thread was created.")

        if not already_running:
            self.send_command(
                command=commands.start(self.__password),
                timeout=self.timeouts_register.get_value(current_func_name),
                max_request_attempts=self.max_request_attempts_register.get_value(
                    current_func_name
                ),
            )

        if not already_running and (wait_for_started or wait_for_finished):
            self._logger.info("Waiting for started")
            successfully_started = wait_for_started_queue.get()
            self.__delete_exec_started_listener()
            if successfully_started == "Terminate":
                raise TimeoutError("Waiting for started timed out.")
            self._logger.info(f"Successfully started: {successfully_started}.")

        if wait_for_finished and (successfully_started or already_running):
            self._logger.info("Waiting for finished")
            successfully_finished = wait_for_finished_queue.get()
            self.__delete_exec_finished_listener()
            if successfully_finished == "Terminate":
                raise TimeoutError("Waiting for finished timed out.")
            self._logger.info(f"Successfully finished: {successfully_finished}.")

    def stop(self, wait_for_finished: bool = True) -> None:
        """Stop project execution.

        Parameters
        ----------
        wait_for_finished : bool, optional
            Determines whether this function call should wait on the optiSlang to finish
            the command execution. I.e. don't continue on next line of python script after command
            was successfully sent to optiSLang but wait for execution of command inside optiSLang.
            Defaults to ``True``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.stop.__name__

        if wait_for_finished:
            exec_finished_listener = self.__create_exec_finished_listener(
                timeout=self.timeouts_register.get_value(self.__class__.stop)
            )
            exec_finished_listener.cleanup_notifications()
            wait_for_finished_queue: Queue = Queue()
            exec_finished_listener.add_callback(
                self.__class__.__terminate_listener_thread,
                (
                    [
                        ServerNotification.EXECUTION_FINISHED.name,
                        ServerNotification.NOTHING_PROCESSED.name,
                    ],
                    wait_for_finished_queue,
                    self._logger,
                ),
            )
            exec_finished_listener.start_listening()
            self._logger.debug("Wait for finished thread was created.")

        status = self.__get_project_status()

        # do not send stop request if project is already stopped or request
        # with higher or equal priority was already sent
        if status in self._STOPPED_STATES:
            self._logger.debug(f"Do not send STOP request, project status is: {status}")
            if wait_for_finished:
                exec_finished_listener.stop_listening()
                exec_finished_listener.clear_callbacks()
                self.__delete_exec_finished_listener()
            return
        elif status in self._STOP_REQUESTS_PRIORITIES:
            stop_request_priority = self._STOP_REQUESTS_PRIORITIES["STOP"]
            current_status_priority = self._STOP_REQUESTED_STATES_PRIORITIES[status]
            if stop_request_priority > current_status_priority:
                self.send_command(
                    command=commands.stop(password=self.__password),
                    timeout=self.timeouts_register.get_value(current_func_name),
                    max_request_attempts=self.max_request_attempts_register.get_value(
                        current_func_name
                    ),
                )
            else:
                self._logger.debug(f"Do not send STOP request, project status is: {status}")
        else:
            self.send_command(
                command=commands.stop(password=self.__password),
                timeout=self.timeouts_register.get_value(current_func_name),
                max_request_attempts=self.max_request_attempts_register.get_value(
                    current_func_name
                ),
            )

        if wait_for_finished:
            self._logger.info("Waiting for finished")
            successfully_finished = wait_for_finished_queue.get()
            self.__delete_exec_finished_listener()
            if successfully_finished == "Terminate":
                raise TimeoutError("Waiting for finished timed out.")
            self._logger.info(f"Successfully_finished: {successfully_finished}.")

    def _force_shutdown_local_process(self):
        """Force shutdown local optiSLang server process.

        It waits a while and then terminates the process.
        """
        start_time = datetime.now()
        while (
            self.__osl_process.is_running()
            and (datetime.now() - start_time).seconds < self._SHUTDOWN_WAIT
        ):
            time.sleep(0.5)

        if self.__osl_process.is_running():
            self.__osl_process.terminate()
        self.__osl_process = None
        self.__host = None
        self.__port = None

    def _get_osl_version(self) -> OslVersion:
        """Get version of used optiSLang.

        Returns
        -------
        OslVersion
            optiSLang version as typing.NamedTuple containing
            major, minor, maintenance and revision versions.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        RuntimeError
            Raised when parsing version numbers from string fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        osl_version_str = self._get_osl_version_string()

        pattern = r"(\d+)\.(\d+)\.(\d+).*\((\d+)M?\)"
        osl_version_entries = re.fullmatch(pattern, osl_version_str)

        if osl_version_entries:
            major, minor, maintenance, revision = osl_version_entries.groups()
            return OslVersion(int(major), int(minor), int(maintenance), int(revision))
        else:
            raise RuntimeError(
                'Invalid provided optiSLang version string: "{}".'.format(osl_version_str)
            )

    def _get_osl_version_string(self) -> str:
        """Get version of used optiSLang.

        Returns
        -------
        str
            optiSLang version.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        server_info = self.get_server_info()
        return server_info["application"]["version"]

    def _unregister_listener(self, listener: TcpOslListener) -> None:
        """Unregister a listener.

        Parameters
        ----------
        listener : TcpOslListener
            Class with listener properties.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self._unregister_listener.__name__
        self.send_command(
            command=commands.unregister_listener(str(listener.uid), self.__password),
            timeout=self.timeouts_register.get_value(current_func_name),
            max_request_attempts=self.max_request_attempts_register.get_value(current_func_name),
        )
        listener.uid = None

    def _start_local(self, ini_timeout: float, shutdown_on_finished: bool) -> None:
        """Start local optiSLang server.

        Parameters
        ----------
        ini_timeout : float
            Time in seconds to listen to the optiSLang server port. If the port is not listened
            for specified time, the optiSLang server is not started and RuntimeError is raised.
        shutdown_on_finished: bool
            Shut down when execution is finished and there are not any listeners registered.

        Raises
        ------
        RuntimeError
            Raised when the optiSLang server is already started.
            -or-
            Port listener cannot be started.
            -or-
            optiSLang server port is not listened for specified timeout value.
        """
        if self.__osl_process is not None:
            raise RuntimeError("optiSLang server is already started.")

        listener = self.__create_listener(
            uid=self.__listener_id if self.__listener_id else str(uuid.uuid4()),
            timeout=None,
            name="Main",
            notifications=[
                ServerNotification.SERVER_UP,
                ServerNotification.SERVER_DOWN,
            ],
        )
        port_queue: Queue = Queue()
        listener.add_callback(self.__class__.__port_on_listended, (port_queue, self._logger))

        try:
            listener.start_listening(timeout=ini_timeout)

            multi_listener = (
                list(self.__multi_listener) if self.__multi_listener is not None else []
            )

            for host_address in listener.host_addresses:
                multi_listener.append((host_address, listener.port, listener.uid))

            self.__osl_process = OslServerProcess(
                executable=self.__executable,
                project_path=self.__project_path,
                no_save=self.__no_save,
                password=self.__password,
                multi_listener=multi_listener,
                notifications=[
                    ServerNotification.SERVER_UP,
                    ServerNotification.SERVER_DOWN,
                ],
                shutdown_on_finished=shutdown_on_finished,
                logger=self._logger,
                batch=self.__batch,
                service=self.__service,
                port_range=self.__port_range,
                no_run=self.__no_run,
                force=self.__force,
                reset=self.__reset,
                auto_relocate=self.__auto_relocate,
                env_vars=self.__env_vars,
                import_project_properties_file=self.__import_project_properties_file,
                export_project_properties_file=self.__export_project_properties_file,
                import_placeholders_file=self.__import_placeholders_file,
                export_placeholders_file=self.__export_placeholders_file,
                output_file=self.__output_file,
                dump_project_state=self.__dump_project_state,
                opx_project_definition_file=self.__opx_project_definition_file,
                additional_args=self.__additional_args,
            )
            self.__osl_process.start()

            listener.join()
            if not port_queue.empty():
                self.__port = port_queue.get()

        except Exception:
            listener.dispose()
            raise

        finally:
            if self.__port is None:
                if self.__osl_process is not None:
                    self.__osl_process.terminate()
                    self.__osl_process = None
                    raise RuntimeError("Cannot get optiSLang server port.")

        listener.refresh_listener_registration = True
        self.__listeners["main_listener"] = listener
        self.__start_listeners_registration_thread()

    def __cast_to_path(self, file_path: Union[str, Path]) -> Path:
        """Cast path to Path."""
        if isinstance(file_path, Path):
            return file_path
        else:
            return Path(file_path)

    def __create_listener(
        self,
        timeout: float,
        name: str,
        uid: Optional[str] = None,
        notifications: Optional[List[ServerNotification]] = None,
    ) -> TcpOslListener:
        """Create new listener.

        Parameters
        ----------
        timeout: float
            Timeout.
        Uid: Optional[str], optional
            Listener uid. Defaults to ``None``.
        notifications: Optional[Iterable[ServerNotification]], optional
            Notifications to subscribe to.
            Either ["ALL"] or Sequence picked from below options:
            Server: [ "SERVER_UP", "SERVER_DOWN" ] (always be sent by default).
            Logging: [ "LOG_INFO", "LOG_WARNING", "LOG_ERROR", "LOG_DEBUG" ].
            Project: [ "EXECUTION_STARTED", "PROCESSING_STARTED", "EXECUTION_FINISHED",
                "NOTHING_PROCESSED", "CHECK_FAILED", "EXEC_FAILED" ].
            Nodes: [ "ACTOR_STATE_CHANGED", "ACTOR_ACTIVE_CHANGED", "ACTOR_NAME_CHANGED",
                "ACTOR_CONTENTS_CHANGED", "ACTOR_DATA_CHANGED" ].
            Defaults to ``None``.

        Returns
        -------
        TcpOslListener
            Listener ready to be registered to optiSLang server.

        Raises
        ------
        RuntimeError
            Raised when the optiSLang server is already started.
            -or-
            Port listener cannot be started.
            -or-
            optiSLang server port is not listened for specified timeout value.
        """
        listener = TcpOslListener(
            port_range=self._PRIVATE_PORTS_RANGE,
            timeout=timeout,
            name=name,
            uid=uid,
            logger=self._logger,
            notifications=notifications,
        )

        if not listener.is_initialized():
            raise RuntimeError("Cannot start listener of optiSLang server port.")

        return listener

    def __create_exec_started_listener(self, timeout: Optional[float] = None) -> TcpOslListener:
        """Create exec_started listener and add to self.__listeners.

        Returns
        -------
        exec_started_listener: TcpOslListener
            Listener registered to the optiSLang server and subscribed
            for push notifications.
        timeout: Optional[float], optional
            Listener's timeout.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        exec_started_listener = self.__create_listener(
            timeout=timeout,
            name="ExecStarted",
            notifications=[
                ServerNotification.PROCESSING_STARTED,
                ServerNotification.NOTHING_PROCESSED,
                ServerNotification.EXEC_FAILED,
                ServerNotification.CHECK_FAILED,
            ],
        )
        exec_started_listener.uid = self.__register_listener(
            host_addresses=exec_started_listener.host_addresses,
            port=exec_started_listener.port,
            timeout=self.__listeners_default_timeout,
            notifications=exec_started_listener.notifications,
        )
        exec_started_listener.refresh_listener_registration = True
        self.__listeners["exec_started_listener"] = exec_started_listener
        return exec_started_listener

    def __create_exec_finished_listener(self, timeout: Optional[float] = None) -> TcpOslListener:
        """Create exec_finished listener and add to self.__listeners.

        Returns
        -------
        exec_finished_listener: TcpOslListener
            Listener registered to the optiSLang server and subscribed
            for push notifications.
        timeout: Optional[float], optional
            Listener's timeout.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        exec_finished_listener = self.__create_listener(
            timeout=timeout,
            name="ExecFinished",
            notifications=[
                ServerNotification.EXECUTION_FINISHED,
                ServerNotification.NOTHING_PROCESSED,
                ServerNotification.EXEC_FAILED,
                ServerNotification.CHECK_FAILED,
            ],
        )
        exec_finished_listener.uid = self.__register_listener(
            host_addresses=exec_finished_listener.host_addresses,
            port=exec_finished_listener.port,
            timeout=self.__listeners_default_timeout,
            notifications=exec_finished_listener.notifications,
        )
        exec_finished_listener.refresh_listener_registration = True
        self.__listeners["exec_finished_listener"] = exec_finished_listener
        return exec_finished_listener

    def __delete_exec_started_listener(self) -> None:
        """Terminate ExecStarted listener and remove from active listeners dict."""
        exec_started_listener: TcpOslListener = self.__listeners["exec_started_listener"]
        exec_started_listener.refresh_listener_registration = False
        self._unregister_listener(exec_started_listener)
        self.__listeners.pop("exec_started_listener")
        del exec_started_listener

    def __delete_exec_finished_listener(self) -> None:
        """Terminate ExecFinished listener and remove from active listeners dict."""
        exec_finished_listener: TcpOslListener = self.__listeners["exec_finished_listener"]
        exec_finished_listener.refresh_listener_registration = False
        self._unregister_listener(exec_finished_listener)
        self.__listeners.pop("exec_finished_listener")
        del exec_finished_listener

    def __dispose_all_listeners(self) -> None:
        """Dispose all listeners."""
        for listener in self.__listeners.values():
            listener.dispose()
        self.__listeners = {}

    def __get_project_status(self) -> Optional[str]:
        """Get status of the optiSLang project.

        Returns
        -------
        Optional[str]
            optiSLang project status. If no project is loaded in the optiSLang,
            returns ``None``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        project_info = self.get_basic_project_info()
        if len(project_info.get("projects", [])) == 0:
            return None
        return project_info.get("projects", [{}])[0].get("state", None)

    def __register_listener(
        self,
        host_addresses: Iterable[str],
        port: int,
        timeout: int = 60000,
        explicit_listener_id: Optional[str] = None,
        notifications: Optional[List[ServerNotification]] = None,
    ) -> str:
        """Register a client, returning a reference ID.

        Parameters
        ----------
        host_addresses: Iterable[str]
            String representations of IPv4/v6 addresses.
        port: int
            A numeric port number of listener.
        timeout: float
            Listener will remain active for ``timeout`` ms unless refreshed.
        explicit_listener_id: Optional[str], optional
            Explicitly requested listener ID.
            Defaults to ``None``.
        notifications: Optional[Iterable[ServerNotification]], optional
            Notifications to subscribe to.
            Either ["ALL"] or Sequence picked from below options:
            Server: [ "SERVER_UP", "SERVER_DOWN" ] (always be sent by default).
            Logging: [ "LOG_INFO", "LOG_WARNING", "LOG_ERROR", "LOG_DEBUG" ].
            Project: [ "EXECUTION_STARTED", "PROCESSING_STARTED", "EXECUTION_FINISHED",
                "NOTHING_PROCESSED", "CHECK_FAILED", "EXEC_FAILED" ].
            Nodes: [ "ACTOR_STATE_CHANGED", "ACTOR_ACTIVE_CHANGED", "ACTOR_NAME_CHANGED",
                "ACTOR_CONTENTS_CHANGED", "ACTOR_DATA_CHANGED" ].
            Defaults to ``None``.

        Returns
        -------
        str
            Uid of registered listener created by optiSLang server.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        current_func_name = self.__register_listener.__name__
        listener_id = (
            explicit_listener_id
            if explicit_listener_id is not None
            else self.__listener_id if self.__listener_id is not None else str(uuid.uuid4())
        )
        notification_names = None
        if notifications is not None:
            notification_names = [ntf.name for ntf in notifications]

        for host_address in host_addresses:
            self.send_command(
                command=commands.register_listener(
                    host=host_address,
                    port=port,
                    timeout=timeout,
                    notifications=notification_names,
                    password=self.__password,
                    listener_uid=listener_id,
                ),
                timeout=self.timeouts_register.get_value(current_func_name),
                max_request_attempts=self.max_request_attempts_register.get_value(
                    current_func_name
                ),
            )
        return listener_id

    def __refresh_listeners_registration(self) -> None:  # pragma: no cover
        """Refresh listeners registration.

        Raises
        ------
        RuntimeError
            Raised when the optiSLang server is not started.
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout expires.
        """
        check_for_refresh = 0.5
        counter = 0.0
        current_func_name = self.__refresh_listeners_registration.__name__
        while not self.__refresh_listeners_stopped.is_set():
            if counter >= self.__listeners_refresh_interval:
                for listener in self.__listeners.values():
                    if listener.refresh_listener_registration:
                        try:
                            self._logger.debug(
                                "Refreshing registration for listener: %s", listener.uid
                            )
                            self.send_command(
                                commands.refresh_listener_registration(
                                    uid=listener.uid, password=self.__password
                                ),
                                timeout=self.timeouts_register.get_value(current_func_name),
                                max_request_attempts=self.max_request_attempts_register.get_value(
                                    current_func_name
                                ),
                            )
                        except OslCommandError as e:
                            self._logger.debug(
                                "Refreshing registration for listener %s failed: %s",
                                listener.uid,
                                str(e),
                            )
                            if "No such listener" in str(e):
                                self._logger.debug("Re-register listener: %s", listener.uid)
                                try:
                                    # re-register the listener
                                    listener.uid = self.__register_listener(
                                        host_addresses=listener.host_addresses,
                                        port=listener.port,
                                        timeout=self.__listeners_default_timeout,
                                        explicit_listener_id=listener.uid,
                                        notifications=listener.notifications,
                                    )
                                except Exception as e:
                                    self._logger.debug(
                                        "Re-registering listener %s failed: %s",
                                        listener.uid,
                                        str(e),
                                    )
                counter = 0
            counter += check_for_refresh
            self.__refresh_listeners_stopped.wait(check_for_refresh)
        self._logger.debug("Stop refreshing listener registration, self.__refresh = False")

    def __signal_handler(self, signum, frame):
        self._logger.error("Interrupt from keyboard (CTRL + C), terminating execution.")
        self.dispose()
        raise KeyboardInterrupt

    def __start_listeners_registration_thread(self) -> None:
        """Create new thread for refreshing of listeners registrations and start it."""
        self.__listeners_registration_thread = threading.Thread(
            target=self.__refresh_listeners_registration,
            name="PyOptiSLang.ListenersRegistrationThread",
            args=(),
            daemon=True,
        )
        self.__refresh_listeners_stopped.clear()
        self.__listeners_registration_thread.start()

    def __stop_listeners_registration_thread(self) -> None:
        """Stop listeners registration thread."""
        if (
            self.__listeners_registration_thread is not None
            and self.__listeners_registration_thread.is_alive()
        ):
            self.__refresh_listeners_stopped.set()
            self.__listeners_registration_thread.join()
            self._logger.debug("Listener registration thread stopped.")

    def __unregister_all_listeners(self) -> None:
        """Unregister all instance listeners."""
        for listener in self.__listeners.values():
            if listener.uid is not None:
                try:
                    self._unregister_listener(listener)
                except Exception as ex:
                    self._logger.warning("Cannot unregister port listener: %s", ex)

    def __validate_path(self, file_path: Path) -> None:
        """Check type and suffix of project_file path."""
        if not isinstance(file_path, Path):
            raise TypeError(
                f'Invalid type of project_path: "{type(file_path)}", "pathlib.Path" is supported.'
            )
        if not file_path.suffix == ".opf":
            raise ValueError('Invalid optiSLang project file, project must end with ".opf".')

    # To be fixed in 2023R2:
    # close method doesn't work properly in optiSLang 2023R1, therefore it was commented out
    # def close(self) -> None:
    #     """Close the current project.

    #     Raises
    #     ------
    #     OslCommunicationError
    #         Raised when an error occurs while communicating with server.
    #     OslCommandError
    #         Raised when the command or query fails.
    #     TimeoutError
    #         Raised when the timeout float value expires.
    #     """
    #     self.send_command(commands.close(password=self.__password))

    # stop_gently method doesn't work properly in optiSLang 2023R1, therefore it was commented out
    # def stop_gently(self, wait_for_finished: bool = True) -> None:
    #     """Stop project execution after the current design is finished.

    #     Parameters
    #     ----------
    #     wait_for_finished : bool, optional
    #         Determines whether this function call should wait on the optiSlang to finish
    #         the command execution. I.e. don't continue on next line of python script after command
    #         was successfully sent to optiSLang but wait for execution of command inside optiSLang.
    #         Defaults to ``True``.

    #     Raises
    #     ------
    #     OslCommunicationError
    #         Raised when an error occurs while communicating with server.
    #     OslCommandError
    #         Raised when the command or query fails.
    #     TimeoutError
    #         Raised when the timeout float value expires.
    #     """
    #     if wait_for_finished:
    #         exec_finished_listener = self.__create_exec_finished_listener()
    #         exec_finished_listener.cleanup_notifications()
    #         wait_for_finished_queue = Queue()
    #         exec_finished_listener.add_callback(
    #             self.__class__.__terminate_listener_thread,
    #             (
    #                 [
    #                     ServerNotification.EXECUTION_FINISHED.name,
    #                     ServerNotification.NOTHING_PROCESSED.name,
    #                 ],
    #                 wait_for_finished_queue,
    #                 self._logger,
    #             ),
    #         )
    #         exec_finished_listener.start_listening()
    #         self._logger.debug("Wait for finished thread was created.")

    #     status = self.get_project_status()

    #     # do not send stop_gently request if project is already stopped or request
    #     # with higher or equal priority was already sent
    #     if status in self._STOPPED_STATES:
    #         self._logger.debug(f"Do not send STOP request, project status is: {status}")
    #         if wait_for_finished:
    #             exec_finished_listener.stop_listening()
    #             exec_finished_listener.clear_callbacks()
    #             self.__delete_exec_finished_listener()
    #         return
    #     elif status in self._STOP_REQUESTS_PRIORITIES:
    #         stop_request_priority = self._STOP_REQUESTS_PRIORITIES["STOP_GENTLY"]
    #         current_status_priority = self._STOP_REQUESTED_STATES_PRIORITIES[status]
    #         if stop_request_priority > current_status_priority:
    #             self.send_command(commands.stop(self.__password))
    #         else:
    #             self._logger.debug(f"Do not send STOP request, project status is: {status}")
    #     else:
    #         self.send_command(commands.stop(self.__password))

    #     if wait_for_finished:
    #         self._logger.info(f"Waiting for finished")
    #         successfully_finished = wait_for_finished_queue.get()
    #         self.__delete_exec_finished_listener()
    #         if successfully_finished == "Terminate":
    #             raise TimeoutError("Waiting for finished timed out.")
    #         self._logger.info(f"Successfully_finished: {successfully_finished}.")

    @staticmethod
    def __check_command_response(response: Dict) -> None:
        """Check whether the server response for a sent command contains any failure information.

        Parameters
        ----------
        response : Dict
            Server response as dictionary.

        Raises
        ------
        OslCommandError
            Raised when the server response for the sent command contains any failure information.
        """
        if "status" in response and response["status"].lower() == "failure":
            message = None
            if "message" in response:
                message = response["message"]
            if "std_err" in response:
                message += "; " + response["std_err"]
            if message is None:
                message = "Command error: " + str(response)
            raise OslCommandError(message)

    def __get_default_max_request_attempts_register(self) -> FunctionsAttributeRegister:
        max_requests_register = FunctionsAttributeRegister(
            default_value=2, validator=self.__class__.__validate_max_request_attempts_value
        )
        max_requests_register.register(self.__class__.evaluate_design, 1)
        max_requests_register.register(self.__class__.get_full_project_status_info, 1)
        max_requests_register.register(self.__class__.open, 1)
        max_requests_register.register(self.__class__.reset, 1)
        max_requests_register.register(self.__class__.run_python_script, 1)
        max_requests_register.register(self.__class__.save, 1)
        max_requests_register.register(self.__class__.save_as, 1)
        max_requests_register.register(self.__class__.save_copy, 1)
        max_requests_register.register(self.__class__.start, 1)
        max_requests_register.register(self.__class__.stop, 1)
        return max_requests_register

    def __get_default_timeouts_register(self) -> FunctionsAttributeRegister:
        timeout_register = FunctionsAttributeRegister(
            default_value=30, validator=self.__class__.__validate_timeout_value
        )
        timeout_register.register(self.__class__.evaluate_design, None)
        timeout_register.register(self.__class__.get_full_project_status_info, None)
        timeout_register.register(self.__class__.open, None)
        timeout_register.register(self.__class__.reset, None)
        timeout_register.register(self.__class__.run_python_script, None)
        timeout_register.register(self.__class__.save, None)
        timeout_register.register(self.__class__.save_as, None)
        timeout_register.register(self.__class__.save_copy, None)
        timeout_register.register(self.__class__.start, None)
        timeout_register.register(self.__class__.stop, None)
        return timeout_register

    @staticmethod
    def __port_on_listended(
        sender: TcpOslListener, response: dict, port_queue: Queue, logger
    ) -> None:
        """Listen to the optiSLang server port."""
        try:
            if "port" in response:
                port = int(response["port"])
                port_queue.put(port)
                sender.stop_listening()
                sender.clear_callbacks()
        except:
            logger.debug("Port cannot be received from response: %s", str(response))

    @staticmethod
    def __terminate_listener_thread(
        sender: TcpOslListener,
        response: dict,
        target_notifications: List[str],
        target_queue: Queue,
        logger: logging.Logger,
    ) -> None:
        """Terminate listener thread if execution finished or failed."""
        type = response.get("type", None)
        if type is not None:
            sender.stop_listening()
            sender.clear_callbacks()
            sender.refresh_listener_registration = False
            if type in [ServerNotification.EXEC_FAILED.name, ServerNotification.CHECK_FAILED.name]:
                target_queue.put(False)
                logger.error(f"Listener {sender.name} received error notification.")
            elif type in target_notifications:
                target_queue.put(True)
                logger.debug(f"Listener {sender.name} received expected notification.")
            elif type == "TimeoutError":
                target_queue.put("Terminate")
                logger.error(f"Listener {sender.name} timed out.")
        else:
            logger.error("Invalid response from server, push notification not evaluated.")

    @staticmethod
    def __validate_timeout_value(value: Any) -> bool:
        return value is None or (
            isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
        )

    @staticmethod
    def __validate_max_request_attempts_value(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

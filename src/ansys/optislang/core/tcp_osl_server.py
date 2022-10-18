"""Contains classes for plain TCP/IP communication with server."""
from datetime import datetime
import json
import logging
import os
from queue import Queue
import select
import socket
import struct
import threading
import time
from typing import Callable, Dict, List, Sequence, Tuple, Union
import uuid

from ansys.optislang.core import server_commands as commands
from ansys.optislang.core import server_queries as queries
from ansys.optislang.core.encoding import force_bytes, force_text
from ansys.optislang.core.errors import (
    ConnectionEstablishedError,
    ConnectionNotEstablishedError,
    EmptyResponseError,
    OslCommandError,
    OslCommunicationError,
    ResponseFormatError,
)
from ansys.optislang.core.osl_process import OslServerProcess, ServerNotification
from ansys.optislang.core.osl_server import OslServer


def _get_current_timeout(initial_timeout: Union[float, None], start_time: float) -> None:
    """Get actual timeout value.

    The function will raise a timeout exception if the timeout has expired.

    Parameters
    ----------
    initial_timeout : float, None
        Initial timeout value. For non-zero value, the new timeout value is computed.
        If the timeout period value has elapsed, the timeout exception is raised.
        For zero value, the non-blocking mode is assumed and zero value is returned.
        For ``None``, the blocking mode is assumed and ``None`` is returned.
    start_time : float
        The time when the initial time out starts to count down. It is defined in seconds
        since the epoch as a floating point number.

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


class TcpClient:
    r"""Client of the plain TCP/IP communication.

    Parameters
    ----------
    socket: socket.SocketType, None, optional
        Client socket.
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

    _BUFFER_SIZE = pow(2, 12)
    # Response size in bytes. Value is assumed to be binary 64Bit unsigned integer.
    _RESPONSE_SIZE_BYTES = 8

    def __init__(self, socket: Union[socket.SocketType, None] = None, logger=None) -> None:
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

    def connect(self, host: str, port: int, timeout: Union[float, None] = 2) -> None:
        """Connect to the plain TCP/IP server.

        Parameters
        ----------
        host : str
            A string representation of an IPv4/v6 address or domain name.
        port : int
            A numeric port number.
        timeout : Union[float, None], optional
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
        if self.is_connected:
            raise ConnectionEstablishedError("Connection is already established.")

        start_time = time.time()

        for af, socktype, proto, canonname, sa in socket.getaddrinfo(
            host, port, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE
        ):
            try:
                self.__socket = socket.socket(af, socktype, proto)
            except OSError as ex:
                self.__socket = None
                continue
            self.__socket.settimeout(_get_current_timeout(timeout, start_time))
            try:
                self.__socket.connect(sa)
            except OSError:
                self.__socket.close()
                self.__socket = None
                continue

        if self.__socket is None:
            raise ConnectionRefusedError(
                f"Connection could not be established to host {host} and port {port}."
            )

        self._logger.debug("Connection has been established to host %s and port %d.", host, port)

    def disconnect(self) -> None:
        """Disconnect from the server."""
        if self.is_connected:
            self.__socket.close()
            self.__socket = None

    def send_msg(self, msg: str, timeout: Union[float, None] = 5) -> None:
        """Send message to the server.

        Parameters
        ----------
        msg : str
            Message to send.
        timeout : Union[float, None], optional
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
        if not self.is_connected:
            raise ConnectionNotEstablishedError(
                "Cannot send message. Connection is not established."
            )

        self._logger.debug("Sending message to %s. Message: %s", self.__socket.getpeername(), msg)
        data = force_bytes(msg)
        data_len = len(data)

        header = struct.pack("!QQ", data_len, data_len)

        self.__socket.settimeout(timeout)
        self.__socket.sendall(header + data)

    def send_file(self, file_path: str, timeout: Union[float, None] = 5) -> None:
        """Send content of the file to the server.

        Parameters
        ----------
        file_path : str
            Path to the file whose content is to be sent to the server.
        timeout : Union[float, None], optional
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
        if not self.is_connected:
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
            load = file.read(self.__class__._BUFFER_SIZE)
            while load:
                self.__socket.send(load)
                load = file.read(self.__class__._BUFFER_SIZE)

    def receive_msg(self, timeout: Union[float, None] = 5) -> str:
        """Receive message from the server.

        Parameters
        ----------
        timeout : Union[float, None], optional
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
        if not self.is_connected:
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

    def receive_file(self, file_path: str, timeout: Union[float, None] = 5) -> None:
        """Receive file from the server.

        Parameters
        ----------
        file_path : str
            Path where the received file is to be saved.
        timeout : Union[float, None], optional
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
        if not self.is_connected:
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

    def _recv_response_length(self, timeout: Union[float, None]) -> int:
        """Receive length of the response.

        Parameters
        ----------
        timeout : Union[float, None], optional
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

        start_time = time.time()
        self.__socket.settimeout(timeout)

        response_len = -1
        bytes_to_receive = self.__class__._RESPONSE_SIZE_BYTES
        # read from socket until response size (twice) has been received
        while True:
            try:
                # Test if we will be able to read something from the connection.
                readable_sockets, _, _ = select.select([self.__socket], [], [], 1)
                if self.__socket in readable_sockets:
                    # Read and convert response size. Assume server sent response size twice.
                    # Sizes need to match.
                    response_len_1 = struct.unpack("!Q", self.__socket.recv(bytes_to_receive))[0]
                    response_len_2 = struct.unpack("!Q", self.__socket.recv(bytes_to_receive))[0]
                    if response_len_1 != response_len_2:
                        raise ResponseFormatError("The message size values do not match.")

                    response_len = response_len_1
                if response_len >= 0:
                    break
            except Exception as e:
                self._logger.debug(e)
                pass
            now = time.time()
            elapsed = now - start_time
            if timeout is not None and elapsed > timeout:
                raise TimeoutError("Time to receive message length has expired.")

        return response_len

    def _receive_bytes(self, count: int, timeout: Union[float, None]) -> bytes:
        """Receive specified number of bytes from the server.

        Parameters
        ----------
        count : int
            Number of bytes to be received from the server.
        timeout : Union[float, None], optional
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

        start_time = time.time()

        received = b""
        received_len = 0
        while received_len < count:
            remain = count - received_len
            if remain > self.__class__._BUFFER_SIZE:
                buff = self.__class__._BUFFER_SIZE
            else:
                buff = remain

            self.__socket.settimeout(_get_current_timeout(timeout, start_time))
            chunk = self.__socket.recv(buff)
            if not chunk:
                break
            received += chunk
            received_len += len(chunk)
        return received

    def _fetch_file(self, file_len: int, file_path: str, timeout: Union[float, None]) -> None:
        """Write received bytes from the server to the file.

        Parameters
        ----------
        file_len : int
            Number of bytes to be written.
        file_path : str
            Path to the file to which the received data is to be written.
        timeout : Union[float, None], optional
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

        start_time = time.time()

        with open(file_path, "wb") as file:
            data_len = 0
            while data_len < file_len:
                remain = file_len - data_len
                if remain > self.__class__._BUFFER_SIZE:
                    buff = self.__class__._BUFFER_SIZE
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
        host: str
            Local IPv6 address.
        uid: str, optional
            Unique ID of listener, should be used only if listener is used for optiSLangs port
            when started locally.
        logger: OslLogger, optional
            Preferably OslLogger should be given. If not given, default logging.Logger is used.

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
    >>>     port_range = self.__class__._PRIVATE_PORTS_RANGE,
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
        host: str = None,
        uid: str = None,
        logger=None,
    ):
        """Initialize a new instance of the ``TcpOslListener`` class."""
        self.__uid = uid
        self.__name = name
        self.__timeout = timeout
        self.__listener_socket = None
        self.__thread = None
        self.__callbacks = []
        self.__run_listening_thread = False

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

        self.__init_listener_socket(host=host, port_range=port_range)

    def is_initialized(self) -> bool:
        """Return True if listener was initialized."""
        return self.__listener_socket is not None

    def dispose(self) -> None:
        """Delete listeners socket if exists."""
        if self.__listener_socket is not None:
            self.__listener_socket.close()

    @property
    def uid(self) -> str:
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
    def timeout(self) -> Union[float, None]:
        """Timeout in seconds to receive a message."""
        return self.__timeout

    @timeout.setter
    def timeout(self, timeout) -> None:
        self.__timeout = timeout

    @property
    def host(self) -> str:
        """Local IPv6 address associated with self.__listener_socket."""
        return self.__listener_socket.getsockname()[0]

    @property
    def port(self) -> int:
        """Port number associated with self.__listener_socket."""
        return self.__listener_socket.getsockname()[1]

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

    # def remove_callback(self, callback: Callable):
    #     self.__callbacks.remove(callback)

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

            except TimeoutError or socket.timeout:
                self._logger.warning(f"Listener {self.uid} listening timed out.")
                self.stop_listening()
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

    def is_listening(self) -> None:
        """Return True if listener is listening."""
        return self.is_initialized() and self.__thread is not None and self.__thread.is_alive()

    def join(self) -> None:
        """Wait until self.__thread is finished."""
        if not self.is_listening():
            raise RuntimeError("Listener is not listening.")
        self.__thread.join()

    def cleanup_notifications(self, timeout: float = 0.2) -> None:
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
                break
            except Exception as ex:
                self._logger.warning(ex)
            finally:
                if client is not None:
                    client.disconnect()


class TcpOslServer(OslServer):
    """Class which provides access to optiSLang server using plain TCP/IP communication protocol.

    For remote connection, it is assumed that the optiSLang server process is already running
    on remote (or local) host. In that case, the host and port must be specified and other
    parameters are ignored.

    Parameters
    ----------
    host : str, optional
        A string representation of an IPv4/v6 address or domain name of running optiSLang server.
        Defaults to ``None``.
    port : int, optional
        A numeric port number of running optiSLang server. Defaults to ``None``.
    executable : str, optional
        Path to the optiSLang executable file which supposed to be executed on localhost.
        It is ignored when the host and port parameters are specified. Defaults to ``None``.
    project_path : str, optional
        Path to the optiSLang project file which is supposed to be used by new local optiSLang
        server. It is ignored when the host and port parameters are specified.
        - If the project file exists, it is opened.
        - If the project file does not exist, a new project is created on the specified path.
        - If the path is None, a new project is created in the temporary directory.
        Defaults to ``None``.
    no_save : bool, optional
        Determines whether not to save the specified project after all other actions are completed.
        It is ignored when the host and port parameters are specified. Defaults to ``False``.
    ini_timeout : float, optional
        Time in seconds to listen to the optiSLang server port. If the port is not listened
        for specified time, the optiSLang server is not started and RuntimeError is raised.
        It is ignored when the host and port parameters are specified. Defaults to 20 s.
    password : str, optional
        The server password. Use when communication with the server requires the request
        to contain a password entry. Defaults to ``None``.
    logger : Any, optional
        Object for logging. If ``None``, standard logging object is used. Defaults to ``None``.
    shutdown_on_finished: bool, optional
        Shut down when execution is finished and there are not any listeners registered.
        It is ignored when the host and port parameters are specified. Defaults to ``True``.

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
    >>> osl_version = osl_server.get_osl_version()
    >>> print(osl_version)
    >>> osl_server.shutdown()

    Connect to the remote optiSLang server, get optiSLang version and shutdown the server.
    >>> from ansys.optislang.core.tcp_osl_server import TcpOslServer
    >>> host = "192.168.101.1"  # IP address of the remote host
    >>> port = 49200            # Port of the remote optiSLang server
    >>> osl_server = TcpOslServer(host, port)
    >>> osl_version = osl_server.get_osl_version()
    >>> print(osl_version)
    >>> osl_server.shutdown()
    """

    _LOCALHOST = "127.0.0.1"
    _PRIVATE_PORTS_RANGE = (49152, 65535)
    _SHUTDOWN_WAIT = 5  # wait for local server to shutdown in second

    def __init__(
        self,
        host: str = None,
        port: int = None,
        executable: str = None,
        project_path: str = None,
        no_save: bool = False,
        ini_timeout: float = 20,
        password: str = None,
        logger=None,
        shutdown_on_finished=True,
    ) -> None:
        """Initialize a new instance of the ``TcpOslServer`` class."""
        self.__host = host
        self.__port = port
        self.__timeout = None
        self.__executable = executable

        if logger is None:
            self._logger = logging.getLogger(__name__)
        else:
            self._logger = logger

        self.__project_path = project_path
        self.__no_save = no_save
        self.__password = password
        self.__osl_process = None
        self.__listeners = {}
        self.__listeners_registration_thread = None
        self.__refresh_listeners = threading.Event()
        self.__listeners_refresh_interval = 20

        if self.__host is None or self.__port is None:
            self.__host = self.__class__._LOCALHOST
            self._start_local(ini_timeout, shutdown_on_finished)
        else:
            listener = self.__create_listener(
                timeout=self.__timeout,
                name="Main",
            )
            listener.uid = self.__register_listener(
                host=listener.host,
                port=listener.port,
                notifications=[ServerNotification.ALL],
            )
            self.__listeners["main"] = listener
            self.__start_listeners_registration_thread()

    def _get_server_info(self) -> Dict:
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
        return self._send_command(queries.server_info())

    def _get_basic_project_info(self) -> Dict:
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
        return self._send_command(queries.basic_project_info())

    def close(self) -> None:
        """Close the current project.

        Raises
        ------
        NotImplementedError
            Currently, command is not supported in batch mode.
        """
        raise NotImplementedError("Currently, command is not supported in batch mode.")

    def get_osl_version(self) -> str:
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
        server_info = self._get_server_info()
        return server_info["application"]["version"]

    def get_project_description(self) -> str:
        """Get description of optiSLang project.

        Returns
        -------
        str
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
        project_info = self._get_basic_project_info()
        if len(project_info["projects"]) == 0:
            return None
        return project_info["projects"][0]["settings"]["short_description"]

    def get_project_location(self) -> str:
        """Get path to the optiSLang project file.

        Returns
        -------
        str
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
        project_info = self._get_basic_project_info()
        if len(project_info["projects"]) == 0:
            return None
        return project_info["projects"][0]["location"]

    def get_project_name(self) -> str:
        """Get name of the optiSLang project.

        Returns
        -------
        str
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
        project_info = self._get_basic_project_info()
        if len(project_info["projects"]) == 0:
            return None
        return project_info["projects"][0]["name"]

    def get_project_status(self) -> str:
        """Get status of the optiSLang project.

        Returns
        -------
        str
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
        project_info = self._get_basic_project_info()
        if len(project_info["projects"]) == 0:
            return None
        return project_info["projects"][0]["state"]

    def get_timeout(self) -> Union[float, None]:
        """Get current timeout value for execution of commands.

        Returns
        -------
        timeout: Union[float, None]
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
        return self.__timeout

    def get_working_dir(self) -> str:
        """Get path to the optiSLang project working directory.

        Returns
        -------
        str
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
        project_info = self._get_basic_project_info()
        if len(project_info["projects"]) == 0:
            return None
        return project_info["projects"][0]["working_dir"]

    def new(self) -> None:
        """Create a new project.

        Parameters
        ----------
        timeout : float, None, optional
            Timeout in seconds to perform the command. It must be greater than zero or ``None``.
            The function will raise a timeout exception if the timeout period value has
            elapsed before the operation has completed. If ``None`` is given, the function
            will wait until the function is finished (no timeout exception is raised).
            Defaults to ``None``.

        Raises
        ------
        NotImplementedError
            Currently, command is not supported in batch mode.
        """
        raise NotImplementedError("Currently, command is not supported in batch mode.")

    def open(
        self,
        file_path: str,
        force: bool,
        restore: bool,
        reset: bool,
    ) -> None:
        """Open a new project.

        Parameters
        ----------
        file_path : str
            Path to the optiSLang project file to open.
        force : bool
            # TODO: description of this parameter is missing in ANSYS help
        restore : bool
            # TODO: description of this parameter is missing in ANSYS help
        reset : bool
            # TODO: description of this parameter is missing in ANSYS help
        timeout : float, None, optional
            Timeout in seconds to perform the command. It must be greater than zero or ``None``.
            The function will raise a timeout exception if the timeout period value has
            elapsed before the operation has completed. If ``None`` is given, the function
            will wait until the function is finished (no timeout exception is raised).
            Defaults to ``None``.

        Raises
        ------
        NotImplementedError
            Currently, command is not supported in batch mode.
        """
        raise NotImplementedError("Currently, command is not supported in batch mode.")

    def reset(self):
        """Reset complete project.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        TimeoutError
            Raised when the timeout float value expires.
        """
        self._send_command(commands.reset(password=self.__password))

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
        responses = self._send_command(commands.run_python_script(script, args, self.__password))
        std_out = ""
        std_err = ""
        for response in responses:
            std_out += response.get("std_out", "")
            std_err += response.get("std_err", "")

        return (std_out, std_err)

    def run_python_file(
        self,
        file_path: str,
        args: Union[Sequence[object], None] = None,
    ) -> Tuple[str, str]:
        """Read python script from the file, load it in a project context and execute it.

        Parameters
        ----------
        file_path : str
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
        NotImplementedError
            Currently, command is not supported in batch mode.
        """
        raise NotImplementedError("Currently, command is not supported in batch mode.")

    def save_as(
        self,
        file_path: str,
        force: bool,
        restore: bool,
        reset: bool,
    ) -> None:
        """Save and open the current project at a new location.

        Parameters
        ----------
        file_path : str
            Path where to save the project file.
        force : bool
            # TODO: description of this parameter is missing in ANSYS help
        restore : bool
            # TODO: description of this parameter is missing in ANSYS help
        reset : bool
            # TODO: description of this parameter is missing in ANSYS help

        Raises
        ------
        NotImplementedError
            Currently, command is not supported in batch mode.
        """
        raise NotImplementedError("Currently, command is not supported in batch mode.")

    def save_copy(self, file_path: str) -> None:
        """Save the current project as a copy to a location.

        Parameters
        ----------
        file_path : str
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
        self._send_command(commands.save_copy(file_path, self.__password))

    def set_timeout(self, timeout: Union[float, None] = None) -> None:
        """Set timeout value for execution of commands.

        Parameters
        ----------
        timeout: Union[float, None]
            Timeout in seconds to perform commands, it must be greater than zero or ``None``.
            Another functions will raise a timeout exception if the timeout period value has
            elapsed before the operation has completed.
            If ``None`` is given, functions will wait until they're finished (no timeout
            exception is raised). Defaults to ``None``.

        Raises
        ------
        OslCommunicationError
            Raised when an error occurs while communicating with server.
        OslCommandError
            Raised when the command or query fails.
        ValueError
            Raised when timeout <= 0.
        TypeError
            Raised when timeout not Union[float, None].
        """
        if timeout is None:
            self.__timeout = timeout
        elif isinstance(timeout, (int, float)):
            if timeout > 0:
                self.__timeout = timeout
            else:
                raise ValueError(
                    "Timeout must be float greater than zero or ``None`` but "
                    f"``{timeout}`` was given."
                )
        else:
            raise TypeError(
                "Invalid type of timeout, timeout must be float greater than zero or "
                f"``None`` but {type(timeout)} was given."
            )

        for listener in self.__listeners.values():
            listener.timeout = timeout

    def shutdown(self, force: bool = False) -> None:
        """Shutdown the server.

        Stop listening for incoming connections, discard pending requests, and shut down
        the server. Batch mode exclusive: Continue project run until execution finished.
        Terminate optiSLang.

        Parameters
        ----------
        force : bool, optional
            Determines whether to force shutdown the local optiSLang server. Has no effect when
            the connection is established to the remote optiSLang server. In all cases, it is tried
            to shutdown the optiSLang server process in a proper way. However, if the force
            parameter is ``True``, after a while, the process is forced to terminate and
            no exception is raised. Defaults to ``False``.

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
        self.__finish_all_threads()

        # Only in case shutdown_on_finished option is not set, actively send shutdown command
        if self.__osl_process is None or (
            self.__osl_process is not None and not self.__osl_process.shutdown_on_finished
        ):
            try:
                self._send_command(commands.shutdown(self.__password))
            except Exception:
                if not force or self.__osl_process is None:
                    raise

        # If desired actively force osl process to terminate
        if force and self.__osl_process is not None:
            self._force_shutdown_local_process()

    def _force_shutdown_local_process(self):
        """Force shutdown local optiSLang server process.

        It waits a while and then terminates the process.
        """
        start_time = datetime.now()
        while (
            self.__osl_process.is_running()
            and (datetime.now() - start_time).seconds < self.__class__._SHUTDOWN_WAIT
        ):
            time.sleep(0.5)

        if self.__osl_process.is_running():
            self.__osl_process.terminate()
        self.__osl_process = None
        self.__host = None
        self.__port = None

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

        if self.get_project_status() == "PROCESSING":
            already_running = True
            self._logger.debug("Status PROCESSING")

        if not already_running and (wait_for_started or wait_for_finished):
            exec_started_listener = self.__listeners.get("exec_started_listener", None)
            if exec_started_listener is None:
                exec_started_listener = self.__create_exec_started_listener()
            exec_started_listener.cleanup_notifications()
            wait_for_started_queue = Queue()
            exec_started_listener.add_callback(
                self.__class__.__terminate_listener_thread,
                (
                    [ServerNotification.EXECUTION_STARTED.name],
                    wait_for_started_queue,
                    self._logger,
                ),
            )
            exec_started_listener.start_listening()
            self._logger.debug("Wait for started thread was created.")

        if wait_for_finished:
            exec_finished_listener = self.__listeners.get("exec_finished_listener", None)
            if exec_finished_listener is None:
                exec_finished_listener = self.__create_exec_finished_listener()
            exec_finished_listener.cleanup_notifications()
            wait_for_finished_queue = Queue()
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
            self._send_command(commands.start(self.__password))

        if not already_running and (wait_for_started or wait_for_finished):
            self._logger.info(f"Waiting for started")
            successfully_started = wait_for_started_queue.get()
            self._logger.info(f"Successfully_started: {successfully_started}.")

        if wait_for_finished and (successfully_started or already_running):
            self._logger.info(f"Waiting for finished")
            successfully_finished = wait_for_finished_queue.get()
            self._logger.info(f"Successfully_finished: {successfully_finished}.")
        else:
            time.sleep(1)

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
        status = self.get_project_status()

        if not self._is_status_in_stopped_states(status):
            if wait_for_finished:
                exec_finished_listener = self.__listeners.get("exec_finished_listener", None)
                if exec_finished_listener is None:
                    exec_finished_listener = self.__create_exec_finished_listener()
                exec_finished_listener.cleanup_notifications()
                wait_for_finished_queue = Queue()
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

            self._send_command(commands.stop(self.__password))

            if wait_for_finished:
                self._logger.info(f"Waiting for finished")
                # exec_finished_listener.join()
                successfully_finished = wait_for_finished_queue.get()
                self._logger.info(f"Successfully_finished: {successfully_finished}.")
        else:
            self._logger.debug(f"Do not send STOP request, project status is: {status}")

    def stop_gently(self, wait_for_finished: bool = True) -> None:
        """Stop project execution after the current design is finished.

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
        status = self.get_project_status()

        if not self._is_status_in_stopped_states(status):
            if wait_for_finished:
                exec_finished_listener = self.__listeners.get("exec_finished_listener", None)
                if exec_finished_listener is None:
                    exec_finished_listener = self.__create_exec_finished_listener()
                exec_finished_listener.cleanup_notifications()
                wait_for_finished_queue = Queue()
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

            self._send_command(commands.stop_gently(self.__password))

            if wait_for_finished:
                self._logger.info(f"Waiting for finished")
                # exec_finished_listener.join()
                successfully_finished = wait_for_finished_queue.get()
                self._logger.info(f"Successfully_finished: {successfully_finished}.")
        else:
            self._logger.debug(f"Do not send STOP_GENTLY request, project status is: {status}")

    def _is_status_in_stopped_states(self, status: str) -> bool:
        """Compare current project status with list."""
        stopped_states = [
            "IDLE",
            "FINISHED",
            "STOP_REQUESTED",
            "STOPPED",
            "ABORT_REQUESTED",
            "ABORTED",
        ]
        return status in stopped_states

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
        self._send_command(commands.unregister_listener(str(listener.uid), self.__password))
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
            uid=str(uuid.uuid4()), timeout=self.__timeout, name="Main"
        )
        port_queue = Queue()
        listener.add_callback(self.__class__.__port_on_listended, (port_queue, self._logger))

        try:
            listener.start_listening(timeout=ini_timeout)

            self.__osl_process = OslServerProcess(
                executable=self.__executable,
                project_path=self.__project_path,
                no_save=self.__no_save,
                password=self.__password,
                listener=(listener.host, listener.port),
                listener_id=listener.uid,
                notifications=[ServerNotification.ALL],
                shutdown_on_finished=shutdown_on_finished,
                logger=self._logger,
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
                self.__osl_process.terminate()
                self.__osl_process = None
                raise RuntimeError("Cannot get optiSLang server port.")

        self.__listeners["main_listener"] = listener
        self.__start_listeners_registration_thread()

    def __create_listener(self, timeout: float, name: str, uid: str = None) -> TcpOslListener:
        """Create new listener.

        Parameters
        ----------
        timeout: float
            Timeout.
        Uid: str
            Listener uid.

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
            port_range=self.__class__._PRIVATE_PORTS_RANGE,
            timeout=timeout,
            name=name,
            host=self.__host,
            uid=uid,
            logger=self._logger,
        )

        if not listener.is_initialized():
            raise RuntimeError("Cannot start listener of optiSLang server port.")

        return listener

    def __create_exec_started_listener(self) -> TcpOslListener:
        """Create exec_started listener and add to self.__listeners.

        Returns
        -------
        exec_started_listener: TcpOslListener
            Listener registered to the optiSLang server and subscribed
            for push notifications.

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
            timeout=self.__timeout,
            name="ExecStarted",
        )
        exec_started_listener.uid = self.__register_listener(
            host=exec_started_listener.host,
            port=exec_started_listener.port,
            notifications=[
                ServerNotification.EXECUTION_STARTED,
                ServerNotification.EXEC_FAILED,
                ServerNotification.CHECK_FAILED,
            ],
        )
        self.__listeners["exec_started_listener"] = exec_started_listener
        return exec_started_listener

    def __create_exec_finished_listener(self) -> TcpOslListener:
        """Create exec_finished listener and add to self.__listeners.

        Returns
        -------
        exec_finished_listener: TcpOslListener
            Listener registered to the optiSLang server and subscribed
            for push notifications.

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
            timeout=self.__timeout,
            name="ExecFinished",
        )
        exec_finished_listener.uid = self.__register_listener(
            host=exec_finished_listener.host,
            port=exec_finished_listener.port,
            notifications=[
                ServerNotification.EXECUTION_FINISHED,
                ServerNotification.NOTHING_PROCESSED,
                ServerNotification.EXEC_FAILED,
                ServerNotification.CHECK_FAILED,
            ],
        )
        self.__listeners["exec_finished_listener"] = exec_finished_listener
        return exec_finished_listener

    def __start_listeners_registration_thread(self) -> None:
        """Create new thread for refreshing of listeners registrations and start it."""
        self.__listeners_registration_thread = threading.Thread(
            target=self.__refresh_listeners_registration,
            name="PyOptiSLang.ListenersRegistrationThread",
            args=(),
            daemon=True,
        )
        self.__refresh_listeners.set()
        self.__listeners_registration_thread.start()

    def __stop_listeners_registration_thread(self) -> None:
        """Stop listeners registration thread."""
        if self.__listeners_registration_thread and self.__listeners_registration_thread.is_alive():
            self.__refresh_listeners.clear()
            self.__listeners_registration_thread.join()
            self._logger.debug("Listener registration thread stopped.")

    def __register_listener(
        self,
        host: str,
        port: int,
        timeout: int = 60000,
        notifications: List[ServerNotification] = None,
    ) -> str:
        """Register a client, returning a reference ID.

        Parameters
        ----------
        host : str
            A string representation of an IPv4/v6 address or domain name.
        port: int
            A numeric port number of listener.
        timeout: float
            Listener will remain active for ``timeout`` ms unless refreshed.

        notifications: Iterable[ServerNotification], optional
            Either ["ALL"] or Sequence picked from below options:
            Server: [ "SERVER_UP", "SERVER_DOWN" ] (always be sent by default).
            Logging: [ "LOG_INFO", "LOG_WARNING", "LOG_ERROR", "LOG_DEBUG" ].
            Project: [ "EXECUTION_STARTED", "EXECUTION_FINISHED", "NOTHING_PROCESSED",
                "CHECK_FAILED", "EXEC_FAILED" ].
            Nodes: [ "ACTOR_STATE_CHANGED", "ACTOR_ACTIVE_CHANGED", "ACTOR_NAME_CHANGED",
                "ACTOR_CONTENTS_CHANGED", "ACTOR_DATA_CHANGED" ].

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
        msg = self._send_command(
            commands.register_listener(
                host=host,
                port=port,
                timeout=timeout,
                notifications=[ntf.name for ntf in notifications],
                password=self.__password,
            )
        )
        return msg[0]["uid"]

    def __refresh_listeners_registration(self) -> None:
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
        counter = 0
        while self.__refresh_listeners.is_set():
            if counter >= self.__listeners_refresh_interval:
                for listener in self.__listeners.values():
                    response = self._send_command(
                        commands.refresh_listener_registration(
                            uid=listener.uid, password=self.__password
                        )
                    )
                counter = 0
            counter += check_for_refresh
            time.sleep(check_for_refresh)
        self._logger.debug("Stop refreshing listener registration, self.__refresh = False")

    def __finish_all_threads(self) -> None:
        """Stop listeners registration and unregister them."""
        self.__stop_listeners_registration_thread()
        for listener in self.__listeners.values():
            if listener.uid is not None:
                try:
                    self._unregister_listener(listener)
                except Exception as ex:
                    self._logger.warn("Cannot unregister port listener: %s", ex)
            if listener.is_listening():
                listener.dispose()

    def _send_command(self, command: str) -> Dict:
        """Send command or query to the optiSLang server.

        Parameters
        ----------
        command : str
            Command or query to be executed on optiSLang server.

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
        if self.__host is None or self.__port is None:
            raise RuntimeError("optiSLang server is not started.")

        start_time = time.time()
        self._logger.debug("Sending command or query to the server: %s", command)
        client = TcpClient(logger=self._logger)
        try:
            client.connect(
                self.__host, self.__port, timeout=_get_current_timeout(self.__timeout, start_time)
            )
            client.send_msg(command, timeout=_get_current_timeout(self.__timeout, start_time))
            response_str = client.receive_msg(
                timeout=_get_current_timeout(self.__timeout, start_time)
            )

        except TimeoutError as ex:
            raise
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
                self.__class__.__check_command_response(resp_elem)
        else:
            self.__class__.__check_command_response(response)

        return response

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
        logger,
    ) -> None:
        """Terminate listener thread if execution finished or failed."""
        type = response.get("type", None)
        if type in [ServerNotification.EXEC_FAILED.name or ServerNotification.CHECK_FAILED.name]:
            sender.stop_listening()
            sender.clear_callbacks()
            target_queue.put("False")
            logger.error(f"Listener {sender.name} received error notification.")
        elif type in target_notifications:
            sender.stop_listening()
            sender.clear_callbacks()
            target_queue.put("True")
            logger.debug(f"Listener {sender.name} received expected notification.")
        elif type is None:
            logger.error("Invalid response from server, push notification not evaluated.")

from abc import ABC, abstractmethod
from socket import AF_INET, SOCK_DGRAM, SOCK_STREAM, socket
from typing import (
    Any, BinaryIO, Generator, Generic, Iterable, List, Optional, TypeVar, cast
)

from pyais.exceptions import InvalidNMEAMessageException
from pyais.messages import NMEAMessage
from pyais.util import FixedSizeDict

F = TypeVar("F", BinaryIO, socket, None)
DOLLAR_SIGN = ord("$")
EXCLAMATION_POINT = ord("!")


def should_parse(byte_str: bytes) -> bool:
    """Return True if a given byte string seems to be NMEA message.
    This method does **NOT** validate the message, but uses a heuristic
    approach to check (or guess) if byte string is a valid nmea_message.
    """
    # The byte sequence is not empty and starts with a $ or a ! and has 6 ','
    return len(byte_str) > 0 and byte_str[0] in (DOLLAR_SIGN, EXCLAMATION_POINT) and byte_str.count(b",") == 6


class AssembleMessages(ABC):
    """
    Base class that assembles multiline messages.
    Offers a iterator like interface.

    This class comes without a __init__ method, because it should never be instantiated!
    """

    def __enter__(self) -> "AssembleMessages":
        # Enables use of with statement
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        return None

    def __iter__(self) -> Generator[NMEAMessage, None, None]:
        return self._assemble_messages()

    def __next__(self) -> NMEAMessage:
        """Returns the next decoded NMEA message."""
        return next(iter(self))

    def _assemble_messages(self) -> Generator[NMEAMessage, None, None]:
        queue: List[NMEAMessage] = []

        for line in self._iter_messages():

            # Be gentle and just skip invalid messages
            try:
                msg: NMEAMessage = NMEAMessage(line)
            except InvalidNMEAMessageException:
                continue

            if msg.is_single:
                yield msg

            # Assemble multiline messages
            elif msg.is_multi:
                queue.append(msg)

                if msg.fragment_number == msg.message_fragments:
                    yield msg.assemble_from_iterable(queue)
                    queue.clear()
            else:
                raise ValueError("Messages are out of order!")

    @abstractmethod
    def _iter_messages(self) -> Generator[bytes, None, None]:
        raise NotImplementedError("Implement me!")


class IterMessages(AssembleMessages):

    def __init__(self, messages: Iterable[bytes]):
        # If the user passes a single byte string make it into a list
        if isinstance(messages, bytes):
            messages = [messages, ]
        self.messages: Iterable[bytes] = messages

    @classmethod
    def from_strings(cls, messages: Iterable[str], ignore_encoding_errors: bool = False,
                     encoding: str = "utf-8") -> "IterMessages":
        # If the users passes a single message as string, make it a list
        if isinstance(messages, str):
            messages = [messages, ]

        encoded: List[bytes] = []
        for message in messages:
            try:
                encoded.append(message.encode(encoding))
            except UnicodeEncodeError as e:
                if ignore_encoding_errors:
                    # Just skip and carry on
                    continue
                raise e

        return IterMessages(encoded)

    def _iter_messages(self) -> Generator[bytes, None, None]:
        # Transform self.messages into a generator
        yield from (message for message in self.messages)


class Stream(AssembleMessages, Generic[F], ABC):

    def __init__(self, fobj: F) -> None:
        """
        Create a new Stream-like object.
        @param fobj: A file-like or socket object.
        """
        self._fobj: F = fobj

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._fobj is not None:
            self._fobj.close()

    def _iter_messages(self) -> Generator[bytes, None, None]:
        # Do not parse lines, that are obviously not NMEA messages
        yield from (line for line in self.read() if should_parse(line))

    @abstractmethod
    def read(self) -> Generator[bytes, None, None]:
        raise NotImplementedError()


class BinaryIOStream(Stream[BinaryIO]):
    """Read messages from a file-like object"""

    def __init__(self, file: BinaryIO) -> None:
        super().__init__(file)

    def read(self) -> Generator[bytes, None, None]:
        yield from self._fobj.readlines()


class FileReaderStream(BinaryIOStream):
    """
    Read NMEA messages from file
    """

    def __init__(self, filename: str, mode: str = "rb") -> None:
        self.filename: str = filename
        self.mode: str = mode
        # Try to open file
        try:
            file = open(self.filename, mode=self.mode)
            file = cast(BinaryIO, file)
        except Exception as e:
            raise FileNotFoundError(f"Could not open file {self.filename}") from e
        super().__init__(file)


class ByteStream(Stream[None]):
    """
    Takes a iterable that contains ais messages as bytes and assembles them.
    """

    def __init__(self, iterable: Iterable[bytes]) -> None:
        self.iterable: Iterable[bytes] = iterable
        super().__init__(None)

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        return

    def read(self) -> Generator[bytes, None, None]:
        yield from self.iterable


class OutOfOrderByteStream(Stream[F], ABC):
    """
    Handles multipart NMEA that are delivered out of order.

    This class is not attached to a datasource by default.
    You need to subclass it and override _get_messages().
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # create a fixed sized message queue
        self._queue = FixedSizeDict(10000)
        super().__init__(*args, **kwargs)

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        del self._queue
        super().__exit__(exc_type, exc_val, exc_tb)

    def _split_nmea_header(self, msg: bytes) -> None:
        """
        Read the important parts of a NMEA header
        """
        parts: List[bytes] = msg.split(b',')
        self.seq_id: int = int(parts[3]) if parts[3] else 0
        self.fragment_offset: int = int(parts[2]) - 1
        self.fragment_count: int = int(parts[1])

    def _yield_complete(self) -> Optional[List[bytes]]:
        """
        Check if the message is complete and return it
        """
        # get all messages for the current sequence number
        queue: List[bytes] = self._queue[self.seq_id][0:self.fragment_count]
        if all(queue[0: self.fragment_count]):
            # if all required messages are received yield them and free their space
            del self._queue[self.seq_id]
            return queue[0: self.fragment_count]
        return None

    def _add_to_queue(self, msg: bytes) -> None:
        """
        Append a new nmea message to queue
        """
        # MAX frag offset for any AIS NMEA is 9
        msg_queue: List[Optional[bytes]] = ([None, ] * 9)
        try:
            # place the message at its correct position
            msg_queue[self.fragment_offset] = msg
        except IndexError:
            # message is invalid clear it
            del self._queue[self.seq_id]
        self._queue[self.seq_id] = msg_queue

    def _update_queue(self, msg: bytes) -> Optional[Iterable[bytes]]:
        """
        Update an existing message queue that is not complete yet.
        Return a list of fully assembled messages if all required messages for a given sequence number are received.
        """
        msg_queue: List[bytes] = self._queue[self.seq_id]
        msg_queue[self.fragment_offset] = msg
        complete: Optional[List[bytes]] = self._yield_complete()
        if complete:
            yield from complete
        return None

    def _iter_messages(self) -> Generator[bytes, None, None]:
        for msg in self.read():
            # decode nmea header
            self._split_nmea_header(msg)
            if not self.seq_id:
                yield msg
            try:
                complete = self._update_queue(msg)
                if complete is not None:
                    yield from complete

            except KeyError:
                # place item a correct pos and then store the list
                self._add_to_queue(msg)


class SocketStream(Stream[socket]):
    BUF_SIZE = 4096

    def read(self) -> Generator[bytes, None, None]:
        partial: bytes = b''
        while True:
            body = self._fobj.recv(self.BUF_SIZE)
            # Server closed connection
            if not body:
                return None

            lines = body.split(b'\r\n')

            line = partial + lines[0]
            if line:
                yield line

            yield from (line for line in lines[1:-1] if line)

            partial = lines[-1]


class UDPStream(OutOfOrderByteStream[socket], SocketStream):

    def __init__(self, host: str, port: int) -> None:
        sock: socket = socket(AF_INET, SOCK_DGRAM)
        sock.bind((host, port))
        super().__init__(sock)


class TCPStream(SocketStream):
    """
     NMEA0183 stream via socket. Refer to
     https://en.wikipedia.org/wiki/NMEA_0183
     """

    def __init__(self, host: str, port: int = 80) -> None:
        sock: socket = socket(AF_INET, SOCK_STREAM)
        try:
            sock.connect((host, port))
        except ConnectionRefusedError as e:
            sock.close()
            raise ConnectionRefusedError(f"Failed to connect to {host}:{port}") from e
        super().__init__(sock)

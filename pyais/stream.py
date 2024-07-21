import typing
from abc import ABC, abstractmethod
from socket import AF_INET, SOCK_DGRAM, SOCK_STREAM, socket
from typing import (
    BinaryIO, Generator, Generic, Iterable, List, TypeVar,
    cast, Tuple, Optional, Dict, Union, Any, Callable
)

from pyais.exceptions import InvalidNMEAMessageException, NonPrintableCharacterException, UnknownMessageException
from pyais.messages import AISSentence, GatehouseSentence, NMEAMessage, NMEASentenceFactory

T = TypeVar("T")
F = TypeVar("F", BinaryIO, socket, None)
DOLLAR_SIGN = ord("$")
EXCLAMATION_POINT = ord("!")
BACKSLASH = ord("\\")


def should_parse(byte_str: bytes, parse_function: Optional[Callable] = None) -> bool:
    """Return True if a given byte string seems to be NMEA message.
    This method does **NOT** validate the message, but uses a heuristic
    approach to check (or guess) if byte string is a valid nmea_message.
    """
    if parse_function is None:
        # The byte sequence is not empty and starts with a $ or a ! or \
        return len(byte_str) > 0 and byte_str[0] in (DOLLAR_SIGN, EXCLAMATION_POINT, BACKSLASH)
    else:
        try:
            # try to parse the line and run the above test
            nmea_message = parse_function(byte_str)[0]
            return should_parse(nmea_message)
        except Exception:  # TODO: better Exception
            # otherwise, the line must not be processed
            return False


class AssembleMessages(ABC):
    """
    Base class that assembles multiline messages.
    Offers a iterator like interface.
    """

    def __init__(self) -> None:
        self.wrapper_msg: Optional[GatehouseSentence] = None

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

    def __set_last_wrapper_msg(self, wrapper_msg: GatehouseSentence) -> None:
        self.wrapper_msg = wrapper_msg

    def __get_last_wrapper_msg(self) -> Optional[GatehouseSentence]:
        self.wrapper_msg, wrapper_msg = None, self.wrapper_msg
        return wrapper_msg

    def __insert_wrapper_msg(self, msg: AISSentence) -> AISSentence:
        wrapper_msg = self.__get_last_wrapper_msg()
        if wrapper_msg:
            msg.wrapper_msg = wrapper_msg
        return msg

    def _assemble_messages(
            self
    ) -> Generator[Union[NMEAMessage, Tuple[NMEAMessage, Any]], None, None]:
        buffer: Dict[Tuple[int, str], List[Optional[NMEAMessage]]] = {}
        messages = self._iter_messages()
        msg: AISSentence

        for nmea_message, metadata in messages:
            try:
                sentence = NMEASentenceFactory.produce(nmea_message)
                if sentence.TYPE == GatehouseSentence.TYPE:
                    sentence = cast(GatehouseSentence, sentence)
                    self.__set_last_wrapper_msg(sentence)
                    continue
            except (InvalidNMEAMessageException, NonPrintableCharacterException, UnknownMessageException):
                # Be gentle and just skip invalid messages
                continue

            if sentence.TYPE != AISSentence.TYPE:
                continue
            msg = typing.cast(AISSentence, sentence)

            if msg.is_single:
                msg_with_wrapper = self.__insert_wrapper_msg(msg)
                yield msg_with_wrapper if metadata is None else (msg_with_wrapper, metadata)
            else:
                # Instead of None use -1 as a seq_id
                seq_id = msg.seq_id
                if seq_id is None:
                    seq_id = -1

                # seq_id and channel make a unique stream
                slot = (seq_id, msg.channel)

                if slot not in buffer:
                    # Create a new array in the buffer that has enough space for all fragments
                    buffer[slot] = [None, ] * max(msg.fragment_count, 0xff)

                buffer[slot][msg.frag_num - 1] = msg
                msg_parts = buffer[slot][0:msg.fragment_count]

                # Check if all fragments are found
                not_none_parts = [m for m in msg_parts if m is not None]
                if len(not_none_parts) == msg.fragment_count:
                    msg = NMEAMessage.assemble_from_iterable(not_none_parts)
                    msg_with_wrapper = self.__insert_wrapper_msg(msg)
                    yield msg_with_wrapper if metadata is None else (msg_with_wrapper, metadata)
                    del buffer[slot]

    @abstractmethod
    def _iter_messages(self) -> Generator[bytes, None, None]:
        raise NotImplementedError("Implement me!")


class IterMessages(AssembleMessages):
    def __init__(
            self,
            messages: Iterable[bytes],
            parse_function: Optional[Callable] = None,
            encoding: Optional[str] = None
    ) -> None:
        super().__init__()

        # If the user passes a single byte string make it into a list
        if isinstance(messages, bytes):
            messages = [messages, ]
        self.messages = messages
        self.parse_function = parse_function
        self.encoding = encoding

    @classmethod
    def from_strings(
            cls, messages: Iterable[str],
            parse_function: Optional[Callable] = None,
            ignore_encoding_errors: bool = False,
            encoding: str = "utf-8"
    ) -> "IterMessages":
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

        return IterMessages(encoded, parse_function, encoding)

    def _iter_messages(self) -> Generator[Tuple[bytes, Any], None, None]:
        # Transform self.messages into a generator
        if self.parse_function is not None:
            yield from (
                self.parse_function(messages if self.encoding is None else messages.decode(self.encoding))
                for messages in self.messages
            )
        yield from ((msg, None) for msg in self.messages)


class Stream(AssembleMessages, Generic[F], ABC):
    def __init__(
            self,
            fobj: F,
            parse_function: Optional[Callable] = None,
            encoding: Optional[str] = None
    ) -> None:
        """
        Create a new Stream-like object.
        @param fobj: A file-like or socket object.
        """
        super().__init__()
        self._fobj: F = fobj
        self.parse_function = parse_function
        self.encoding = encoding

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._fobj is not None:
            self._fobj.close()

    def _iter_messages(self) -> Generator[bytes, None, None]:
        # Do not parse lines, that are obviously not NMEA messages
        # Transform self.messages into a generator
        if self.parse_function is not None:
            yield from (self.parse_function(line) for line in self.read() if should_parse(line, self.parse_function))
        yield from ((line, None) for line in self.read() if should_parse(line))

    @abstractmethod
    def read(self) -> Generator[bytes, None, None]:
        raise NotImplementedError()


class BinaryIOStream(Stream[BinaryIO]):
    """Read messages from a file-like object"""

    def __init__(self, file: BinaryIO, *args, **kwargs) -> None:
        super().__init__(file, *args, **kwargs)

    def read(self) -> Generator[bytes, None, None]:
        yield from self._fobj


class FileReaderStream(BinaryIOStream):
    """
    Read NMEA messages from file
    """

    def __init__(
            self,
            filename: str,
            *args,
            mode: str = "rb",
            **kwargs
    ) -> None:
        self.filename: str = filename
        self.mode: str = mode
        # Try to open file
        try:
            file = open(self.filename, mode=self.mode)
            file = cast(BinaryIO, file)
        except Exception as e:
            raise FileNotFoundError(f"Could not open file {self.filename}") from e
        super().__init__(file, *args, **kwargs)


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


class SocketStream(Stream[socket]):
    BUF_SIZE = 4096

    def recv(self) -> bytes:
        return b""

    def read(self) -> Generator[bytes, None, None]:
        partial: bytes = b''
        while True:
            body = self.recv()

            # Server closed connection
            if not body:
                return None

            lines = body.splitlines(keepends=True)

            # last incomplete line
            line = partial + lines[0]
            if line:
                yield line
            partial = b''

            if lines[-1].endswith(b'\n'):
                # all lines are complete
                yield from lines[1:]
            else:
                # the last line was only partially received
                yield from lines[1:-1]
                partial = lines[-1]


class UDPReceiver(SocketStream):

    def __init__(self, host: str, port: int) -> None:
        sock: socket = socket(AF_INET, SOCK_DGRAM)
        sock.bind((host, port))
        super().__init__(sock)

    def recv(self) -> bytes:
        return self._fobj.recvfrom(self.BUF_SIZE)[0]


class TCPConnection(SocketStream):
    """
     Read AIS data from a remote TCP server
     https://en.wikipedia.org/wiki/NMEA_0183
     """

    def recv(self) -> bytes:
        return self._fobj.recv(self.BUF_SIZE)

    def __init__(self, host: str, port: int = 80) -> None:
        sock: socket = socket(AF_INET, SOCK_STREAM)
        try:
            sock.connect((host, port))
        except ConnectionRefusedError as e:
            sock.close()
            raise ConnectionRefusedError(f"Failed to connect to {host}:{port}") from e
        super().__init__(sock)

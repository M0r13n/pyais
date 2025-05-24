import typing
import pathlib
import queue
from abc import ABC, abstractmethod
from socket import AF_INET, SOCK_DGRAM, SOCK_STREAM, socket
from typing import BinaryIO, Generator, Generic, Iterable, List, TypeVar, cast

from pyais.exceptions import InvalidNMEAMessageException, NonPrintableCharacterException, UnknownMessageException
from pyais.messages import AISSentence, GatehouseSentence, NMEAMessage, NMEASentence, NMEASentenceFactory

T = TypeVar("T")
F = TypeVar("F", BinaryIO, socket, None)
DOLLAR_SIGN = ord("$")
EXCLAMATION_POINT = ord("!")
BACKSLASH = ord("\\")


def should_parse(byte_str: bytes) -> bool:
    """Return True if a given byte string seems to be NMEA message.
    This method does **NOT** validate the message, but uses a heuristic
    approach to check (or guess) if byte string is a valid nmea_message.
    """
    # The byte sequence is not empty and starts with a $ or a ! or \
    return len(byte_str) > 0 and byte_str[0] in (DOLLAR_SIGN, EXCLAMATION_POINT, BACKSLASH)


class PreprocessorProtocol(typing.Protocol):
    """
    Protocol for preprocessing lines of bytes into NMEA0183 format.

    This protocol must be implemented to support various message formats in the pyais library.
    Implementing classes should provide a `process` method that transforms input lines of bytes
    into NMEA0183 compliant messages.

    Methods:
    --------
    process(line: bytes) -> bytes:
        Processes an input line of bytes and returns it in NMEA0183 format.
    """

    def process(self, line: bytes) -> bytes:
        """
        Process an input line of bytes and return it in NMEA0183 format.

        Parameters:
        -----------
        line : bytes
            The input line of bytes to be processed.

        Returns:
        --------
        bytes
            The processed line in bytes, conforming to the NMEA0183 format.
        """
        pass


class TagBlockQueue(queue.Queue):  # type: ignore

    def __init__(self, maxsize: int = 0) -> None:
        self.groups: typing.Dict[str, typing.Dict[str, object]] = {}
        super().__init__(maxsize)

    def put_sentence(self, sentence: NMEASentence) -> None:
        if not sentence.tag_block:
            # No NMEA 4.10 tag block
            # Returns a single line immediately.
            super().put([sentence,])
            return

        tb = sentence.tag_block
        tb.init()

        if not tb.group:
            # No NMEA 4.10 tag block 'g'.
            super().put([sentence,])
            return

        if int(tb.group.sentence_tot) == 1:
            # Group of a single sentence
            super().put([sentence,])
            return

        if int(tb.group.sentence_num) == 1:
            # The first sentence
            self.groups[tb.group.group_id] = {'sentence_tot': tb.group.sentence_tot, 'sentences': [sentence,]}
            return

        if tb.group.group_id not in self.groups:
            # Unknown group. First sentence of group is missing.
            return

        self.groups[tb.group.group_id]['sentences'].append(sentence)  # type: ignore

        # is_last_sentence = int(tb.group.sentence_num) != int(self.groups[tb.group.group_id]['sentence_tot'])
        group_is_complete = int(tb.group.sentence_tot) != len(self.groups[tb.group.group_id]['sentences'])  # type: ignore

        if group_is_complete:
            return

        # All sentences belonging to this group were received.
        super().put(self.groups[tb.group.group_id]['sentences'])
        del self.groups[tb.group.group_id]


class AssembleMessages(ABC):
    """
    Base class that assembles multiline messages.
    Offers a iterator like interface.
    """

    def __init__(self, tbq: typing.Optional[TagBlockQueue] = None) -> None:
        self.wrapper_msg: typing.Optional[GatehouseSentence] = None
        self.tbq: typing.Optional[TagBlockQueue] = tbq

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

    def __get_last_wrapper_msg(self) -> typing.Optional[GatehouseSentence]:
        wrapper_msg = self.wrapper_msg
        self.wrapper_msg = None
        return wrapper_msg

    def __insert_wrapper_msg(self, msg: AISSentence) -> AISSentence:
        wrapper_msg = self.__get_last_wrapper_msg()
        if wrapper_msg:
            msg.wrapper_msg = wrapper_msg
        return msg

    def __add_to_tbq(self, sentence: NMEASentence) -> None:
        if not self.tbq:
            # Tag Block Queue not defined. Do nothing.
            return
        self.tbq.put_sentence(sentence)

    def _assemble_messages(self) -> Generator[NMEAMessage, None, None]:
        buffer: typing.Dict[typing.Tuple[int, str], typing.List[typing.Optional[NMEAMessage]]] = {}
        messages = self._iter_messages()
        msg: AISSentence

        for line in messages:
            try:
                sentence = NMEASentenceFactory.produce(line)
                self.__add_to_tbq(sentence)
                if sentence.TYPE == GatehouseSentence.TYPE:
                    sentence = cast(GatehouseSentence, sentence)
                    self.__set_last_wrapper_msg(sentence)
                    continue
            except (InvalidNMEAMessageException, NonPrintableCharacterException, UnknownMessageException):
                # Be gentle and just skip invalid messages
                continue

            if not sentence.TYPE == AISSentence.TYPE:
                continue
            msg = typing.cast(AISSentence, sentence)

            if msg.is_single:
                yield self.__insert_wrapper_msg(msg)
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
                if not_none_parts and len(not_none_parts) == msg.fragment_count:
                    msg = NMEAMessage.assemble_from_iterable(not_none_parts)
                    yield self.__insert_wrapper_msg(msg)
                    del buffer[slot]

    @abstractmethod
    def _iter_messages(self) -> Generator[bytes, None, None]:
        raise NotImplementedError("Implement me!")


class IterMessages(AssembleMessages):

    def __init__(self, messages: Iterable[bytes], tbq: typing.Optional[TagBlockQueue] = None):
        super().__init__(tbq=tbq)
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

    def __init__(
        self, fobj: F,
        preprocessor: typing.Optional[PreprocessorProtocol] = None,
        tbq: typing.Optional[TagBlockQueue] = None
    ) -> None:
        """
        Create a new Stream-like object.
        @param fobj: A file-like or socket object.
        @param preprocessor: An optional preprocessor
        """
        super().__init__(tbq=tbq)
        self._fobj: F = fobj
        self.preprocessor = preprocessor

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def _iter_messages(self) -> Generator[bytes, None, None]:
        # Do not parse lines, that are obviously not NMEA messages
        for line in self.read():
            if len(line) <= 10:
                continue
            if self.preprocessor is not None:
                line = self.preprocessor.process(line)
            if should_parse(line):
                yield line

    def close(self) -> None:
        if self._fobj is not None:
            self._fobj.close()

    @abstractmethod
    def read(self) -> Generator[bytes, None, None]:
        raise NotImplementedError()


class BinaryIOStream(Stream[BinaryIO]):
    """Read messages from a file-like object"""

    def __init__(
        self,
        file: BinaryIO,
        preprocessor: typing.Optional[PreprocessorProtocol] = None,
        tbq: typing.Optional[TagBlockQueue] = None
    ) -> None:
        super().__init__(file, preprocessor=preprocessor, tbq=tbq)

    def read(self) -> Generator[bytes, None, None]:
        yield from self._fobj


class FileReaderStream(BinaryIOStream):
    """
    Read NMEA messages from file
    """

    def __init__(
        self,
        filename: typing.Union[str, pathlib.Path],
        mode: str = "rb",
        preprocessor: typing.Optional[PreprocessorProtocol] = None,
        tbq: typing.Optional[TagBlockQueue] = None
    ) -> None:
        self.filename: typing.Union[str, pathlib.Path] = filename
        self.mode: str = mode
        # Try to open file
        try:
            file = open(self.filename, mode=self.mode)
            file = cast(BinaryIO, file)
        except Exception as e:
            raise FileNotFoundError(f"Could not open file {self.filename}") from e
        super().__init__(file, preprocessor=preprocessor, tbq=tbq)


class ByteStream(Stream[None]):
    """
    Takes a iterable that contains ais messages as bytes and assembles them.
    """

    def __init__(
        self,
        iterable: Iterable[bytes],
        preprocessor: typing.Optional[PreprocessorProtocol] = None,
        tbq: typing.Optional[TagBlockQueue] = None
    ) -> None:
        self.iterable: Iterable[bytes] = iterable
        super().__init__(None, preprocessor=preprocessor, tbq=tbq)

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        return

    def read(self) -> Generator[bytes, None, None]:
        yield from self.iterable


class SocketStream(Stream[socket]):
    BUF_SIZE = 4096

    def recv(self) -> bytes:
        return self._fobj.recv(self.BUF_SIZE)

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

    def __init__(
        self,
        host: str,
        port: int,
        preprocessor: typing.Optional[PreprocessorProtocol] = None,
        tbq: typing.Optional[TagBlockQueue] = None
    ) -> None:
        sock: socket = socket(AF_INET, SOCK_DGRAM)
        sock.bind((host, port))
        super().__init__(sock, preprocessor=preprocessor, tbq=tbq)

    def recv(self) -> bytes:
        return self._fobj.recvfrom(self.BUF_SIZE)[0]


class TCPConnection(SocketStream):
    """
     Read AIS data from a remote TCP server
     https://en.wikipedia.org/wiki/NMEA_0183
     """

    def recv(self) -> bytes:
        return self._fobj.recv(self.BUF_SIZE)

    def __init__(
        self,
        host: str,
        port: int = 80,
        preprocessor: typing.Optional[PreprocessorProtocol] = None,
        tbq: typing.Optional[TagBlockQueue] = None
    ) -> None:
        sock: socket = socket(AF_INET, SOCK_STREAM)
        try:
            sock.connect((host, port))
        except ConnectionRefusedError as e:
            sock.close()
            raise ConnectionRefusedError(f"Failed to connect to {host}:{port}") from e
        super().__init__(sock, preprocessor=preprocessor, tbq=tbq)

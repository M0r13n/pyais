import typing
from abc import ABC, abstractmethod
from socket import AF_INET, SOCK_DGRAM, SOCK_STREAM, socket
from typing import Iterable, List, Generator

from pyais.messages import NMEAMessage
from pyais.util import FixedSizeDict


class Stream(ABC):

    def __init__(self, fobj):
        self._fobj = fobj

    def __enter__(self):
        # Enables use of with statement
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._fobj.close()

    def __iter__(self):
        return self._assemble_messages()

    def __next__(self):
        return next(iter(self))

    def _assemble_messages(self) -> Generator[NMEAMessage, None, None]:
        queue: List[NMEAMessage] = []

        for line in self._iter_messages():
            # Try to parse the message
            try:
                msg: NMEAMessage = NMEAMessage(line)
            except Exception as e:
                raise ValueError(f'Failed to parse line "{line}"') from e

            # Be gentle and just skip invalid messages
            if not msg.is_valid:
                continue

            if msg.is_single:
                yield msg

            # Assemble multiline messages
            elif msg.is_multi:
                queue.append(msg)

                if msg.index == msg.count:
                    yield msg.assemble_from_iterable(queue)
                    queue.clear()
            else:
                raise ValueError("Messages are out of order!")

    def _iter_messages(self) -> Generator[bytes, None, None]:
        yield from self.read()

    @abstractmethod
    def read(self) -> Generator[bytes, None, None]:
        raise NotImplementedError()


class FileReaderStream(Stream):
    """
    Read NMEA messages from file
    """

    def __init__(self, filename, mode="rb"):
        self.filename = filename
        self.mode = mode
        # Try to open file
        try:
            file = open(self.filename, mode=self.mode)
        except Exception as e:
            raise FileNotFoundError(f"Could not open file {self.filename}") from e
        super().__init__(file)

    def read(self) -> Generator[bytes, None, None]:
        yield from self._fobj.readlines()


class ByteStream(Stream):
    """
    Takes a iterable that contains ais messages as bytes and assembles them.
    """

    def __init__(self, iterable: typing.Iterable[bytes]):
        self.iterable: typing.Iterable[bytes] = iterable
        super().__init__(None)

    def __exit__(self, exc_type, exc_val, exc_tb):
        return 0

    def read(self) -> Generator[bytes, None, None]:
        yield from self.iterable


class OutOfOrderByteStream(Stream, ABC):
    """
    Handles multipart NMEA that are delivered out of order.

    This class is not attached to a datasource by default.
    You need to subclass it and override _get_messages().
    """

    def __init__(self, *args, **kwargs):
        # create a fixed sized message queue
        self._queue = FixedSizeDict(10000)
        super().__init__(*args, **kwargs)

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self._queue
        super().__exit__(exc_type, exc_val, exc_tb)

    def _split_nmea_header(self, msg: bytes):
        """
        Read the important parts of a NMEA header
        """
        parts = msg.split(b',')
        self.seq_id = int(parts[3]) if parts[3] else 0
        self.fragment_offset: int = int(parts[2]) - 1
        self.fragment_count: int = int(parts[1])

    def _yield_complete(self) -> typing.Optional[List[bytes]]:
        """
        Check if the message is complete and return it
        """
        # get all messages for the current sequence number
        queue: List[bytes] = self._queue[self.seq_id][0:self.fragment_count]
        if all(queue[0: self.fragment_count]):
            # if all required messages are received yield them and free their space
            del self._queue[self.seq_id]
            return queue[0: self.fragment_count]

    def _add_to_queue(self, msg: bytes):
        """
        Append a new nmea message to queue
        """
        # MAX frag offset for any AIS NMEA is 9
        msg_queue: list = ([None, ] * 9)
        try:
            # place the message at its correct position
            msg_queue[self.fragment_offset] = msg
        except IndexError:
            # message is invalid clear it
            del self._queue[self.seq_id]
        self._queue[self.seq_id] = msg_queue

    def _update_queue(self, msg: bytes) -> typing.Optional[Iterable[bytes]]:
        """
        Update an existing message queue that is not complete yet.
        Return a list of fully assembled messages if all required messages for a given sequence number are received.
        """
        msg_queue: list = self._queue[self.seq_id]
        msg_queue[self.fragment_offset] = msg
        complete: typing.Optional[List[bytes]] = self._yield_complete()
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


class SocketStream(Stream):
    BUF_SIZE = 4096

    def read(self) -> Generator[bytes, None, None]:
        partial = b''
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


class UDPStream(OutOfOrderByteStream, SocketStream):

    def __init__(self, host: str, port: int):
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.bind((host, port))
        super().__init__(sock)


class TCPStream(SocketStream):
    """
     NMEA0183 stream via socket. Refer to
     https://en.wikipedia.org/wiki/NMEA_0183
     """

    def __init__(self, host: str, port: int = 80):
        sock = socket(AF_INET, SOCK_STREAM)
        try:
            sock.connect((host, port))
        except ConnectionRefusedError as e:
            sock.close()
            raise ConnectionRefusedError(f"Failed to connect to {host}:{port}") from e
        super().__init__(sock)

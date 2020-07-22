from socket import AF_INET, SOCK_STREAM, socket
from typing import Iterable
import typing

from pyais.messages import NMEAMessage


class Stream:

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

    def _iter_messages(self) -> Iterable[bytes]:
        raise NotImplementedError()

    def _assemble_messages(self):
        queue = []

        for line in self._iter_messages():
            # Try to parse the message
            try:
                msg = NMEAMessage(line)
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

    def _iter_messages(self) -> Iterable[bytes]:
        yield from self._fobj.readlines()


class ByteStream(Stream):
    """
    Takes a iterable that contains ais messages as bytes and assembles them.
    """

    def __init__(self, iterable: typing.Iterable[bytes]):
        self.iterable: typing.Iterable[bytes] = iterable

    def __exit__(self, exc_type, exc_val, exc_tb):
        return 0

    def _iter_messages(self) -> Iterable[bytes]:
        yield from self.iterable


class TCPStream(Stream):
    """
     NMEA0183 stream via socket. Refer to
     https://en.wikipedia.org/wiki/NMEA_0183
     """

    BUF_SIZE = 4096

    def __init__(self, host: str, port: int = 80):
        sock = socket(AF_INET, SOCK_STREAM)
        try:
            sock.connect((host, port))
        except ConnectionRefusedError as e:
            sock.close()
            raise ConnectionRefusedError(f"Failed to connect to {host}:{port}") from e
        super().__init__(sock)

    def _iter_messages(self) -> Iterable[bytes]:
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

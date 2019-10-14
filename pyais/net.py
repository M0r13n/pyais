from socket import AF_INET, SOCK_STREAM, socket
from typing import Iterable


BUF_SIZE = 4096


def ais_stream(host: str = "ais.exploratorium.edu", port: int = 80) -> Iterable[bytes]:
    with socket(AF_INET, SOCK_STREAM) as s:
        s.connect((host, port))

        partial = b''

        while True:
            body = s.recv(BUF_SIZE)
            lines = body.split(b'\r\n')

            line = partial + lines[0]
            if line:
                yield line

            yield from (line for line in lines[1:-1] if line)

            partial = lines[-1]
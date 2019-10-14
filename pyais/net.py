import socket
import struct


def ais_stream(url="ais.exploratorium.edu", port=80):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((url, port))
    while True:
        for msg in s.recv(4096).decode("utf-8").splitlines():
            yield msg


def recv_line(url="ais.exploratorium.edu", port=80):
    """
    Asks for 4096 bytes, yields chunks of one line at a time,
    and maintains a local buffer between loop iterations of incomplete lines.
    """
    # Create a TCP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((url, port))
    # Create local message buffer
    buffer = b''
    last_byte = b''
    while True:
        # Receive up to 4096 bytes and store them in a temporary buffer
        temp = s.recv(4096)
        # Iterate over each byte and yield a message if a new1line byte is reached
        for byte in struct.unpack(str(len(temp)) + 'c', temp):
            # New lines are indicated by '\r\n'
            if last_byte == b'\r' and byte == b'\n':
                yield buffer
                buffer = b''
                last_byte = b''
            else:
                buffer += last_byte
                last_byte = byte

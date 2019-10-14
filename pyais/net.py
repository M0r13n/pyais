import socket


def ais_stream(url="ais.exploratorium.edu", port=80):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((url, port))
    while True:
        for msg in s.recv(4096).decode("utf-8").splitlines():
            yield msg

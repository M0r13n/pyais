from .message import decode
from .net import ais_stream


def main():
    for msg in ais_stream():
        if msg and msg[0] == "!":
            print(decode(msg))
        else:
            print("Unparsed msg: " + msg)


main()

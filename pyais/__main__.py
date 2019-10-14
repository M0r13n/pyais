from .message import decode
from .net import ais_stream


def main():
    for msg in ais_stream():
        if msg[0] == ord('!'):
            print(decode(msg))
        else:
            print("Unparsed msg: " + msg.decode('ascii'))


main()

import argparse
import sys
from _io import BufferedReader
from typing import List, BinaryIO, TextIO

from pyais.exceptions import InvalidChecksumException
from pyais.stream import ByteStream, TCPStream, UDPStream, BinaryIOStream


def parse_arguments() -> argparse.ArgumentParser:
    """Create a new ArgumentParser instance that serves as a entry point to the pyais application.
    All possible commandline options and parameters must be defined here.
    The goal is to create a grep-like interface:
        Usage: ais-decode [OPTION]... PATTERNS [FILE]...
    """
    main_parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="ais-decode",
        description="AIS message decoding. 100% pure Python."
                    "Supports AIVDM/AIVDO messages. Supports single messages, files and TCP/UDP sockets.",
    )
    sub_parsers = main_parser.add_subparsers()

    # Modes
    # Currently two mutual exclusive modes are supported: TCP/UDP or file
    # By default the program accepts input from STDIN
    # Optional subparsers server as subcommands that handle socket connections and file reading
    main_parser.add_argument(
        '-f',
        '--file',
        dest="in_file",
        nargs="?",
        type=argparse.FileType("rb"),
        default=None
    )

    main_parser.set_defaults(func=decode_from_file)

    socket_parser = sub_parsers.add_parser('socket')
    socket_parser.add_argument(
        'destination',
        type=str,
    )
    socket_parser.add_argument(
        'port',
        type=int
    )
    socket_parser.add_argument(
        '-t',
        '--type',
        default='udp',
        nargs='?',
        choices=['udp', 'tcp']
    )

    socket_parser.set_defaults(func=decode_from_socket)

    # Optional a single message can be decoded
    # This has the highest precedence and will overwrite all other settings
    single_msg_parser = sub_parsers.add_parser('single')
    single_msg_parser.add_argument(
        'messages',
        nargs='+',
        default=[]
    )
    single_msg_parser.set_defaults(func=decode_single)

    # Output
    # By default the application writes it output to STDOUT - but this can be any file
    main_parser.add_argument(
        "-o",
        "--out-file",
        dest="out_file",
        type=argparse.FileType("w"),
        default=sys.stdout
    )

    return main_parser


def print_error(*args, **kwargs):
    print(*args, **kwargs, file=sys.stdout)


def decode_from_socket(args) -> int:
    if args.type == "udp":
        stream = UDPStream
    else:
        stream = TCPStream

    with stream(args.destination, args.port) as s:
        try:
            for msg in s:
                decoded_message = msg.decode(silent=True)
                print(decoded_message, file=args.out_file)
        except KeyboardInterrupt:
            # do nothing here
            return 0
    return 0


def decode_single(args) -> int:
    """Decode a list of single messages."""
    messages: List[str] = args.messages
    messages_as_bytes: List[bytes] = [msg.encode() for msg in messages]
    try:
        for msg in ByteStream(messages_as_bytes):
            print(msg.decode(), file=args.out_file)
    except InvalidChecksumException:
        print_error(f"Checksum invalid")
        return 1
    return 0


def decode_from_file(args) -> int:
    if not args.in_file:
        file: BinaryIO = sys.stdin.buffer
    else:
        file: BinaryIO = args.in_file

    with BinaryIOStream(file) as s:
        try:
            for msg in s:
                decoded_message = msg.decode(silent=True)
                print(decoded_message, file=args.out_file)
        except KeyboardInterrupt:
            # do nothing here
            return 0
    return 0


def main() -> int:
    main_parser = parse_arguments()
    namespace: argparse.Namespace = main_parser.parse_args()
    exit_code: int = namespace.func(namespace)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

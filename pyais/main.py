import argparse
import sys
from typing import List, Tuple, Type, Any, Union

from pyais.stream import ByteStream, TCPStream, UDPStream, BinaryIOStream

SOCKET_OPTIONS: Tuple[str, str] = ('udp', 'tcp')

# Error Codes
INVALID_CHECKSUM_ERROR = 21


def arg_parser() -> argparse.ArgumentParser:
    """Create a new ArgumentParser instance that serves as a entry point to the pyais application.
    All possible commandline options and parameters must be defined here.
    The goal is to create a grep-like interface:
        Usage: ais-decode [OPTION]... PATTERNS [FILE]...
    """
    main_parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="ais-decode",
        description="AIS message decoding. 100% pure Python."
                    "Supports AIVDM/AIVDO messages. Supports single messages, files and TCP/UDP sockets.rst.",
    )
    sub_parsers = main_parser.add_subparsers()

    # Modes
    # Currently three mutual exclusive modes are supported: TCP/UDP / file / single messages as arguments
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
        choices=SOCKET_OPTIONS
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


def print_error(*args: Any, **kwargs: Any) -> None:
    """Wrapper around the default print function that writes to STDERR."""
    print(*args, **kwargs, file=sys.stdout)


def decode_from_socket(args: argparse.Namespace) -> int:
    """Connect a socket and start decoding."""
    t: str = args.type
    stream_cls: Type[Union[UDPStream, TCPStream]]
    if t == "udp":
        stream_cls = UDPStream
    elif t == "tcp":
        stream_cls = TCPStream
    else:
        raise ValueError("args.type must be either TCP or UDP.")

    with stream_cls(args.destination, args.port) as s:
        try:
            for msg in s:
                decoded_message = msg.decode(silent=True)
                print(decoded_message, file=args.out_file)
        except KeyboardInterrupt:
            # Catch KeyboardInterrupts in order to close the socket and free associated resources
            return 0
    return 0


def decode_single(args: argparse.Namespace) -> int:
    """Decode a list of messages."""
    messages: List[str] = args.messages
    messages_as_bytes: List[bytes] = [msg.encode() for msg in messages if isinstance(msg, str)]
    for msg in ByteStream(messages_as_bytes):
        print(msg.decode(), file=args.out_file)
        if not msg.is_valid:
            print_error("WARNING: Checksum invalid")
    return 0


def decode_from_file(args: argparse.Namespace) -> int:
    """Decode messages from a file-like object."""
    if not args.in_file:
        # This is needed, because it is not possible to open STDOUT in binary mode (it is text mode by default)
        # Therefore it is None by default and we interact with the buffer directly
        file = sys.stdin.buffer
    else:
        # If the file is not None, then it was opened during argument parsing
        file = args.in_file

    with BinaryIOStream(file) as s:
        try:
            for msg in s:
                decoded_message = msg.decode(silent=True)
                print(decoded_message, file=args.out_file)
        except KeyboardInterrupt:
            # Catch KeyboardInterrupts in order to close the file descriptor and free associated resources
            return 0
    return 0


def main() -> int:
    main_parser = arg_parser()
    namespace: argparse.Namespace = main_parser.parse_args()
    exit_code: int = namespace.func(namespace)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

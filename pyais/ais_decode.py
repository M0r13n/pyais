import argparse
import json
import sys
from typing import List, Tuple, Type, Any, Union, TextIO, cast

from pyais.messages import AISJSONEncoder
from pyais.stream import ByteStream, TCPConnection, UDPReceiver, BinaryIOStream

SOCKET_OPTIONS: Tuple[str, str] = ('udp', 'tcp')

# Error Codes
INVALID_CHECKSUM_ERROR = 21


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for the AIS decoder application."""
    parser = argparse.ArgumentParser(
        prog="ais-decode",
        description="Decode NMEA (AIVDM/AIVDO) AIS messages."
                    "Supports single messages, files and TCP/UDP sockets.",
        epilog="Examples:\n"
               "  ais-decode -f input.txt                    # Decode from file\n"
               "  ais-decode -j < input.txt                  # Decode from stdin with JSON output\n"
               "  ais-decode socket localhost 5000           # Decode from UDP socket\n"
               "  ais-decode socket localhost 5000 -t tcp    # Decode from TCP socket\n"
               "  ais-decode single '!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23'\n"
               "  nc 153.44.253.27 5631 | ais-decode --json | jq",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global options
    parser.add_argument(
        '-j', '--json',
        dest="json",
        action='store_true',
        help="Output messages in JSON format"
    )

    parser.add_argument(
        '-o', '--out-file',
        dest="out_file",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="Output file (default: stdout)"
    )

    # Create subparsers for different input modes
    subparsers = parser.add_subparsers(
        title="Input modes",
        description="Choose input source",
        dest="mode",
        required=False
    )

    # File input mode (also default for stdin)
    parser.add_argument(
        '-f', '--file',
        dest="in_file",
        type=argparse.FileType("rb"),
        nargs='?',
        help="Input file (default: stdin if no subcommand specified)"
    )
    parser.set_defaults(func=decode_from_file)

    # Socket input mode
    socket_parser = subparsers.add_parser(
        'socket',
        help="Decode from TCP/UDP socket"
    )
    socket_parser.add_argument(
        'destination',
        help="Hostname or IP address"
    )
    socket_parser.add_argument(
        'port',
        type=int,
        help="Port number"
    )
    socket_parser.add_argument(
        '-t', '--type',
        default='udp',
        choices=SOCKET_OPTIONS,
        help="Socket type (default: udp)"
    )
    socket_parser.set_defaults(func=decode_from_socket)

    # Single message mode
    single_parser = subparsers.add_parser(
        'single',
        help="Decode single message(s)"
    )
    single_parser.add_argument(
        'messages',
        nargs='+',
        help="One or more NMEA messages to decode"
    )
    single_parser.set_defaults(func=decode_single)

    return parser


def print_error(*args: Any, **kwargs: Any) -> None:
    """Print error messages to stderr."""
    print(*args, **kwargs, file=sys.stderr)


def output_message(msg: Any, out_file: TextIO, as_json: bool) -> None:
    """Output a decoded message in the requested format."""
    decoded = msg.decode()

    if as_json:
        json.dump(decoded.asdict(), out_file, cls=AISJSONEncoder)
        out_file.write('\n')  # Add newline for readability
    else:
        out_file.write(str(decoded) + '\n')

    out_file.flush()  # Ensure immediate output for streaming scenarios


def decode_from_socket(args: argparse.Namespace) -> int:
    """Connect to a socket and decode incoming AIS messages."""
    stream_cls: Type[Union[UDPReceiver, TCPConnection]]

    if args.type == "udp":
        stream_cls = UDPReceiver
    elif args.type == "tcp":
        stream_cls = TCPConnection
    else:
        print_error(f"Invalid socket type: {args.type}")
        return 1

    try:
        with stream_cls(args.destination, args.port) as stream:
            print_error(f"Connected to {args.type.upper()} {args.destination}:{args.port}")

            for msg in stream:
                try:
                    output_message(msg, args.out_file, args.json)

                    if not msg.is_valid:
                        print_error(f"WARNING: Invalid checksum for message: {msg}")

                except Exception as e:
                    print_error(f"ERROR decoding message: {e}")
                    continue

    except KeyboardInterrupt:
        print_error("\nConnection closed by user")
        return 0
    except Exception as e:
        print_error(f"ERROR: Failed to connect to {args.destination}:{args.port} - {e}")
        return 1

    return 0


def decode_single(args: argparse.Namespace) -> int:
    """Decode a list of single messages."""
    messages_as_bytes: List[bytes] = [msg.encode() for msg in args.messages]
    error_count = 0

    for i, msg in enumerate(ByteStream(messages_as_bytes)):
        try:
            output_message(msg, args.out_file, args.json)

            if not msg.is_valid:
                print_error(f"WARNING: Invalid checksum for message {i + 1}: {args.messages[i]}")
                error_count += 1

        except Exception as e:
            print_error(f"ERROR decoding message {i + 1}: {e}")
            error_count += 1

    return INVALID_CHECKSUM_ERROR if error_count > 0 else 0


def decode_from_file(args: argparse.Namespace) -> int:
    """Decode messages from a file or stdin."""
    # Use stdin buffer if no file specified
    file_obj = sys.stdin.buffer if args.in_file is None else args.in_file

    try:
        with BinaryIOStream(file_obj) as stream:
            message_count = 0
            error_count = 0

            for msg in stream:
                try:
                    output_message(msg, args.out_file, args.json)
                    message_count += 1

                    if not msg.is_valid:
                        print_error(f"WARNING: Invalid checksum at line {message_count}")
                        error_count += 1

                except Exception as e:
                    print_error(f"ERROR decoding message at line {message_count + 1}: {e}")
                    error_count += 1
                    continue

    except KeyboardInterrupt:
        print_error(f"\nProcessing interrupted. Decoded {message_count} messages.")
        return 0
    except Exception as e:
        print_error(f"ERROR reading input: {e}")
        return 1

    if args.in_file:
        print_error(f"Processed {message_count} messages ({error_count} errors)")

    return 0


def main() -> int:
    """Main entry point for the AIS decoder application."""
    parser = create_parser()
    args = parser.parse_args()

    # Validate arguments
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1

    try:
        return cast(int, args.func(args))
    except Exception as e:
        print_error(f"FATAL ERROR: {e}")
        return 1
    finally:
        # Ensure output file is properly closed
        if hasattr(args, 'out_file') and args.out_file != sys.stdout:
            args.out_file.close()


if __name__ == "__main__":
    sys.exit(main())

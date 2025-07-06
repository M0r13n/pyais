#!/usr/bin/env python3
"""
AIS JSON to NMEA Encoder

This CLI application encodes JSON-formatted AIS (Automatic Identification System) data into NMEA sentences.
It reads JSON from stdin and outputs encoded NMEA AIS messages to stdout.

The encoder supports multiple input modes:
- Single JSON object
- Line-delimited JSON (one object per line)
- Streaming JSON (continuous stream with partial reads)
- Auto-detection (tries single first, then line-delimited)

Usage Examples:
--------------
1. Encode a single AIS position report:
   $ echo '{"msg_type":1,"mmsi":231234000,"turn":5.0,"speed":10.1,"lon":5,"lat":59,"course":356.0}' | ais-encode

2. Encode multiple messages from line-delimited JSON:
   $ cat ais_messages.jsonl | ais-encode --mode lines

3. Process a continuous stream of AIS data:
   $ nc 153.44.253.27 5631 | ais-decode --json | jq -c | ais-encode --mode stream

4. Convert decoded AIS messages back to NMEA:
   $ ais-decode --json < nmea.txt | ais-encode

Input Format:
------------
JSON objects must contain valid AIS message fields. Unknown fields are automatically filtered out.
Required fields vary by message type, but typically include:
- msg_type: AIS message type (1-27)
- mmsi: Maritime Mobile Service Identity
- Additional fields specific to each message type

Output Format:
-------------
NMEA 0183 formatted AIS sentences, one per line, in the format:
!AIVDM,1,1,,A,<encoded_payload>,<checksum>
"""

import argparse
import sys
import json

from functools import partial
from typing import Any, Generator, TextIO

from pyais.encode import encode_dict

KNOWN_FIELDS = {
    'destination', 'ship_type', 'display', 'month',
    'seqno', 'msg22', 'callsign', 'off_position',
    'sw_lat', 'virtual_aid', 'name_ext', 'alt',
    'mmsiseq4', 'to_port', 'minute', 'mmsiseq2',
    'mmsiseq1', 'mmsiseq3', 'assigned', 'reserved_1',
    'reserved_2', 'ne_lon', 'raim', 'maneuver',
    'msg_type', 'to_stern', 'dsc', 'accuracy',
    'heading', 'lat', 'text', 'sw_lon',
    'name', 'hour', 'number2', 'number3',
    'imo', 'number1', 'number4', 'mmsi',
    'dac', 'lon', 'day', 'data',
    'to_starboard', 'ne_lat', 'repeat', 'gnss',
    'ais_version', 'fid', 'station_type', 'dest_mmsi',
    'epfd', 'second', 'mmsi4', 'mmsi3',
    'mmsi2', 'mmsi1', 'txrx', 'radio',
    'turn', 'aid_type', 'speed', 'year',
    'band', 'cs', 'quiet', 'retransmit',
    'status', 'course', 'shipname', 'dte',
    'interval', 'to_bow', 'draught',
}


class AISJSONDecoder(json.JSONDecoder):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(object_hook=self._filter_hook, *args, **kwargs)

    def _filter_hook(self, obj: Any) -> dict[str, Any]:
        """Remove unknown keys from decoded objects"""
        return {k: v for k, v in obj.items() if k in KNOWN_FIELDS}


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Encode NMEA AIS sentences from JSON.'
    )

    parser.add_argument(
        '--mode',
        choices=['single', 'lines', 'stream', 'auto'],
        default='auto',
        help='JSON reading mode'
    )

    parser.add_argument(
        '--talker',
        choices=['AIVDM', 'AIVDO',],
        default='AIVDM',
        help='AIVDM (default) is used for reports from other ships. AIVDO is used for own ship.',
        type=str.upper
    )

    parser.add_argument(
        '--radio',
        choices=['A', 'B',],
        default='A',
        help='The radio channel. Can be either "A" (default) or "B".',
        type=str.upper
    )
    return parser


def read_json_stream(file_obj: TextIO) -> Generator[Any, None, None]:
    """Read JSON objects from a stream, handling partial reads"""
    buffer = ""
    decoder = AISJSONDecoder()

    for line in file_obj:
        buffer += line
        while buffer := buffer.lstrip():
            try:
                obj, idx = decoder.raw_decode(buffer)
                yield obj
                buffer = buffer[idx:]
            except json.JSONDecodeError:
                # Need more data
                break


def read(mode: str) -> Generator[Any, None, None]:
    """Main execution method"""
    if mode == 'stream':
        # Stream mode - process objects as they come
        yield from read_json_stream(sys.stdin)
    else:
        # Read all input first
        json_loads = partial(json.loads, cls=AISJSONDecoder)
        input_text = sys.stdin.read()

        if not input_text.strip():
            return

        if mode == 'single':
            yield json_loads(input_text)
        elif mode == 'lines':
            for line in input_text.strip().split('\n'):
                if line.strip():
                    yield json_loads(line)
        else:  # auto mode
            try:
                yield json_loads(input_text)
            except json.JSONDecodeError:
                # Try line-delimited
                for line in input_text.strip().split('\n'):
                    if line.strip():
                        yield json_loads(line)


def main() -> int:
    # Create an argument parser instance to parse arguments passed via stdin
    parser = create_parser()
    args = parser.parse_args()

    try:
        # read input JSON based on the input mode
        for data in read(args.mode):
            try:
                # encode NMEA AIS message
                encoded = encode_dict(data, talker_id=args.talker, radio_channel=args.radio)
            except Exception as e:
                print(f'Failed to encode: {e}.', file=sys.stderr)
                continue

            # write result
            sys.stdout.writelines(encoded)
            sys.stdout.write('\n')
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

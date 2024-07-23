"""
The following example shows how to read and parse AIS messages from a file.

When reading a file, the following things are important to know:

- lines that begin with a `#` are ignored
- invalid messages are skipped
- invalid lines are skipped
"""
import pathlib
import re
from typing import Tuple, Any

from pyais.stream import FileReaderStream

filename = pathlib.Path(__file__).parent.joinpath('sample.ais')

for message in FileReaderStream(str(filename)):
    print(message.decode())

# Create a custom parsing function:
# - NMEA message must be always in the first position
# - Always consider that the NMEA message are bytes when parsing
# - The metadata field can be also parsed during the process: he could
# be anything (string, float, datetime, etc.)
def parse_function(msg: bytes) -> Tuple[bytes, Any]:
    nmea_message = re.search(b'.* (.*)', msg).group(1)  # NMEA
    metadata = re.search(b'(.*) .*', msg).group(1)  # Metadata

    return nmea_message, metadata


filename = pathlib.Path(__file__).parent.joinpath('enhanced_sample.ais')

for message, infos in FileReaderStream(str(filename), parse_function):
    print(infos, message.decode())

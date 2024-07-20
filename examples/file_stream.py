"""
The following example shows how to read and parse AIS messages from a file.

When reading a file, the following things are important to know:

- lines that begin with a `#` are ignored
- invalid messages are skipped
- invalid lines are skipped
"""
import pathlib
import re
from typing import Tuple, Union

from pyais.stream import FileReaderStream

filename = pathlib.Path(__file__).parent.joinpath('sample.ais')

for message in FileReaderStream(str(filename)):
    print(message.decode())


def parse_function(msg: Union[str, bytes], encoding: str = 'utf-8') -> Tuple[bytes, str]:
    if isinstance(msg, bytes):
        msg = msg.decode(encoding)
    nmea_message = re.search(".* (.*)", msg).group(1)  # NMEA
    metadata = re.search("(.*) .*", msg).group(1)  # Metadata

    return bytes(nmea_message, encoding), metadata


filename = pathlib.Path(__file__).parent.joinpath('enhanced_sample.ais')

for message, infos in FileReaderStream(str(filename), parse_function):
    print(infos, message.decode())

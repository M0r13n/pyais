"""
The following example shows how to read and parse AIS messages from a file.

When reading a file, the following things are important to know:

- lines that begin with a `#` are ignored
- invalid messages are skipped
- invalid lines are skipped
"""
import pathlib

from pyais.stream import FileReaderStream

filename = pathlib.Path(__file__).parent.joinpath('sample.ais')

with FileReaderStream(str(filename)) as stream:
    for msg in stream:
        decoded = msg.decode()
        print(decoded)

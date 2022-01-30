"""
The following example shows how to read and parse AIS messages from a file.

When reading a file, the following things are important to know:

- lines that begin with a `#` are ignored
- invalid messages are skipped
- invalid lines are skipped
"""
from pyais.stream import FileReaderStream

filename = "sample.ais"

for msg in FileReaderStream(filename):
    decoded = msg.decode()
    print(decoded)

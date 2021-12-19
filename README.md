# pyais

[![PyPI](https://img.shields.io/pypi/v/pyais)](https://pypi.org/project/pyais/)
[![license](https://img.shields.io/pypi/l/pyais)](https://github.com/M0r13n/pyais/blob/master/LICENSE)
[![codecov](https://codecov.io/gh/M0r13n/pyais/branch/master/graph/badge.svg)](https://codecov.io/gh/M0r13n/pyais)
[![downloads](https://img.shields.io/pypi/dm/pyais)](https://pypi.org/project/pyais/)
![CI](https://github.com/M0r13n/pyais/workflows/CI/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/pyais/badge/?version=latest)](https://pyais.readthedocs.io/en/latest/?badge=latest)

AIS message encoding and decoding. 100% pure Python. Supports AIVDM/AIVDO messages. Supports single messages, files and
TCP/UDP sockets.

You can find the full documentation on [readthedocs](https://pyais.readthedocs.io/en/latest/).

# Acknowledgements

![Jetbrains Logo](./docs/jetbrains_logo.svg)

This project is a grateful recipient of
the [free Jetbrains Open Source sponsorship](https://www.jetbrains.com/?from=pyais). Thank you. 🙇

# General

This module contains functions to decode and parse Automatic Identification System (AIS) serial messages. For detailed
information about AIS refer to
the [AIS standard](https://en.wikipedia.org/wiki/Automatic_identification_system#Message_format).

# Features/Improvements

I open to any form of idea to further improve this library. If you have an idea or a feature request - just open an
issue. :-)

# Installation

The project is available at Pypi:

```shell
$ pip install pyais
```

# Usage

Using this module is easy. If you want to parse a file, that contains AIS messages, just copy the following code and
replace `filename` with your desired filename.

```python
from pyais import FileReaderStream

filename = "sample.ais"

for msg in FileReaderStream(filename):
    decoded_message = msg.decode()
    ais_content = decoded_message.content
```

It is possible to directly convert messages into JSON.

```python
from pyais import TCPStream

for msg in TCPStream('ais.exploratorium.edu'):
    json_data = msg.decode().to_json()
```

You can also parse a single message encoded as bytes or from a string:

```python
from pyais import NMEAMessage, decode_msg

message = NMEAMessage(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")
message = NMEAMessage.from_string("!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")

# or newer 

msg = decode_msg("!AIVDM,1,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
msg = decode_msg(b"!AIVDM,1,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")

```

See the example folder for more examples.

Another common use case is the reception of messages via UDP. This lib comes with an `UDPStream` class that enables just
that. This stream class also handles out-of-order delivery of messages, which can occur when using UDP.

```py
from pyais.stream import UDPStream

host = "127.0.0.1"
port = 55555

for msg in UDPStream(host, port):
    msg.decode()
    # do something with it

```

## Encode

It is also possible to encode messages.

| :exclamation:  Every message needs at least a single keyword argument: `mmsi`. All other fields have most likely default values. |
|----------------------------------------------------------------------------------------------------------------------------------|

### Encode data using a dictionary

You can pass a dict that has a set of key-value pairs:

- use `from pyais.encode import encode_dict` to import `encode_dict` method
- it takes a dictionary of data and some NMEA specific kwargs and returns the NMEA 0183 encoded AIS sentence.
- only keys known to each message are considered
    - other keys are simply omitted
    - you can get list of available keys by looking at pyais/encode.py
    - you can also call `MessageType1.fields()` to get a list of fields programmatically for each message
- every message needs at least two keyword arguments:
    - `mmsi` the MMSI number to encode
    - `type` or `msg_type` the type of the message to encode (1-27)

**NOTE:**
This method takes care of splitting large payloads (larger than 60 characters)
into multiple sentences. With a total of 80 maximum chars excluding end of line per sentence, and 20 chars head + tail
in the nmea 0183 carrier protocol, 60 chars remain for the actual payload. Therefore, it returns a list of messages.

```py
from pyais.encode import encode_dict

data = {
    'course': 219.3,
    'lat': 37.802,
    'lon': -122.341,
    'mmsi': '366053209',
    'type': 1,
}
# This will create a type 1 message for the MMSI 366053209 with lat, lon and course values specified above
encoded = encode_dict(data, radio_channel="B", talker_id="AIVDM")[0]
```

### Create a message directly

It is also possible to create messages directly and pass them to `encode_payload`.

```py
from pyais.encode import MessageType5, encode_payload

payload = MessageType5.create(mmsi="123", shipname="Titanic", callsign="TITANIC", destination="New York")
encoded = encode_payload(payload)
print(encoded)
```

# Commandline utility

If you install the library a commandline utility is installed to your PATH. This commandline interface offers access to
common actions like decoding single messages, reading from files or connection to sockets.

```shell
$ ais-decode --help
usage: ais-decode [-h] [-f [IN_FILE]] [-o OUT_FILE] {socket,single} ...

AIS message decoding. 100% pure Python.Supports AIVDM/AIVDO messages. Supports single messages, files and TCP/UDP sockets.rst.

positional arguments:
  {socket,single}

optional arguments:
  -h, --help            show this help message and exit
  -f [IN_FILE], --file [IN_FILE]
  -o OUT_FILE, --out-file OUT_FILE

```

### Decode messages passed as arguments

Because there are some special characters in AIS messages, you need to pass the arguments wrapped in single quotes ('').
Otherwise, you may encounter weird issues with the bash shell.

```shell
$ ais-decode single '!AIVDM,1,1,,A,15NPOOPP00o?b=bE`UNv4?w428D;,0*24'
{'type': 1, 'repeat': 0, 'mmsi': '367533950', 'status': <NavigationStatus.UnderWayUsingEngine: 0>, 'turn': -128, 'speed': 0.0, 'accuracy': True, 'lon': -122.40823166666667, 'lat': 37.808418333333336, 'course': 360.0, 'heading': 511, 'second': 34, 'maneuver': <ManeuverIndicator.NotAvailable: 0>, 'raim': True, 'radio': 34059}
```

### Decode messages from stdin

The program reads content from STDIN by default. So you can use it like grep:

```shell
$ cat tests/ais_test_messages | ais-decode
{'type': 1, 'repeat': 0, 'mmsi': '227006760', 'status': <NavigationStatus.UnderWayUsingEngine: 0>, 'turn': -128, 'speed': 0.0, 'accuracy': False, 'lon': 0.13138, 'lat': 49.47557666666667, 'course': 36.7, 'heading': 511, 'second': 14, 'maneuver': <ManeuverIndicator.NotAvailable: 0>, 'raim': False, 'radio': 22136}
{'type': 1, 'repeat': 0, 'mmsi': '205448890', 'status': <NavigationStatus.UnderWayUsingEngine: 0>, 'turn': -128, 'speed': 0.0, 'accuracy': True, 'lon': 4.419441666666667, 'lat': 51.237658333333336, 'course': 63.300000000000004, 'heading': 511, 'second': 15, 'maneuver': <ManeuverIndicator.NotAvailable: 0>, 'raim': True, 'radio': 2248}
{'type': 1, 'repeat': 0, 'mmsi': '000786434', 'status': <NavigationStatus.UnderWayUsingEngine: 0>, 'turn': -128, 'speed': 1.6, 'accuracy': True, 'lon': 5.320033333333333, 'lat': 51.967036666666665, 'course': 112.0, 'heading': 511, 'second': 15, 'maneuver': <ManeuverIndicator.NoSpecialManeuver: 1>, 'raim': False, 'radio': 153208}
...
```

It is possible to read from a file by using the `-f` option

```shell
$ ais-decode -f tests/ais_test_messages 
{'type': 1, 'repeat': 0, 'mmsi': '227006760', 'status': <NavigationStatus.UnderWayUsingEngine: 0>, 'turn': -128, 'speed': 0.0, 'accuracy': False, 'lon': 0.13138, 'lat': 49.47557666666667, 'course': 36.7, 'heading': 511, 'second': 14, 'maneuver': <ManeuverIndicator.NotAvailable: 0>, 'raim': False, 'radio': 22136}
{'type': 1, 'repeat': 0, 'mmsi': '205448890', 'status': <NavigationStatus.UnderWayUsingEngine: 0>, 'turn': -128, 'speed': 0.0, 'accuracy': True, 'lon': 4.419441666666667, 'lat': 51.237658333333336, 'course': 63.300000000000004, 'heading': 511, 'second': 15, 'maneuver': <ManeuverIndicator.NotAvailable: 0>, 'raim': True, 'radio': 2248}
```

### Decode from socket

By default the program will open a UDP socket

```shell
$ ais-decode socket localhost 12345
```

but you can also connect to a TCP socket by setting the `-t tcp` parameter.

```shell
$ ais-decode socket localhost 12345 -t tcp
```

### Write content to file

By default, the program writes it's output to STDOUT. But you can write to a file by passing the `-o` option. You need
to add this option before invoking any of the subcommands, due to the way `argparse` parses it's arguments.

```shell
$ ais-decode -o /tmp/some_file.tmp single '!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07' '!AIVDM,2,2,1,A,F@V@00000000000,2*35' 

# This is same as redirecting the output to a file

$ ais-decode single '!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07' '!AIVDM,2,2,1,A,F@V@00000000000,2*35' > /tmp/file
```

I also wrote a [blog post about AIS decoding](https://leonrichter.de/posts/pyais/) and this lib.

# Performance Considerations

You may refer to
the [Code Review Stack Exchange question](https://codereview.stackexchange.com/questions/230258/decoding-of-binary-data-ais-from-socket)
. After a some research I decided to use the bitarray module as foundation. This module uses a C extension under the
hood and has a nice user interface in Python. Performance is also great. Decoding
this [sample](https://www.aishub.net/ais-dispatcher) with roughly 85k messages takes **less than 6 seconds** on my
machine. For comparison, the C++ based [libais module](https://github.com/schwehr/libais) parses the same file in \~ 2
seconds.

# Disclaimer

This module is a private project of mine and does not claim to be complete. I try to improve and extend it, but there
may be bugs. If you find such a bug feel free to submit an issue or even better create a pull-request. :-)

# Coverage

Currently, this module is able to decode most message types. There are only a few exceptions. These are messages that
only occur in very rare cases and that you will probably never observe. The module was able to completely decode a 4
hour stream with real-time data from San Francisco Bay Area without any errors or problems. If you find a bug or missing
feature, please create an issue.

# Known Issues

During installation, you may encounter problems due to missing header files. The error looks like this:

````sh
...

    bitarray/_bitarray.c:13:10: fatal error: Python.h: No such file or directory
       13 | #include "Python.h"
          |          ^~~~~~~~~~
    compilation terminated.
    error: command 'x86_64-linux-gnu-gcc' failed with exit status 1

...

````

In order to solve this issue, you need to install header files and static libraries for python dev:

````sh
$ sudo apt install python3-dev
````

# For developers

After you cloned the repo head into the `pyais` base directory.

Then install all dependencies:

```sh
$ pip install .[test]
```

Make sure that all tests pass and that there aren't any issues:

```sh
$ make test
```

Now you are ready to start developing on the project! Don't forget to add tests for every new change or feature!




# pyais
[![PyPI](https://img.shields.io/pypi/v/pyais)](https://pypi.org/project/pyais/)
[![license](https://img.shields.io/pypi/l/pyais)](https://github.com/M0r13n/pyais/blob/master/LICENSE)
[![codecov](https://codecov.io/gh/M0r13n/pyais/branch/master/graph/badge.svg)](https://codecov.io/gh/M0r13n/pyais)
[![downloads](https://img.shields.io/pypi/dm/pyais)](https://pypi.org/project/pyais/)
![CI](https://github.com/M0r13n/pyais/workflows/CI/badge.svg)
  
AIS message decoding. 100% pure Python. Supports AIVDM/AIVDO messages. Supports single messages, files and TCP/UDP sockets.

# Acknowledgements
![Jetbrains Logo](./docs/jetbrains_logo.svg)

This project is a grateful recipient of the [free Jetbrains Open Source sponsorship](https://www.jetbrains.com/?from=pyais). Thank you. 🙇

# General
This module contains functions to decode and parse Automatic Identification System (AIS) serial messages.
For detailed information about AIS refer to the [AIS standard](https://en.wikipedia.org/wiki/Automatic_identification_system#Message_format).

# Installation
The project is available at Pypi:

```shell
$ pip install pyais
```

# Usage
Using this module is easy. If you want to parse a file, that contains AIS messages, just copy the following code and replace `filename` with your desired filename.

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
message = NMEAMessage(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")
message = NMEAMessage.from_string("!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")
```

See the example folder for more examples.

Another common use case is the reception of messages via UDP.
This lib comes with an `UDPStream` class that enables just that. 
This stream class also handles out-of-order delivery of messages, which can occur when using UDP.

```py
from pyais.stream import UDPStream

host = "127.0.0.1"
port = 55555

for msg in UDPStream(host, port):
    msg.decode()
    # do something with it

```

# Commandline utility
If you install the library a commandline utility is installed to your PATH. This commandline interface offers access to common actions like decoding single messages, reading from files or connection to sockets.

```shell
$ ais-decode --help
usage: ais-decode [-h] [-f [IN_FILE]] [-o OUT_FILE] {socket,single} ...

AIS message decoding. 100% pure Python.Supports AIVDM/AIVDO messages. Supports single messages, files and TCP/UDP sockets.

positional arguments:
  {socket,single}

optional arguments:
  -h, --help            show this help message and exit
  -f [IN_FILE], --file [IN_FILE]
  -o OUT_FILE, --out-file OUT_FILE

```
I also wrote a [blog post about AIS decoding](https://leonrichter.de/posts/pyais/) and this lib. 

# Performance Considerations
You may refer to the [Code Review Stack Exchange question](https://codereview.stackexchange.com/questions/230258/decoding-of-binary-data-ais-from-socket).
After a some research I decided to use the bitarray module as foundation.
This module uses a C extension under the hood and has a nice user interface in Python.
Performance is also great.
Decoding this [sample](https://www.aishub.net/ais-dispatcher) with roughly 85k messages takes **less than 6 seconds** on my machine.
For comparison, the C++ based [libais module](https://github.com/schwehr/libais) parses the same file in \~ 2 seconds. 

# Disclaimer
This module is a private project of mine and does not claim to be complete. I try to improve and extend it, but there may be bugs. If you find such a bug feel free to submit an issue or even better create a pull-request. :-)

# Coverage
Currently, this module is able to decode most message types. There are only a few exceptions. These are messages that only occur in very rare cases and that you will probably never observe. The module was able to completely decode a 4 hour stream with real-time data from San Francisco Bay Area without any errors or problems. If you find a bug or missing feature, please create an issue.


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

In  order to solve this issue, you need to install header files and static libraries for python dev:

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




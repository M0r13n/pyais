# pyais
[![codecov](https://codecov.io/gh/M0r13n/pyais/branch/master/graph/badge.svg)](https://codecov.io/gh/M0r13n/pyais)
  
AIS message decoding. 100% pure Python.

# General
This module contains functions to decode and parse Automatic Identification System (AIS) serial messages.
For detailed information about AIS refer to the [AIS standard](https://en.wikipedia.org/wiki/Automatic_identification_system#Message_format).

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
Currently this module is able to decode most message types. There are only a few exceptions. These are messages that only occur in very rare cases and that you will probably never observe. The module was able to completely decode a 4 hour stream with real-time data from San Francisco Bay Area without any errors or problems. If you find a bug or missing feature, please create an issue.

# Tests
You should run all tests before you submit a new pull request to prevent regressions. Also run flake8.

**Without Coverage**
- `python -m unittest discover tests && flake8`

**With Coverage**
- `pip install coverage`
- `coverage run --source=pyais -m unittest discover tests && coverage report -m && flake8`




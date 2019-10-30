# pyais

AIS message decoding in Python.

# General
This module contains functions to decode and parse Automatic Identification System (AIS) serial messages.
For detailed information about AIS refer to the [AIS standard](https://en.wikipedia.org/wiki/Automatic_identification_system#Message_format).

Data is read from a TCP socket and then decoded into a bitarray. 
Note that AIS messages are encoded in [6-bit character code](https://en.wikipedia.org/wiki/Six-bit_character_code).
The respective message is then decoded depending on its Message-ID.
Therefore the bitarray is sliced and it's individual parts are converted into their required data type (mostly int).

Decoded data is returned as a dictionary. Depending on what kind of data is being decoded,
additional context will be added. Such entries will not just contain an single value,
but rather a tuple of values. A simple, reduced example could look like this:
```python
{
    'type': 1, # single value without additional context
    'status': (0, 'Under way using engine'), # tuple of value and context
}
```

# Performance Considerations
You may refer to the [Code Review Stack Exchange question](https://codereview.stackexchange.com/questions/230258/decoding-of-binary-data-ais-from-socket).

Using native python strings and converting each substring into an integer:
- Decoding #8000 messages takes ~ 0.90 seconds  


Using bitstring's BitArray and slicing:
- Decoding #8000 AIS messages takes ~ 2.5 seconds 

Using the bitarray module:
- Decoding #8000 AIS messages takes ~ 0.25 seconds 

# Performance Considerations
This module is a private project and does not claim to be complete.
My primary focus is on readability and maintainability.

# Tests

**Without Coverage**
- `python -m unittest discover tests`

**With Coverage**
- `pip install coverage`
- `coverage run --source=pyais -m unittest discover tests && coverage report -m`




"""
Decoding AIS messages in Python

General:
----------------------------------------------------

This module contains functions to decode and parse Automatic
Identification System (AIS) serial messages.

Each message has it's own, unique form and thus is treated individually.

Incoming data is converted from normal 8-bit ASCII into a 6-bit binary string.
Each binary string is then decoded according to it's message id.
Decoding is performed by a function of the form decode_msg_XX(bit_string),
where XX is the message id.

Decoded data is returned as a dictionary. Depending on what kind of data is being decoded,
additional context will be added. Such entries will not just contain an single value,
but rather a tuple of values. E.g:

{
'type': 1, # single value without additional context
...
'status': (0, 'Under way using engine'), # tuple of value and context
...
}

Performance considerations:
----------------------------------------------------

Even though performance is not my primary concern, the code shouldn't be too slow.
I tried a few different straight forward approaches for decoding the messages
and compared their performance:

Using native python strings and converting each substring into an integer:
    -> Decoding #8000 messages takes 0.80 seconds

Using bitstring's BitArray and slicing:
    -> Decoding #8000 AIS messages takes 2.5 seconds

Using the bitarray module:
    -> because their is not native to_int method, the code gets utterly cluttered


Note:
----------------------------------------------------
This module is a private project and does not claim to be complete.
Nor has it been designed to be extremely fast or memory efficient.
My primary focus is on readability and maintainability.

The terms message id and message type are used interchangeably and mean the same.
"""


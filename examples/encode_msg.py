"""
The following example shows how to create an AIS message using a dictionary of values.

The full specification of the AIVDM/AIVDO protocol is out of the scope of this example.
For a good overview of the AIVDM/AIVDO Sentence Layer please refer to this project: https://gpsd.gitlab.io/gpsd/AIVDM.html#_aivdmaivdo_sentence_layer

But you should keep the following things in mind:

- AIS messages are part of a two layer protocol
- the outer layer is the NMEA 0183 data exchange format
- the actual AIS message is part of the NMEA 0183’s 82-character payload
- because some AIS messages are larger than 82 characters they need to be split across several fragments
- there are 27 different types of AIS messages which differ in terms of fields

Now to the actual encoding of messages: It is possible to create a payload class and encode it.

For the following example, let's assume that we want to create a type 1 AIS message.
"""
# Required imports
from pyais.encode import encode_msg
from pyais.messages import MessageType1

# You do not need to pass every attribute to the class.
# All field other than `mmsi` do have default values.
msg = MessageType1.create(course=219.3, lat=37.802, lon=-122.341, mmsi='366053209')

# WARNING: If you try to instantiate the class directly (without using .create())
# you need to pass all attributes, as no default values are used.

# This creates an encoded AIS message
# Note, that `encode_msg` returns always a list of fragments.
# This is done, because you may never know if a message fits into the 82 character
# size limit of payloads
encoded = encode_msg(msg)
print(encoded)

# You can also change the NMEA fields like the radio channel:
print(encode_msg(msg, radio_channel="B"))

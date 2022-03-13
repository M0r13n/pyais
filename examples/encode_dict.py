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

Now to the actual encoding of messages: It is possible to encode a dictionary of values into an AIS message.
To do so, you need some values that you want to encode. The keys need to match the interface of the actual message.
You can call `.fields()` on any message class, to get glimpse on the available fields for each message type.
Unknown keys in the dict are simply omitted by pyais. Most keys have default values and do not need to
be passed explicitly. Only the keys `type` and `mmsi` are always required

For the following example, let's assume that we want to create a type 1 AIS message.
"""
# Required imports
from pyais.encode import encode_dict
from pyais.messages import MessageType1

# This statement tells us which fields can be set for messages of type 1
print(MessageType1.fields())

# A dictionary of fields that we want to encode
# Note that you can pass many more fields for type 1 messages, but we let pyais
# use default values for those keys
data = {
    'course': 219.3,
    'lat': 37.802,
    'lon': -122.341,
    'mmsi': '366053209',
    'type': 1
}

# This creates an encoded AIS message
# Note, that `encode_dict` returns always a list of fragments.
# This is done, because you may never know if a message fits into the 82 character
# size limit of payloads
encoded = encode_dict(data)
print(encoded)

# You can also change the NMEA fields like the radio channel:
print(encode_dict(data, radio_channel="B"))

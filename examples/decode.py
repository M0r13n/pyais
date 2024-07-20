import re
from typing import Tuple, Union
from pyais import decode, IterMessages

# Decode a single part using decode
decoded = decode(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
print(decoded)

parts = [
    b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08",
    b"!AIVDM,2,2,4,A,000000000000000,2*20",
]

# Decode a multipart message using decode
decoded = decode(*parts)
print(decoded)

# Decode a string
decoded = decode("!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
print(decoded)

# Decode to dict
decoded = decode("!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
as_dict = decoded.asdict()
print(as_dict)

# Decode to json
decoded = decode("!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
json = decoded.to_json()
print(json)

# It does not matter if you pass a string or bytes
decoded_b = decode(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
decoded_s = decode("!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
assert decoded_b == decoded_s

# Lets say you have some kind of stream of messages. Then you can use `IterMessages` to decode the messages:
fake_stream = [
    b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23",
    b"!AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F",
    b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B",
    b"!AIVDM,1,1,,B,13eaJF0P00Qd388Eew6aagvH85Ip,0*45",
    b"!AIVDM,1,1,,A,14eGrSPP00ncMJTO5C6aBwvP2D0?,0*7A",
    b"!AIVDM,1,1,,A,15MrVH0000KH<:V:NtBLoqFP2H9:,0*2F",
]

for message in IterMessages(fake_stream):
    print(message.decode())

# We can also have any king of metadata for each message:
enhanced_fake_stream = [
    b"[2024-07-19 08:45:27.141] !AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23",
    b"[2024-07-19 08:45:30.074] !AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F",
    b"[2024-07-19 08:45:35.007] !AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B",
    b"[2024-07-19 08:45:35.301] !AIVDM,1,1,,B,13eaJF0P00Qd388Eew6aagvH85Ip,0*45",
    b"[2024-07-19 08:45:40.021] !AIVDM,1,1,,A,14eGrSPP00ncMJTO5C6aBwvP2D0?,0*7A",
    b"[2024-07-19 08:45:40.074] !AIVDM,1,1,,A,15MrVH0000KH<:V:NtBLoqFP2H9:,0*2F",
]


# Create a custom parsing function:
# - NMEA message must be always in the first position and in bytes
# - For flexibility purposes, consider cases where the data can be bytes or string
def parse_function(msg: Union[str, bytes], encoding: str = 'utf-8') -> Tuple[bytes, str]:
    if isinstance(msg, bytes):
        msg = msg.decode(encoding)
    nmea_message = re.search(".* (.*)", msg).group(1)  # NMEA
    metadata = re.search("(.*) .*", msg).group(1)  # Metadata

    return bytes(nmea_message, encoding), metadata


for message, infos in IterMessages(enhanced_fake_stream, parse_function):
    print(infos, message.decode())

# Whatever if the data are bytes or strings
enhanced_fake_stream = [
    "[2024-07-19 08:45:27.141] !AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23",
    "[2024-07-19 08:45:30.074] !AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F",
    "[2024-07-19 08:45:35.007] !AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B",
    "[2024-07-19 08:45:35.301] !AIVDM,1,1,,B,13eaJF0P00Qd388Eew6aagvH85Ip,0*45",
    "[2024-07-19 08:45:40.021] !AIVDM,1,1,,A,14eGrSPP00ncMJTO5C6aBwvP2D0?,0*7A",
    "[2024-07-19 08:45:40.074] !AIVDM,1,1,,A,15MrVH0000KH<:V:NtBLoqFP2H9:,0*2F",
]

for message, infos in IterMessages.from_strings(enhanced_fake_stream, parse_function):
    print(infos, message.decode())

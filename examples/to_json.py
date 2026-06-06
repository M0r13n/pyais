"""This example shows how to decode AIS messages and how to convert them to JSON.
It also shows how to re-encode these messages back to NMEA AIS sentences."""

import json
import pathlib

from pyais import decode, encode_dict, FileReaderStream
from pyais.util import json_to_data

# Decode a single message
orig = b"!AIVDO,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*45"
decoded = decode(orig)

# Convert it to JSON (including spare fields).
# {"msg_type": 8, "mmsi": 366999712, ...}
json_str = decoded.to_json(ignore_spare=False)

# Re-encode the JSON in a NMEA AIS sentence.
# NOTE: json_to_data decodes string fields produced by to_json back into bytes.
# [!AIVDO,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*45]
nmea_ais = encode_dict(json_to_data(json.loads(json_str)))
assert nmea_ais[0].encode() == orig

# This does not work because the JSON holds base64-encoded data.
# nmea_ais = encode_dict(json.loads(json_str))

# The same works for files
filename = pathlib.Path(__file__).parent.joinpath('sample.ais')
with FileReaderStream(str(filename)) as stream:
    for nmea_msg in stream:
        json_str = nmea_msg.decode().to_json(ignore_spare=False)
        nmea_ais = encode_dict(
            json_to_data(json.loads(json_str)),
            talker_id=nmea_msg.talker_id,
            sentence_type=nmea_msg.type,
            radio_channel=nmea_msg.channel
        )
        print(nmea_msg.raw, nmea_ais)

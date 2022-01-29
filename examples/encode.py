from pyais.encode import MessageType5, encode_msg

from pyais.encode import encode_dict

data = {
    'course': 219.3,
    'lat': 37.802,
    'lon': -122.341,
    'mmsi': '366053209',
    'type': 1
}
encoded = encode_dict(data, radio_channel="B", talker_id="AIVDM")[0]

# It is also possible to create messages directly and pass them to `encode_payload`
payload = MessageType5.create(mmsi="123", shipname="Titanic", callsign="TITANIC", destination="New York")
encoded = encode_msg(payload)
print(encoded)

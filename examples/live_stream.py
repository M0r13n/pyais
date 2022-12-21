"""
The Norwegian Coastal Administration offers real-time AIS data.
This live feed can be accessed via TCP/IP without prior registration.
The AIS data is freely available under the norwegian license for public data:

- https://data.norge.no/nlod/no/1.0
- https://kystverket.no/navigasjonstjenester/ais/tilgang-pa-ais-data/

Data can be read from a TCP/IP socket and is encoded according to IEC 62320-1:

- IP:   153.44.253.27
- Port: 5631
"""
from pyais.stream import TCPConnection

host = '153.44.253.27'
port = 5631

for msg in TCPConnection(host, port=port):
    decoded_message = msg.decode()
    ais_content = decoded_message

    print('*' * 80)
    if msg.tag_block:
        # decode & print the tag block if it is available
        msg.tag_block.init()
        print(msg.tag_block.asdict())

    print(ais_content)

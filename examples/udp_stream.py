"""
This example shows how to list for incoming UDP packets.

Pro-Tip: Start the UDP mock sender in a new terminal instance: `python tests/mock_sender.py`

Afterwards, run this file, and you should receive some looped AIS messages.
"""
from pyais.stream import UDPReceiver

host = "127.0.0.1"
port = 12346

for msg in UDPReceiver(host, port):
    print(msg.decode())
    # do something with it

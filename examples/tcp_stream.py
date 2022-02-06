"""
The following example shows how to decode AIS messages from a TCP socket.

Pro-Tip: You can start a simple server that loops over some messages in order to test
this file. Just open a new terminal instance and run: `python tests/mock_server.py`
"""
from pyais.stream import TCPConnection

url = '127.0.0.1'
port = 12346

for msg in TCPConnection(url, port=port):
    decoded_message = msg.decode()
    ais_content = decoded_message
    print(ais_content)
    # Do something with the AIS message

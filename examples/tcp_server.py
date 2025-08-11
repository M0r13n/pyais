"""This example shows how to create a TCP server that accepts
a remote connection. The client is expected to initiate a TCP
connection.

You could use the following command to create a client in your terminal:

> nc 153.44.253.27 5631 | ais-decode --json | jq -c | ais-encode --mode stream | nc localhost 5678
"""
from pyais.stream import TCPServer

HOST = "0.0.0.0"
PORT = 5678


# Accept an arbitrary number of clients
with TCPServer(HOST, PORT) as server:
    for i, msg in enumerate(server, 1):
        print(i, msg)

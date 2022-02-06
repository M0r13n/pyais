#####################
Reading from sockets
#####################


Examples
--------

Connect to a TCP socket::

    from pyais.stream import TCPConnection

    url = '127.0.0.1'
    port = 12346

    for msg in TCPConnection(url, port=port):
        decoded_message = msg.decode()
        ais_content = decoded_message
        print(ais_content)
        # Do something with the AIS message


Open to a UDP socket::

    from pyais.stream import UDPReceiver

    host = "127.0.0.1"
    port = 12346

    for msg in UDPReceiver(host, port):
        print(msg.decode())
        # do something with it

The UDP stream handles out of order delivery of messages. By default it keeps the last up to 10.000 messages in memory to search for multiline messages.

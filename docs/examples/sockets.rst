#####################
Reading from sockets
#####################


Examples
--------

Connect to a TCP socket::

    from pyais.stream import TCPStream

    url = 'ais.exploratorium.edu'
    port = 80

    for msg in TCPStream(url, port=80):
        decoded_message = msg.decode()
        ais_content = decoded_message.content
        print(ais_content)
        # Do something with the ais message


Connect to a UDP socket::

    from pyais.stream import UDPStream

    host = "127.0.0.1"
    port = 55555

    for msg in UDPStream(host, port):
        msg.decode()
        # do something with it

The UDP stream handles out of order delivery of messages. By default it keeps the last up to 10.000 messages in memory to search for multiline messages.

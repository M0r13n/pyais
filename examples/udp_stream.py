from pyais.stream import UDPStream

host = "127.0.0.1"
port = 55555

for msg in UDPStream(host, port):
    msg.decode()
    # do something with it

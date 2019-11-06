from pyais.stream import TCPStream

url = 'ais.exploratorium.edu'
port = 80

for msg in TCPStream(url, port=80):
    decoded_message = msg.decode()
    ais_content = decoded_message.content
    print(ais_content)
    # Do something with the ais message

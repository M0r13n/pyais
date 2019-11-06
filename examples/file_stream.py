from pyais.stream import FileReaderStream

filename = "sample.ais"

for msg in FileReaderStream(filename):
    decoded_message = msg.decode()
    ais_content = decoded_message.content
    # Do something with the ais message

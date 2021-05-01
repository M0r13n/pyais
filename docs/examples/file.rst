###############
Reading and parsing files
###############


Examples
--------

Parse a file::

    from pyais.stream import FileReaderStream

    filename = "sample.ais"

    for msg in FileReaderStream(filename):
        decoded_message = msg.decode()
        ais_content = decoded_message.content
        # Do something with the ais message


Please note, that by default the following lines are ignored:

* invalid lines
* lines starting with a `#`
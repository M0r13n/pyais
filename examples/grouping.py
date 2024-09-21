from pyais.stream import FileReaderStream, TagBlockQueue
import pathlib

filename = pathlib.Path(__file__).parent.joinpath('sample.ais')

# To track NMEA 4.10 tag block groups a queue is required.
# This queue buffers NMEA sentences belonging until the group is complete.
# NOTE: get_nowait will return NMEA sentences - NOT AIS sentences!
tbq = TagBlockQueue()

with FileReaderStream(str(filename), tbq=tbq) as stream:
    for msg in stream:
        while not tbq.empty():
            print(tbq.get_nowait())

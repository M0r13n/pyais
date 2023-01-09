"""Simple benchmark to check the efficient of the AISTracker class"""
import pathlib
import time

from pyais.stream import FileReaderStream
from pyais.exceptions import UnknownMessageException
from pyais.tracker import AISTracker

filename = pathlib.Path(__file__).parent.joinpath('../tests/nmea-sample')
tracker = AISTracker(ttl_in_seconds=0.1)

start = time.time()
for i, msg in enumerate(FileReaderStream(str(filename)), start=1):
    try:
        tracker.update(msg)
    except UnknownMessageException as e:
        print(str(e))

finish = time.time()

print('total messages:', i)  # 82758
print('total tracks:', len(tracker.tracks))  # 11075
print('total seconds:', finish - start)

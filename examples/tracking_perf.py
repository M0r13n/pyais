"""Simple benchmark to check the efficient of the AISTracker class"""
import pathlib
import time

from pyais.stream import FileReaderStream
from pyais.exceptions import UnknownMessageException
from pyais.tracker import AISTracker

filename = pathlib.Path(__file__).parent.joinpath('../tests/nmea-sample')
tracker = AISTracker(ttl_in_seconds=0.01, stream_is_ordered=True)

start = time.time()
with FileReaderStream(str(filename)) as stream:
    for i, msg in enumerate(stream, start=1):
        try:
            tracker.update(msg)
            _ = tracker.n_latest_tracks(50)
        except UnknownMessageException as e:
            print(str(e))

finish = time.time()

print('total messages:', i)  # 82758
print('total tracks:', len(tracker.tracks))  # 11075
print('total seconds:', finish - start)

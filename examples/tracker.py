import pathlib

from pyais import AISTracker
from pyais.stream import FileReaderStream

filename = pathlib.Path(__file__).parent.joinpath('sample.ais')

with FileReaderStream(str(filename)) as stream:
    with AISTracker() as tracker:
        for msg in stream:
            tracker.update(msg)
            latest_tracks = tracker.n_latest_tracks(10)

# Get the latest 10 tracks
print('latest 10 tracks', ','.join(str(t.mmsi) for t in latest_tracks))

# Get a specific track
print(tracker.get_track(249191000))

import pyais
from pyais.tracker import AISTrackEvent

host = '153.44.253.27'
port = 5631


def handle_create(track):
    print('create', track.mmsi)


def handle_update(track):
    print('update', track.mmsi)


def handle_delete(track):
    print('delete', track.mmsi)


with pyais.AISTracker() as tracker:
    tracker.register_subscriber(AISTrackEvent.CREATED, handle_create)
    tracker.register_subscriber(AISTrackEvent.UPDATED, handle_update)
    tracker.register_subscriber(AISTrackEvent.DELETED, handle_delete)

    for msg in pyais.TCPConnection(host, port=port):
        tracker.update(msg)
        latest_tracks = tracker.n_latest_tracks(10)

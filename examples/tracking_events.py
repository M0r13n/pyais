"""This example shows how to register event listeners as callbacks,
so that you are is instantly notified whenever a track is created, updated, or deleted."""
import pyais
from pyais.tracker import AISTrackEvent

host = '153.44.253.27'
port = 5631


def handle_create(track):
    # called every time an AISTrack is created
    print('create', track.mmsi)


def handle_update(track):
    # called every time an AISTrack is updated
    print('update', track.mmsi)


def handle_delete(track):
    # called every time an AISTrack is deleted (pruned)
    print('delete', track.mmsi)


with pyais.AISTracker() as tracker:
    tracker.register_callback(AISTrackEvent.CREATED, handle_create)
    tracker.register_callback(AISTrackEvent.UPDATED, handle_update)
    tracker.register_callback(AISTrackEvent.DELETED, handle_delete)

    for msg in pyais.TCPConnection(host, port=port):
        tracker.update(msg)
        latest_tracks = tracker.n_latest_tracks(10)

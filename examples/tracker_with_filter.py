import pathlib
from pyais.filter import (
    AttributeFilter,
    FilterChain,
    MessageTypeFilter,
    NoneFilter
)
from pyais.stream import FileReaderStream
from pyais import AISTracker

# Define the filter chain with various criteria
chain = FilterChain([
    # Filter out messages based on the 'turn' attribute or lack thereof
    AttributeFilter(lambda x: not hasattr(x, 'turn') or x.turn == -128.0),

    # Ensure 'lon', 'lat', and 'mmsi2' attributes are not None
    NoneFilter('lon', 'lat'),

    # Include only messages of type 1, 2, or 3
    MessageTypeFilter(1, 2, 3),
])

filename = pathlib.Path(__file__).parent.joinpath('sample.ais')

with FileReaderStream(str(filename)) as stream:
    with AISTracker() as tracker:
        for ais_msg in chain.filter(stream):
            # Only messages that pass this filter chain are printed
            tracker.update(ais_msg)
            latest_tracks = tracker.n_latest_tracks(10)
            print(latest_tracks)

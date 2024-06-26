from pyais.filter import (
    AttributeFilter,
    DistanceFilter,
    FilterChain,
    GridFilter,
    MessageTypeFilter,
    NoneFilter
)
from pyais.stream import TCPConnection

# Define the filter chain with various criteria
chain = FilterChain([
    # Filter out messages based on the 'turn' attribute or lack thereof
    AttributeFilter(lambda x: not hasattr(x, 'turn') or x.turn == -128.0),

    # Ensure 'lon', 'lat', and 'mmsi2' attributes are not None
    NoneFilter('lon', 'lat', 'mmsi2'),

    # Include only messages of type 1, 2, or 3
    MessageTypeFilter(1, 2, 3),

    # Limit messages to within 1000 km of a specific point
    DistanceFilter((51.900, 5.320), distance_km=1000),

    # Restrict messages to a specific geographic grid
    GridFilter(lat_min=50, lon_min=0, lat_max=52, lon_max=5),
])

# Create a stream of ais messages
with TCPConnection('153.44.253.27', port=5631) as ais_stream:
    for ais_msg in chain.filter(ais_stream):
        # Only messages that pass this filter chain are printed
        print(ais_msg)

from pyais import decode
from pyais.filter import (
    AttributeFilter,
    DistanceFilter,
    FilterChain,
    GridFilter,
    MessageTypeFilter,
    NoneFilter
)

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

# Example AIS data to filter
data = [
    decode(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05"),
    decode(b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23"),
    decode(b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B"),
    decode(b"!AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F"),
    decode(b"!AIVDM,1,1,,B,13eaJF0P00Qd388Eew6aagvH85Ip,0*45"),
    decode(b"!AIVDM,1,1,,A,14eGrSPP00ncMJTO5C6aBwvP2D0?,0*7A"),
    decode(b"!AIVDM,1,1,,A,15MrVH0000KH<:V:NtBLoqFP2H9:,0*2F"),
    decode(b"!AIVDM,1,1,,A,702R5`hwCjq8,0*6B"),
]

# Filter the data using the defined chain
filtered_data = list(chain.filter(data))

# Print the latitude and longitude of each message that passed the filters
for msg in filtered_data:
    print(msg.lat, msg.lon)

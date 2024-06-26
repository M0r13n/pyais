=========================
AIS Filters Documentation
=========================

AIS filters provide a modular and flexible way to filter AIS (Automatic Identification System) messages based on various criteria such as attributes, message types, geographical boundaries, and more. Filters can be chained together to create complex filtering logic.

Overview
********

The filtering system is built around a series of filter classes, each designed to filter messages based on specific criteria. Filters are chained together using the ``FilterChain`` class, which allows combining multiple filters into a single, sequential filtering process. The system is flexible, allowing for the easy addition or removal of filters from the chain.

**How It Works**

#. **AIS Stream**: Messages are provided as a stream to the filters.
#. **Filter Application**: Each filter in the chain applies its criteria to the stream, passing the messages that meet the criteria to the next filter.
#. **Filter Chain**: The ``FilterChain`` class orchestrates the passing of messages through each filter, from the first to the last.

Filters
*******

1. AttributeFilter
   - **Description**: Filters messages based on a user-defined function.
   - **Usage**: Initialize with a function that takes an AIS message and returns ``True`` if the message should be kept.

2. NoneFilter
   - **Description**: Filters out messages where specified attributes are ``None``.
   - **Usage**: Initialize with the names of attributes that should not be ``None`` in the messages.

3. MessageTypeFilter
   - **Description**: Filters messages based on their type.
   - **Usage**: Initialize with message types to include.

4. DistanceFilter
   - **Description**: Filters messages based on distance from a reference point.
   - **Usage**: Initialize with a reference point (latitude and longitude) and a distance threshold in kilometers.

5. GridFilter
   - **Description**: Filters messages based on whether they fall within a specified geographical grid.
   - **Usage**: Initialize with the boundaries of the grid (minimum and maximum latitude and longitude).

Utility Functions
*****************

1. Haversine
   - **Description**: Calculates the great circle distance between two points on the Earth.
   - **Parameters**: Takes two tuples representing the latitude and longitude of each point.
   - **Returns**: Distance between the points in kilometers.

2. Is In Grid
   - **Description**: Checks if a point is within a defined geographical grid.
   - **Parameters**: Latitude and longitude of the point and the boundaries of the grid.
   - **Returns**: ``True`` if the point is within the grid, ``False`` otherwise.

FilterChain
***********

- **Description**: Chains multiple filters together into a single filtering process.
- **Usage**: Initialize with a list of filters to be applied in order. The chain can be used to filter a stream of AIS messages.

Example Usage
*************

.. code-block:: python

    from pyais import decode, TCPConnection
    # ... (importing necessary classes)

    # Define and initialize filters
    attribute_filter = AttributeFilter(lambda x: not hasattr(x, 'turn') or x.turn == -128.0)
    none_filter = NoneFilter('lon', 'lat', 'mmsi2')
    message_type_filter = MessageTypeFilter(1, 2, 3)
    distance_filter = DistanceFilter((51.900, 5.320), distance_km=1000)
    grid_filter = GridFilter(lat_min=50, lon_min=0, lat_max=52, lon_max=5)

    # Create a filter chain
    chain = FilterChain([
        attribute_filter,
        none_filter,
        message_type_filter,
        distance_filter,
        grid_filter,
    ])

    # Decode AIS data and filter
    stream = TCPConnection(...)
    filtered_data = chain.filter(stream)

    for msg in filtered_data:
        print(msg.lat, msg.lon)

Conclusion
**********

The AIS filter system provides a powerful and flexible way to filter AIS messages based on a wide range of criteria. By chaining together filters, you can create complex filtering logic tailored to your specific needs.

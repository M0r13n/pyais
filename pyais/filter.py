"""
AIS filters.
A set of filters that allow filtering AIS messages based on different criteria
like attributes, empty values, message types, or geographical boundaries.
Filters can be chained using a FilterChain.
"""

import math
import socket
import typing
import pyais

# Type Aliases for readability
F = typing.TypeVar("F", typing.BinaryIO, socket.socket, None)
AIS_STREAM = pyais.Stream[F]
MESSAGE_STREAM = typing.Generator[pyais.ANY_MESSAGE, None, None]
FILTER_FUNCTION = typing.Callable[[pyais.ANY_MESSAGE], bool]
LAT_LON = typing.Tuple[float, float]  # Tuple type for latitude and longitude


def haversine(latLon1: LAT_LON, latLon2: LAT_LON) -> float:
    """
    Calculate the great circle distance between two points on the earth.

    Parameters:
    latLon1 (LAT_LON): Tuple of latitude and longitude of the first point.
    latLon2 (LAT_LON): Tuple of latitude and longitude of the second point.

    Returns:
    float: Distance between the two points in kilometers.
    """
    R = 6371.0  # Radius of the Earth in km
    lat1, lon1, lat2, lon2 = map(math.radians, [latLon1[0], latLon1[1], latLon2[0], latLon2[1]])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def is_in_grid(lat: float, lon: float, lat_min: float, lon_min: float, lat_max: float, lon_max: float) -> bool:
    """
    Check if a point is within a defined geographical grid.

    Parameters:
    lat, lon (float): Latitude and Longitude of the point to check.
    lat_min, lon_min, lat_max, lon_max (float): Boundaries of the grid.

    Returns:
    bool: True if the point is within the grid, False otherwise.
    """
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


class Filter:
    """
    Base class for all filters.
    """

    def __init__(self) -> None:
        self.next_filter: typing.Optional[Filter] = None

    def set_next(self, filter: 'Filter') -> None:
        """
        Set the next filter in the chain.

        Parameters:
        filter (Filter): The next filter to set.
        """
        self.next_filter = filter

    def filter(self, data: MESSAGE_STREAM) -> MESSAGE_STREAM:
        """
        Apply the filter to the data and then pass it to the next filter.

        Parameters:
        data (MESSAGE_STREAM): The stream of data to filter.

        Returns:
        MESSAGE_STREAM: The filtered data stream.
        """
        data = self.filter_data(data)
        if self.next_filter:
            return self.next_filter.filter(data)
        return data

    def filter_data(self, data: MESSAGE_STREAM) -> MESSAGE_STREAM:
        """
        Abstract method to filter data. Should be implemented by subclasses.

        Parameters:
        data (MESSAGE_STREAM): The stream of data to filter.

        Returns:
        MESSAGE_STREAM: The filtered data stream.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")


class AttributeFilter(Filter):
    """
    Filter based on a user-defined function.
    """

    def __init__(self, ff: FILTER_FUNCTION) -> None:
        """
        Initialize the filter with a user-defined function.

        Parameters:
        ff (FILTER_FUNCTION): A function that takes an AIS message and returns True if the message should be kept.
        """
        super().__init__()
        self.ff = ff

    def filter_data(self, data: MESSAGE_STREAM) -> MESSAGE_STREAM:
        """
        Filter the data based on the user-defined function.

        Parameters:
        data (MESSAGE_STREAM): The stream of data to filter.

        Yields:
        MESSAGE_STREAM: The filtered data stream.
        """
        yield from filter(self.ff, data)


class NoneFilter(Filter):
    """
    Filters messages where specified attributes are not None.
    """

    def __init__(self, *attrs: str) -> None:
        """
        Initialize the filter with attributes to check for None values.

        Parameters:
        attrs (str): Attributes that should not be None in the messages.
        """
        super().__init__()
        self.attrs = attrs

    def filter_data(self, data: MESSAGE_STREAM) -> MESSAGE_STREAM:
        """
        Filter the data, allowing only messages where specified attributes are not None.

        Parameters:
        data (MESSAGE_STREAM): The stream of data to filter.

        Yields:
        MESSAGE_STREAM: The filtered data stream.
        """
        for msg in data:
            if all(getattr(msg, attr, None) is not None for attr in self.attrs):
                yield msg


class MessageTypeFilter(Filter):
    """
    Filters messages based on their type.
    """

    def __init__(self, *types: int) -> None:
        """
        Initialize the filter with message types to include.

        Parameters:
        types (int): Message types that should be included in the filtered data.
        """
        super().__init__()
        self.types = types

    def filter_data(self, data: MESSAGE_STREAM) -> MESSAGE_STREAM:
        """
        Filter the data, allowing only messages of specified types.

        Parameters:
        data (MESSAGE_STREAM): The stream of data to filter.

        Yields:
        MESSAGE_STREAM: The filtered data stream.
        """
        for msg in data:
            if msg.msg_type not in self.types:
                continue
            yield msg


class DistanceFilter(Filter):
    """
    Filters messages based on distance.
    """

    def __init__(self, ref_lat_lon: LAT_LON, distance_km: float) -> None:
        """
        Initialize the filter with a reference point and distance.

        Parameters:
        ref_lat_lon (LAT_LON): Reference latitude and longitude point.
        distance_km (float): Distance threshold in kilometers.
        """
        super().__init__()
        self.ref_lat_lon = ref_lat_lon
        self.distance_km = distance_km

    def filter_data(self, data: MESSAGE_STREAM) -> MESSAGE_STREAM:
        """
        Filter the data based on distance from a reference point.

        Parameters:
        data (MESSAGE_STREAM): The stream of data to filter.

        Yields:
        MESSAGE_STREAM: The filtered data stream.
        """
        for msg in data:
            if hasattr(msg, 'lat'):
                if haversine(self.ref_lat_lon, (msg.lat, msg.lon)) >= self.distance_km:  # type: ignore
                    continue
            yield msg


class GridFilter(Filter):
    """
    Filters messages based on a geographical grid.
    """

    def __init__(self, lat_min: float, lon_min: float, lat_max: float, lon_max: float) -> None:
        """
        Initialize the filter with grid boundaries.

        Parameters:
        lat_min, lon_min, lat_max, lon_max (float): Boundaries of the grid.
        """
        super().__init__()
        self.lat_min = lat_min
        self.lon_min = lon_min
        self.lat_max = lat_max
        self.lon_max = lon_max

    def filter_data(self, data: MESSAGE_STREAM) -> MESSAGE_STREAM:
        """
        Filter the data based on whether it falls within a specified grid.

        Parameters:
        data (MESSAGE_STREAM): The stream of data to filter.

        Yields:
        MESSAGE_STREAM: The filtered data stream.
        """
        for msg in data:
            if hasattr(msg, 'lat'):
                if not is_in_grid(msg.lat, msg.lon, self.lat_min, self.lon_min, self.lat_max, self.lon_max):  # type: ignore
                    continue
            yield msg


class FilterChain:
    """
    Chains multiple filters together.
    """

    def __init__(self, filters: typing.List[Filter]) -> None:
        """
        Initialize the filter chain with a sequence of filters.

        Parameters:
        filters (list of Filter): A list of filters to be applied in order.
        """
        if not filters:
            raise ValueError('At least one filter required')

        # Link filters together in the order provided
        for current, next in zip(filters[:-1], filters[1:]):
            current.set_next(next)

        self.filters = filters
        self.start = filters[0]

    def filter(self, stream: AIS_STREAM[F]) -> MESSAGE_STREAM:
        """
        Apply the chain of filters to the data.

        Parameters:
        stream (AIS_STREAM): The stream of data to filter.

        Yields:
        AIS_STREAM: The filtered data stream.
        """
        yield from self.start.filter(x.decode() for x in stream)

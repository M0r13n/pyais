import pathlib
import unittest
from pyais.filter import AttributeFilter, DistanceFilter, FilterChain, GridFilter, MessageTypeFilter, NoneFilter, haversine
from pyais.stream import FileReaderStream


class MockAISMessage:
    def __init__(self, msg_type=None, lat=None, lon=None, other_attr=None):
        self.msg_type = msg_type
        self.lat = lat
        self.lon = lon
        self.other_attr = other_attr

    def decode(self):
        return self


class TestNoneFilter(unittest.TestCase):
    def test_filtering_none_attributes(self):
        # Setup
        attrs = ['lat', 'lon']  # Attributes to check for None
        filter = NoneFilter(*attrs)
        mock_data = [MockAISMessage(lat=1, lon=1), MockAISMessage(lat=None, lon=1)]

        # Execute
        filtered_data = list(filter.filter_data(mock_data))

        # Assert
        self.assertEqual(len(filtered_data), 1)  # Only one message should pass through the filter

    def test_filtering_missing_attributes(self):
        # Setup - foo is never an attribute
        attrs = ['foo']
        filter = NoneFilter(*attrs)

        # Create mock data with varying attributes: some missing, some None, some with value
        mock_data = [
            MockAISMessage(lat=1, lon=1),  # All attributes present
            MockAISMessage(lat=None, lon=1),  # One attribute is None
            MockAISMessage(other_attr=1)  # Both 'lat' and 'lon' missing
        ]

        # Execute
        filtered_data = list(filter.filter_data(mock_data))

        # Assert
        self.assertEqual(len(filtered_data), 0)


class TestMessageTypeFilter(unittest.TestCase):
    def test_message_type_filtering(self):
        # Setup
        types = [1, 2]  # Message types to include
        filter = MessageTypeFilter(*types)
        mock_data = [MockAISMessage(msg_type=1), MockAISMessage(msg_type=3)]

        # Execute
        filtered_data = list(filter.filter_data(mock_data))

        # Assert
        self.assertEqual(len(filtered_data), 1)  # Only one message of type 1 or 2 should pass through


class TestDistanceFilter(unittest.TestCase):
    def test_distance_filtering(self):
        # Setup
        ref_point = (0, 0)  # Reference point
        distance_km = 1000  # Distance threshold
        filter = DistanceFilter(ref_point, distance_km)
        mock_data = [MockAISMessage(lat=10, lon=10), MockAISMessage(lat=0, lon=0)]  # One within distance, one outside

        # Execute
        filtered_data = list(filter.filter_data(mock_data))

        # Assert
        self.assertEqual(len(filtered_data), 1)  # Only the message within the specified distance should pass through

    def test_all_within_distance(self):
        # Setup: All messages within 100 km of the reference point (0, 0)
        ref_point = (0, 0)  # Reference point
        distance_km = 100  # Distance threshold in kilometers
        filter = DistanceFilter(ref_point, distance_km)
        # Assuming haversine function and distance filter work correctly,
        # these coordinates should be within 100 km of the reference point.
        mock_data = [
            MockAISMessage(lat=0.1, lon=0.1),
            MockAISMessage(lat=0.5, lon=0.5)
        ]

        # Execute: Run the filter
        filtered_data = list(filter.filter_data(mock_data))

        # Assert: Ensure all messages remain
        self.assertEqual(len(filtered_data), len(mock_data))

    def test_none_within_distance(self):
        # Setup: No messages within 100 km of the reference point (0, 0)
        ref_point = (0, 0)  # Reference point
        distance_km = 100  # Distance threshold in kilometers
        filter = DistanceFilter(ref_point, distance_km)
        # Messages far away from the reference point, well beyond 100 km.
        mock_data = [
            MockAISMessage(lat=10, lon=10),
            MockAISMessage(lat=20, lon=20)
        ]

        # Execute: Run the filter
        filtered_data = list(filter.filter_data(mock_data))

        # Assert: Ensure no messages remain
        self.assertEqual(len(filtered_data), 0)

    def test_specific_coordinate_distance(self):
        # Setup
        ref_point = (51.237658, 4.419442)  # Reference point near Antwerp, Belgium
        distance_km = 50  # Distance threshold in kilometers
        filter = DistanceFilter(ref_point, distance_km)
        # Mock data: one message near the reference point, another far away
        mock_data = [
            MockAISMessage(lat=51.2, lon=4.4),  # Near reference point, should be within 50 km
            MockAISMessage(lat=52.5, lon=5.5)   # Far from reference point, should be outside 50 km
        ]

        # Execute: Run the filter
        filtered_data = list(filter.filter_data(mock_data))

        # Assert: Ensure only the near message remains
        self.assertEqual(len(filtered_data), 1)
        self.assertAlmostEqual(filtered_data[0].lat, 51.2, places=1)
        self.assertAlmostEqual(filtered_data[0].lon, 4.4, places=1)


class TestGridFilter(unittest.TestCase):
    def test_grid_filtering(self):
        # Setup
        grid_boundaries = (0, 0, 5, 5)  # Grid boundaries
        filter = GridFilter(*grid_boundaries)
        mock_data = [MockAISMessage(lat=1, lon=1), MockAISMessage(lat=6, lon=6)]  # One inside grid, one outside

        # Execute
        filtered_data = list(filter.filter_data(mock_data))

        # Assert
        self.assertEqual(len(filtered_data), 1)  # Only the message inside the grid should pass through

    def test_central_park_grid(self):
        # Setup: Define a grid covering Central Park in New York City
        lat_min, lon_min = 40.7644, -73.9730  # Southwest corner
        lat_max, lon_max = 40.8005, -73.9580  # Northeast corner
        grid_filter = GridFilter(lat_min, lon_min, lat_max, lon_max)

        # Mock data: one message inside Central Park, another outside
        inside_park = MockAISMessage(lat=40.768, lon=-73.965)  # Inside Central Park
        outside_park = MockAISMessage(lat=40.760, lon=-73.980)  # Outside Central Park

        mock_data = [inside_park, outside_park]

        # Execute: Run the grid filter
        filtered_data = list(grid_filter.filter_data(mock_data))

        # Assert: Ensure only the message inside Central Park remains
        self.assertEqual(len(filtered_data), 1)
        self.assertAlmostEqual(filtered_data[0].lat, 40.768, places=3)
        self.assertAlmostEqual(filtered_data[0].lon, -73.965, places=3)


class TestFilterChain(unittest.TestCase):
    def test_filter_chain(self):
        # Setup
        filter1 = NoneFilter('lat', 'lon')
        filter2 = MessageTypeFilter(1, 2)
        chain = FilterChain([filter1, filter2])

        mock_data = [MockAISMessage(lat=1, lon=1, msg_type=1), MockAISMessage(lat=None, lon=1, msg_type=2)]

        # Execute
        filtered_data = list(chain.filter(mock_data))

        # Assert
        self.assertEqual(len(filtered_data), 1)  # Only one message should pass through the entire chain

    def test_complex_filter_chain(self):
        # Setup: Define the filters and chain
        none_filter = NoneFilter('lat', 'lon', 'msg_type')
        message_type_filter = MessageTypeFilter(1, 2)
        ref_point = (40.7831, -73.9712)  # Reference point near Central Park, NYC
        distance_filter = DistanceFilter(ref_point, 100)  # 100 km distance threshold
        grid_filter = GridFilter(40.7644, -73.9730, 40.8005, -73.9580)  # Central Park grid

        chain = FilterChain([none_filter, message_type_filter, distance_filter, grid_filter])

        # Mock data: Four messages with different attributes
        messages = [
            MockAISMessage(lat=40.768, lon=-73.965, msg_type=1),  # Passes all filters
            MockAISMessage(lat=None, lon=-73.980, msg_type=1),    # Fails NoneFilter
            MockAISMessage(lat=40.760, lon=-73.980, msg_type=3),  # Fails MessageTypeFilter
            MockAISMessage(lat=41.000, lon=-74.000, msg_type=1)   # Fails DistanceFilter and GridFilter
        ]

        # Execute: Run the filter chain
        filtered_data = list(chain.filter(messages))

        # Assert: Ensure only the first message remains
        self.assertEqual(len(filtered_data), 1)
        self.assertEqual(filtered_data[0].lat, 40.768)
        self.assertEqual(filtered_data[0].lon, -73.965)
        self.assertEqual(filtered_data[0].msg_type, 1)

    def test_filter_chain_with_file_stream(self):
        # Setup: Define the filters and chain
        chain = FilterChain([AttributeFilter(lambda x: x.mmsi == 445451000)])

        # Setup: Define sample file
        file = pathlib.Path(__file__).parent.joinpath('messages.ais')

        with FileReaderStream(file) as ais_stream:
            total = len(list(ais_stream))

        with FileReaderStream(file) as ais_stream:
            filtered = list(chain.filter(ais_stream))

        self.assertEqual(len(filtered), 2)
        self.assertEqual(total, 6)


class TestAttributeFilter(unittest.TestCase):
    def test_attribute_filtering(self):
        # Setup: Define a filter function that filters out messages with a 'lat' attribute less than 5
        def filter_func(message):
            return message.lat >= 5

        filter = AttributeFilter(filter_func)
        mock_data = [MockAISMessage(lat=4), MockAISMessage(lat=6)]  # One message should be filtered out

        # Execute: Run the filter
        filtered_data = list(filter.filter_data(mock_data))

        # Assert: Ensure only one message remains
        self.assertEqual(len(filtered_data), 1)
        self.assertEqual(filtered_data[0].lat, 6)  # The remaining message should have lat >= 5


class TestHaversine(unittest.TestCase):
    def test_nyc_to_la(self):
        # Coordinates for New York City and Los Angeles
        nyc = (40.7128, -74.0060)
        la = (34.0522, -118.2437)
        # Known distance approximately: 3940 km
        calculated_distance = haversine(nyc, la)
        self.assertAlmostEqual(calculated_distance, 3940, delta=100)

    def test_london_to_paris(self):
        # Coordinates for London and Paris
        london = (51.5074, -0.1278)
        paris = (48.8566, 2.3522)
        # Known distance approximately: 344 km
        calculated_distance = haversine(london, paris)
        self.assertAlmostEqual(calculated_distance, 344, delta=10)

    def test_sydney_to_melbourne(self):
        # Coordinates for Sydney and Melbourne
        sydney = (-33.8688, 151.2093)
        melbourne = (-37.8136, 144.9631)
        # Known distance approximately: 713 km
        calculated_distance = haversine(sydney, melbourne)
        self.assertAlmostEqual(calculated_distance, 713, delta=10)


if __name__ == '__main__':
    unittest.main()

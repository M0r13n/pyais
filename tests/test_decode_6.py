
import unittest

from pyais import decode
from pyais.encode import ais_to_nmea_0183, encode_dict, encode_msg
from pyais.messages import ANY_MESSAGE, MessageType6Dac1Fid16A, MessageType6Dac1Fid16B, MessageType6Dac1Fid18, MessageType6Dac1Fid20, MessageType6Dac1Fid23, MessageType6Default
from pyais.util import SixBitNibleEncoder, to_six_bit
from tests.utils import _pack_sub_areas, _sub_circle, _sub_rectangle, _sub_sector, _sub_text, _sub_waypoints, _twos


def encode_decode(bits: str) -> ANY_MESSAGE:
    padded = bits + '0' * (-len(bits) % 8)
    data = int(padded, 2).to_bytes(len(padded) // 8, 'big')
    payload, fill_bits = SixBitNibleEncoder().encode(data, len(bits))
    sentences = ais_to_nmea_0183(payload, 'AI', 'VDM', 'A', fill_bits)
    return decode(*[part.encode() for part in sentences])


def _area_notice_header_type_6(**over) -> str:
    """Pack the fixed 143-bit Area Notice header (IMO289 DAC=1/FID=23)."""
    bits = ''
    bits += _twos(6, 6)                                    # Message ID
    bits += _twos(0, 2)                                    # Repeat Indicator
    bits += _twos(356785707, 30)                            # MMSI
    bits += _twos(0, 2)                                    # Sequence Number
    bits += _twos(325185353, 30)                            # Dest MMSI
    bits += _twos(0, 1)                                    # Retransmit
    bits += _twos(0, 1)                                    # Spare
    bits += _twos(1, 10)                                   # DAC
    bits += _twos(23, 6)                                   # FID

    bits += _twos(over.get('linkage', 42), 10)          # Message Linkage ID
    bits += _twos(over.get('notice', 10), 7)            # Notice Description
    bits += _twos(over.get('month', 9), 4)              # Month (UTC)
    bits += _twos(over.get('day', 27), 5)               # Day (UTC)
    bits += _twos(over.get('hour', 12), 5)              # Hour (UTC)
    bits += _twos(over.get('minute', 2), 6)             # Minute (UTC)
    bits += _twos(over.get('duration', 120), 18)        # Duration in minutes
    assert len(bits) == 143
    return bits


class MessageType6Dac1Fid23TestCase(unittest.TestCase):
    def test_bit_layout_matches_spec(self):
        bits = _area_notice_header_type_6()
        bits += _sub_circle(-70.8, 42.3, radius=250, scale=1)
        bits += _sub_rectangle(-70.9, 42.2, east=200, north=150, orientation=45)
        bits += _sub_sector(-70.7, 42.4, radius=1000, left=30, right=120)
        bits += _sub_waypoints(3, [(90, 500), (180, 300), (720, 0), (720, 0)])
        bits += _sub_waypoints(4, [(0, 100), (180, 100), (360, 100), (540, 100)])
        bits += _sub_text("DIVERS DOWN")
        # 143-bit header + 6 sub-areas of 87 bits
        self.assertEqual(len(bits), 143 + 6 * 87)

        decoded = encode_decode(bits)

        assert isinstance(decoded, MessageType6Dac1Fid23)
        self.assertEqual(decoded.mmsi, 356785707)
        self.assertEqual(decoded.dest_mmsi, 325185353)
        self.assertEqual(decoded.linkage, 42)
        self.assertEqual(decoded.notice, 10)  # Caution Area: Divers down
        self.assertEqual(decoded.month, 9)
        self.assertEqual(decoded.day, 27)
        self.assertEqual(decoded.hour, 12)
        self.assertEqual(decoded.minute, 2)
        self.assertEqual(decoded.duration, 120)

        areas = decoded.sub_areas
        self.assertEqual(len(areas), 6)

        # Circle: radius is scaled by 10^scale, so 250 at scale 1 is 2500 m.
        self.assertEqual(areas[0], {
            'shape': 0, 'scale': 1, 'lon': -70.8, 'lat': 42.3,
            'precision': 4, 'radius': 2500, 'shape_str': 'circle'
        })
        self.assertEqual(areas[1], {
            'shape': 1, 'scale': 0, 'lon': -70.9, 'lat': 42.2,
            'precision': 4, 'east': 200, 'north': 150, 'orientation': 45,
            'shape_str': 'rectangle'
        })
        self.assertEqual(areas[2], {
            'shape': 2, 'scale': 0, 'lon': -70.7, 'lat': 42.4,
            'precision': 4, 'radius': 1000, 'left': 30, 'right': 120,
            'shape_str': 'sector'
        })
        # Bearings are half-degree steps, so 90 raw is 45 degrees.
        self.assertEqual(areas[3], {
            'shape': 3, 'scale': 0, 'points': [
                {'bearing': 45.0, 'distance': 500},
                {'bearing': 90.0, 'distance': 300},
                {'bearing': 360.0, 'distance': 0},   # 720 = N/A
                {'bearing': 360.0, 'distance': 0},
            ],
            'shape_str': 'polyline'
        })
        self.assertEqual(areas[4], {
            'shape': 4, 'scale': 0, 'points': [
                {'bearing': 0.0, 'distance': 100},
                {'bearing': 90.0, 'distance': 100},
                {'bearing': 180.0, 'distance': 100},
                {'bearing': 270.0, 'distance': 100},
            ], 'shape_str': 'polygon'
        })
        self.assertEqual(areas[5], {'shape': 5, 'text': 'DIVERS DOWN', 'shape_str': 'text'})

    def test_scale_factor_applies_to_linear_dimensions(self):
        """Each scale step multiplies radius/east/north/distance by ten."""
        for scale, radius in ((0, 4095), (1, 40950), (2, 409500), (3, 4095000)):
            bits = _area_notice_header_type_6() + _sub_circle(0.0, 0.0, 4095, scale=scale)
            decoded = encode_decode(bits)
            assert isinstance(decoded, MessageType6Dac1Fid23)
            self.assertEqual(decoded.sub_areas[0]['radius'], radius)

        bits = _area_notice_header_type_6() + _sub_rectangle(0.0, 0.0, 255, 255, 0, scale=2)
        decoded = encode_decode(bits)
        assert isinstance(decoded, MessageType6Dac1Fid23)
        self.assertEqual(decoded.sub_areas[0]['east'], 25500)
        self.assertEqual(decoded.sub_areas[0]['north'], 25500)

        bits = _area_notice_header_type_6() + _sub_waypoints(3, [(0, 1023)] * 4, scale=3)
        decoded = encode_decode(bits)
        assert isinstance(decoded, MessageType6Dac1Fid23)
        self.assertEqual(decoded.sub_areas[0]['points'][0]['distance'], 1023000)

    def test_single_and_maximum_sub_area_counts(self):
        """1 sub-area is the minimum (230 bits) and 10 the maximum (1012 bits)."""
        bits = _area_notice_header_type_6() + _sub_text("ONE")
        self.assertEqual(len(bits), 230)
        decoded = encode_decode(bits)
        assert isinstance(decoded, MessageType6Dac1Fid23)
        self.assertEqual(len(decoded.sub_areas), 1)
        self.assertEqual(decoded.sub_areas[0]['text'], 'ONE')

        bits = _area_notice_header_type_6()
        for i in range(10):
            bits += _sub_circle(1.0 * i, 2.0 * i, radius=i)
        self.assertEqual(len(bits), 1013)
        decoded = encode_decode(bits)
        assert isinstance(decoded, MessageType6Dac1Fid23)
        self.assertEqual(len(decoded.sub_areas), 10)
        self.assertEqual(decoded.sub_areas[9]['lon'], 9.0)
        self.assertEqual(decoded.sub_areas[9]['lat'], 18.0)
        self.assertEqual(decoded.sub_areas[9]['radius'], 9)

    def test_defaults_and_na_sentinels(self):
        """The N/A defaults from the spec table survive a round trip."""
        bits = _area_notice_header_type_6(
            notice=127,      # Undefined (default)
            month=0,         # N/A
            day=0,           # N/A
            hour=24,         # N/A
            minute=60,       # N/A
            duration=262143  # N/A
        )
        bits += _sub_text("")
        decoded = encode_decode(bits)

        assert isinstance(decoded, MessageType6Dac1Fid23)
        self.assertEqual(decoded.notice, 127)
        self.assertEqual(decoded.month, 0)
        self.assertEqual(decoded.day, 0)
        self.assertEqual(decoded.hour, 24)
        self.assertEqual(decoded.minute, 60)
        self.assertEqual(decoded.duration, 262143)
        self.assertEqual(decoded.sub_areas[0], {'shape': 5, 'shape_str': 'text', 'text': ''})

    def test_notice_126_cancels_the_area_by_linkage_id(self):
        """Notice 126 plus duration 0 is the documented cancellation form."""
        bits = _area_notice_header_type_6(notice=126, linkage=1023, duration=0)
        bits += _sub_circle(-70.8, 42.3, radius=0)
        decoded = encode_decode(bits)

        assert isinstance(decoded, MessageType6Dac1Fid23)
        self.assertEqual(decoded.notice, 126)
        self.assertEqual(decoded.linkage, 1023)
        self.assertEqual(decoded.duration, 0)
        # radius 0 means the shape is a point rather than a circle
        self.assertEqual(decoded.sub_areas[0]['radius'], 0)

    def test_reserved_shapes_are_kept_raw(self):
        """Shapes 6-7 are reserved, so the payload is not guessed at."""
        for shape in (6, 7):
            bits = _area_notice_header_type_6() + _twos(shape, 3) + _twos(12345, 84)
            decoded = encode_decode(bits)
            assert isinstance(decoded, MessageType6Dac1Fid23)
            self.assertEqual(decoded.sub_areas[0], {'shape': shape, 'shape_str': 'reserved', 'data': 12345})

    def test_negative_and_extreme_coordinates(self):
        """Positions are signed 1/1000-minute values."""
        bits = _area_notice_header_type_6()
        bits += _sub_circle(-179.99998, -89.99998, radius=1)
        bits += _sub_circle(179.99998, 89.99998, radius=1)
        decoded = encode_decode(bits)

        assert isinstance(decoded, MessageType6Dac1Fid23)
        self.assertEqual(decoded.sub_areas[0]['lon'], -179.99998)
        self.assertEqual(decoded.sub_areas[0]['lat'], -89.99998)
        self.assertEqual(decoded.sub_areas[1]['lon'], 179.99998)
        self.assertEqual(decoded.sub_areas[1]['lat'], 89.99998)

    def test_encode_decode_round_trip(self):
        """Build a message with create()/encode_msg() and read it back."""
        area_bits = _sub_circle(11.5, 55.25, radius=300)
        area_bits += _sub_text("SURVEY OPS")
        area_data = _pack_sub_areas(area_bits)

        encoded = encode_msg(MessageType6Dac1Fid23.create(
            mmsi='219000001',
            linkage=7,
            notice=13,  # Caution Area: Survey operations
            month=3,
            day=9,
            hour=6,
            minute=45,
            duration=600,
            area_data=area_data,
        ))
        decoded = decode(*encoded)

        assert isinstance(decoded, MessageType6Dac1Fid23)
        self.assertEqual(decoded.mmsi, 219000001)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 23)
        self.assertEqual(decoded.linkage, 7)
        self.assertEqual(decoded.notice, 13)
        self.assertEqual(decoded.duration, 600)
        self.assertEqual(len(decoded.sub_areas), 2)
        self.assertEqual(decoded.sub_areas[0]['lon'], 11.5)
        self.assertEqual(decoded.sub_areas[0]['lat'], 55.25)
        self.assertEqual(decoded.sub_areas[0]['radius'], 300)
        self.assertEqual(decoded.sub_areas[1]['text'], 'SURVEY OPS')

    def test_encode_dict_round_trip(self):
        """The (dac, fid) pair routes through encode_dict as well."""
        area_data = _pack_sub_areas(_sub_text("HIGH WIND"))
        encoded = encode_dict({
            'msg_type': 6,
            'mmsi': '219000001',
            'dac': 1,
            'fid': 23,
            'notice': 26,  # Environmental Caution Area: High wind
            'area_data': area_data,
        })
        decoded = decode(*encoded)

        assert isinstance(decoded, MessageType6Dac1Fid23)
        self.assertEqual(decoded.notice, 26)
        self.assertEqual(decoded.sub_areas[0]['text'], 'HIGH WIND')

    def test_empty_area_region_yields_no_sub_areas(self):
        """A header-only message decodes without raising."""
        decoded = MessageType6Dac1Fid23.create(mmsi='219000001')
        assert isinstance(decoded, MessageType6Dac1Fid23)
        self.assertEqual(decoded.sub_areas, [])


class MessageType6Dac1Fid20TestCase(unittest.TestCase):
    def test_bit_layout_matches_spec(self):
        bits = ''
        bits += _twos(6, 6)                                    # Message ID
        bits += _twos(0, 2)                                    # Repeat Indicator
        bits += _twos(22334455, 30)                            # MMSI
        bits += _twos(0, 2)                                    # Sequence Number
        bits += _twos(67895432, 30)                            # Dest MMSI
        bits += _twos(0, 1)                                    # Retransmit
        bits += _twos(0, 1)                                    # Spare
        bits += _twos(1, 10)                                   # DAC
        bits += _twos(20, 6)                                   # FID

        bits += _twos(42, 10)                                  # Message Linkage ID
        bits += _twos(300, 9)                                  # Berth length
        bits += _twos(125, 8)                                  # Berth water depth (0.1m)
        bits += _twos(1, 3)                                    # Mooring position
        bits += _twos(7, 4)                                    # UTC Month
        bits += _twos(26, 5)                                   # UTC Day
        bits += _twos(14, 5)                                   # UTC Hour
        bits += _twos(27, 6)                                   # UTC Minute
        bits += _twos(1, 1)                                    # Services availability
        services = [
            1,  # agent
            2,  # fuel
            0,  # chandler
            0,  # stevedore
            0,  # electrical
            1,  # water
            0,  # customs
            0,  # cartage
            0,  # crane
            0,  # lift
            0,  # medical
            0,  # navrepair
            0,  # provisions
            0,  # shiprepair
            0,  # surveyor
            0,  # steam
            1,  # tugs
            0,  # solidwaste
            0,  # liquidwaste
            3,  # hazardouswaste
            0,  # ballast
            0,  # additional
            0,  # regional1
            0,  # regional2
            0,  # future1
            0,  # future2
        ]
        self.assertEqual(len(services), 26)
        for service in services:
            bits += _twos(service, 2)
        name = "KIEL OSTUFERHAFEN".ljust(20, '@')
        bits += ''.join(to_six_bit(c) for c in name)           # Name of berth
        bits += _twos(round(10.1394 * 60000), 25)              # Longitude
        bits += _twos(round(54.3233 * 60000), 24)              # Latitude
        self.assertEqual(len(bits), 360)

        decoded = encode_decode(bits)

        assert isinstance(decoded, MessageType6Dac1Fid20)
        self.assertEqual(decoded.linkage, 42)
        self.assertEqual(decoded.berth_length, 300)
        self.assertEqual(decoded.berth_depth, 12.5)
        self.assertEqual(decoded.position, 1)
        self.assertEqual(decoded.month, 7)
        self.assertEqual(decoded.day, 26)
        self.assertEqual(decoded.hour, 14)
        self.assertEqual(decoded.minute, 27)
        self.assertTrue(decoded.availability)
        self.assertEqual(decoded.agent, 1)
        self.assertEqual(decoded.fuel, 2)
        self.assertEqual(decoded.water, 1)
        self.assertEqual(decoded.tugs, 1)
        self.assertEqual(decoded.hazardouswaste, 3)
        self.assertEqual(decoded.berth_name, "KIEL OSTUFERHAFEN")
        self.assertEqual(decoded.berth_lon, 10.1394)
        self.assertEqual(decoded.berth_lat, 54.3233)

    def test_encode(self):
        encoded = encode_dict({
            "msg_type": 6,
            "repeat": 0,
            "mmsi": 23456324,
            "dac": 1,
            "fid": 20,
            "dest_mmsi": 696969,
            "month": 9,
            "day": 26,
            "hour": 13,
            "minute": 00,
            "berth_name": "MALLORCA",
            "berth_lon": 3.29655,
            "berth_lat": 39.598583,
        })
        self.assertEqual(len(encoded), 1)
        self.assertEqual(
            encoded[0],
            "!AIVDO,1,1,,A,60FGbA00:``T05@00002M=0000000000J2HHNT620000000000000hBQ943c,0*19"
        )

    def test_dispatch_is_registered_not_default(self):
        decoded = MessageType6Dac1Fid20.create(mmsi='219000001')
        self.assertIsInstance(decoded, MessageType6Dac1Fid20)


class MessageType6Dac1Fid18TestCase(unittest.TestCase):

    def test_bit_layout_matches_spec(self):
        bits = ''
        bits += _twos(6, 6)                                    # Message ID
        bits += _twos(0, 2)                                    # Repeat Indicator
        bits += _twos(22334455, 30)                            # MMSI
        bits += _twos(0, 2)                                    # Sequence Number
        bits += _twos(22222222, 30)                            # Dest MMSI
        bits += _twos(0, 1)                                    # Retransmit
        bits += _twos(0, 1)                                    # Spare
        bits += _twos(1, 10)                                   # DAC
        bits += _twos(18, 6)                                   # FID

        bits += _twos(69, 10)                                  # Message Linkage ID
        bits += _twos(9, 4)                                    # UTC Month
        bits += _twos(26, 5)                                   # UTC Day
        bits += _twos(13, 5)                                   # UTC Hour
        bits += _twos(0, 6)                                   # UTC Minute
        bits += ''.join(to_six_bit(c) for c in "Mallorca")     # Name of Port & Berth
        bits += _twos(0, 72)
        bits += ''.join(to_six_bit(c) for c in "Palma")        # Destination
        bits += _twos(round(3.296555 * 60000), 25)             # Longitude
        bits += _twos(round(39.598583 * 60000), 24)            # Latitude
        bits += _twos(7777, 43)                                # Spare

        self.assertEqual(len(bits), 360)

        decoded = encode_decode(bits)

        assert isinstance(decoded, MessageType6Dac1Fid18)
        self.assertEqual(decoded.mmsi, 22334455)
        self.assertEqual(decoded.dest_mmsi, 22222222)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 18)

        self.assertEqual(decoded.linkage, 69)
        self.assertEqual(decoded.month, 9)
        self.assertEqual(decoded.day, 26)
        self.assertEqual(decoded.hour, 13)
        self.assertEqual(decoded.minute, 00)
        self.assertEqual(decoded.port_name, "MALLORCA")
        self.assertEqual(decoded.destination, "PALMA")
        self.assertEqual(decoded.lon, 3.29655)
        self.assertEqual(decoded.lat, 39.598583)

    def test_encode(self):
        encoded = encode_dict({
            "msg_type": 6,
            "repeat": 0,
            "mmsi": 23456324,
            "dac": 1,
            "fid": 18,
            "dest_mmsi": 696969,
            "month": 9,
            "day": 26,
            "hour": 13,
            "minute": 00,
            "port_name": "MALLORCA",
            "destination": "PALMA",
            "lon": 3.29655,
            "lat": 39.598583,
        })
        self.assertEqual(len(encoded), 1)
        self.assertEqual(
            encoded[0],
            "!AIVDO,1,1,,A,60FGbA00:``T05809ll0l4hhu8<400000000000104hl41PU2B87F0000000,0*7F"
        )

    def test_dispatch_is_registered_not_default(self):
        decoded = MessageType6Dac1Fid18.create(mmsi='219000001')
        self.assertIsInstance(decoded, MessageType6Dac1Fid18)


class MessageType6Dac1Fid16TestCase(unittest.TestCase):

    def test_bit_layout_matches_spec_short(self):
        bits = ''
        bits += _twos(6, 6)                                    # Message ID
        bits += _twos(0, 2)                                    # Repeat Indicator
        bits += _twos(11223344, 30)                            # MMSI
        bits += _twos(0, 2)                                    # Spare
        bits += _twos(1, 10)                                   # DAC
        bits += _twos(16, 6)                                   # FID
        bits += _twos(8190, 13)                                # Persons on board
        bits += _twos(0, 3)                                    # Spare
        self.assertEqual(len(bits), 72)

        decoded = encode_decode(bits)

        assert isinstance(decoded, MessageType6Dac1Fid16A)
        self.assertEqual(decoded.mmsi, 11223344)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 16)
        self.assertEqual(decoded.persons, 8190)

        # 0 Persons
        bits = ''
        bits += _twos(6, 6)                                    # Message ID
        bits += _twos(0, 2)                                    # Repeat Indicator
        bits += _twos(11223344, 30)                            # MMSI
        bits += _twos(0, 2)                                    # Spare
        bits += _twos(1, 10)                                   # DAC
        bits += _twos(16, 6)                                   # FID
        bits += _twos(0, 13)                                   # Persons on board
        bits += _twos(0, 3)                                    # Spare
        self.assertEqual(len(bits), 72)

        decoded = encode_decode(bits)
        assert isinstance(decoded, MessageType6Dac1Fid16A)
        self.assertEqual(decoded.mmsi, 11223344)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 16)
        self.assertEqual(decoded.persons, 0)

        # 8190 Persons
        bits = ''
        bits += _twos(6, 6)                                    # Message ID
        bits += _twos(0, 2)                                    # Repeat Indicator
        bits += _twos(11223344, 30)                            # MMSI
        bits += _twos(0, 2)                                    # Spare
        bits += _twos(1, 10)                                   # DAC
        bits += _twos(16, 6)                                   # FID
        bits += _twos(8190, 13)                                # Persons on board
        bits += _twos(0, 3)                                    # Spare
        self.assertEqual(len(bits), 72)

        decoded = encode_decode(bits)
        assert isinstance(decoded, MessageType6Dac1Fid16A)
        self.assertEqual(decoded.mmsi, 11223344)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 16)
        self.assertEqual(decoded.persons, 8190)

        # 8191 Persons
        bits = ''
        bits += _twos(6, 6)                                    # Message ID
        bits += _twos(0, 2)                                    # Repeat Indicator
        bits += _twos(11223344, 30)                            # MMSI
        bits += _twos(0, 2)                                    # Spare
        bits += _twos(1, 10)                                   # DAC
        bits += _twos(16, 6)                                   # FID
        bits += _twos(8191, 13)                                # Persons on board
        bits += _twos(0, 3)                                    # Spare
        self.assertEqual(len(bits), 72)

        decoded = encode_decode(bits)
        assert isinstance(decoded, MessageType6Dac1Fid16A)
        self.assertEqual(decoded.mmsi, 11223344)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 16)
        self.assertEqual(decoded.persons, 8191)

    def test_bit_layout_matches_spec_long(self):
        bits = ''
        bits += _twos(6, 6)                                    # Message ID
        bits += _twos(0, 2)                                    # Repeat Indicator
        bits += _twos(22334455, 30)                            # MMSI
        bits += _twos(0, 2)                                    # Sequence Number
        bits += _twos(11111111, 30)                            # Dest MMSI
        bits += _twos(0, 1)                                    # Retransmit
        bits += _twos(0, 1)                                    # Spare
        bits += _twos(1, 10)                                   # DAC
        bits += _twos(16, 6)                                   # FID
        bits += _twos(1337, 13)                                # Persons on board
        bits += _twos(0, 35)                                   # Spare
        self.assertEqual(len(bits), 136)

        decoded = encode_decode(bits)

        assert isinstance(decoded, MessageType6Dac1Fid16B)
        self.assertEqual(decoded.mmsi, 22334455)
        self.assertEqual(decoded.dest_mmsi, 11111111)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 16)
        self.assertEqual(decoded.persons, 1337)

        # 0 Persons
        bits = bits[:88] + _twos(0, 13) + bits[101:]
        decoded = encode_decode(bits)
        assert isinstance(decoded, MessageType6Dac1Fid16B)
        self.assertEqual(decoded.mmsi, 22334455)
        self.assertEqual(decoded.dest_mmsi, 11111111)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 16)
        self.assertEqual(decoded.persons, 0)

        # 8190 Persons
        bits = bits[:88] + _twos(8190, 13) + bits[101:]
        decoded = encode_decode(bits)
        assert isinstance(decoded, MessageType6Dac1Fid16B)
        self.assertEqual(decoded.mmsi, 22334455)
        self.assertEqual(decoded.dest_mmsi, 11111111)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 16)
        self.assertEqual(decoded.persons, 8190)

        # 8191 Persons
        bits = bits[:88] + _twos(8191, 13) + bits[101:]
        decoded = encode_decode(bits)
        assert isinstance(decoded, MessageType6Dac1Fid16B)
        self.assertEqual(decoded.mmsi, 22334455)
        self.assertEqual(decoded.dest_mmsi, 11111111)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 16)
        self.assertEqual(decoded.persons, 8191)

    def test_encode(self):
        encoded = encode_dict({
            "msg_type": 6,
            "repeat": 0,
            "mmsi": 23456324,
            "dac": 1,
            "fid": 16,
            "dest_mmsi": 696969,
            "persons": 25,
        })
        self.assertEqual(len(encoded), 1)
        self.assertEqual(
            encoded[0],
            "!AIVDO,1,1,,A,60FGbA00:``T0500j000000,2*03"
        )

    def test_dispatch_is_registered_not_default(self):
        decoded = MessageType6Dac1Fid16A.create(mmsi='219000001')
        self.assertNotIsInstance(decoded, MessageType6Default)

        decoded = MessageType6Dac1Fid16B.create(mmsi='219000001')
        self.assertNotIsInstance(decoded, MessageType6Default)


if __name__ == '__main__':
    unittest.main()

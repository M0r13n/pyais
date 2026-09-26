
import unittest

from pyais import decode
from pyais.encode import ais_to_nmea_0183, encode_dict
from pyais.messages import ANY_MESSAGE, MessageType6Dac1Fid16A, MessageType6Dac1Fid16B, MessageType6Dac1Fid18, MessageType6Default
from pyais.util import SixBitNibleEncoder, to_six_bit
from tests.utils import _twos


def encode_bits(bits: str) -> ANY_MESSAGE:
    data = int(bits, 2).to_bytes(len(bits) // 8, 'big')
    payload, fill_bits = SixBitNibleEncoder().encode(data, len(bits))
    sentences = ais_to_nmea_0183(payload, 'AI', 'VDM', 'A', fill_bits)
    decoded = decode(*[part.encode() for part in sentences])
    return decoded


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

        decoded = encode_bits(bits)

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

        decoded = encode_bits(bits)

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

        decoded = encode_bits(bits)
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

        decoded = encode_bits(bits)
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

        decoded = encode_bits(bits)
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

        decoded = encode_bits(bits)

        assert isinstance(decoded, MessageType6Dac1Fid16B)
        self.assertEqual(decoded.mmsi, 22334455)
        self.assertEqual(decoded.dest_mmsi, 11111111)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 16)
        self.assertEqual(decoded.persons, 1337)

        # 0 Persons
        bits = bits[:88] + _twos(0, 13) + bits[101:]
        decoded = encode_bits(bits)
        assert isinstance(decoded, MessageType6Dac1Fid16B)
        self.assertEqual(decoded.mmsi, 22334455)
        self.assertEqual(decoded.dest_mmsi, 11111111)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 16)
        self.assertEqual(decoded.persons, 0)

        # 8190 Persons
        bits = bits[:88] + _twos(8190, 13) + bits[101:]
        decoded = encode_bits(bits)
        assert isinstance(decoded, MessageType6Dac1Fid16B)
        self.assertEqual(decoded.mmsi, 22334455)
        self.assertEqual(decoded.dest_mmsi, 11111111)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 16)
        self.assertEqual(decoded.persons, 8190)

        # 8191 Persons
        bits = bits[:88] + _twos(8191, 13) + bits[101:]
        decoded = encode_bits(bits)
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

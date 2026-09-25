
from tests.utils import _twos
import pathlib
import sys
import unittest

from pyais import decode
from pyais.encode import ais_to_nmea_0183, encode_dict
from pyais.messages import ANY_MESSAGE, MessageType6Dac1Fid16A, MessageType6Dac1Fid16B, MessageType6Default
from pyais.util import SixBitNibleEncoder


sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))


def encode_bits(bits: str) -> ANY_MESSAGE:
    data = int(bits, 2).to_bytes(len(bits) // 8, 'big')
    payload, fill_bits = SixBitNibleEncoder().encode(data, len(bits))
    sentences = ais_to_nmea_0183(payload, 'AI', 'VDM', 'A', fill_bits)
    decoded = decode(*[part.encode() for part in sentences])
    return decoded


class MessageType6Dac1Fid16TestCase(unittest.TestCase):

    def test_bit_layout_matches_spec_short(self):
        """
        """
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

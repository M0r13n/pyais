import unittest

from pyais.decode import decode_raw
from pyais.exceptions import InvalidNMEAMessageException


class TestDecode(unittest.TestCase):

    def test_bytes_valid(self):
        msg = decode_raw(b"!AIVDM,1,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        self.assertIsNotNone(msg)
        self.assertIsInstance(msg, dict)
        self.assertEqual(msg['mmsi'], "003669713")
        self.assertEqual(msg['lon'], 181.0)

    def test_bytes_invalid(self):
        with self.assertRaises(InvalidNMEAMessageException):
            decode_raw(b"!AIVDM,1,1,,A")

    def test_str_valid(self):
        msg = decode_raw("!AIVDM,1,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        self.assertIsNotNone(msg)
        self.assertIsInstance(msg, dict)
        self.assertEqual(msg['mmsi'], "003669713")
        self.assertEqual(msg['lon'], 181.0)

    def test_str_invalid(self):
        with self.assertRaises(InvalidNMEAMessageException):
            decode_raw("AIVDM,1,1,,A")

    def test_decode_total_garbage(self):
        def should_raise(msg):
            with self.assertRaises(InvalidNMEAMessageException):
                decode_raw(msg)

        should_raise("")
        should_raise("1234567890")
        should_raise("Foo")
        should_raise("sdfdsfsdfsfdf")

        should_raise(",1,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        should_raise("!AIVDM,,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        should_raise("!AIVDM,1,,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        should_raise("!AIVDM,1,1,,,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        should_raise("!AIVDM,1,1,,A,,0*28")
        should_raise("!AIVDM,1,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,")

        should_raise("!AIVDM,11111111111111,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        should_raise("!AIVDM,1,11111111111111111111,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        should_raise("!AIVDM,1,1,111111111,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")

        should_raise(f"!AIVDM,1,1,,A,{'A' * 256},0*28")

        should_raise(f"{'A' * 82}")

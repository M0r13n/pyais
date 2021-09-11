import unittest

from pyais import decode_msg
from pyais.exceptions import InvalidNMEAMessageException, MissingMultipartMessageException, TooManyMessagesException


class TestDecode(unittest.TestCase):

    def test_bytes_valid(self):
        msg = decode_msg(b"!AIVDM,1,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        self.assertIsNotNone(msg)
        self.assertIsInstance(msg, dict)
        self.assertEqual(msg['mmsi'], "003669713")
        self.assertEqual(msg['lon'], 181.0)

    def test_bytes_invalid(self):
        with self.assertRaises(InvalidNMEAMessageException):
            decode_msg(b"!AIVDM,1,1,,A")

    def test_str_valid(self):
        msg = decode_msg("!AIVDM,1,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        self.assertIsNotNone(msg)
        self.assertIsInstance(msg, dict)
        self.assertEqual(msg['mmsi'], "003669713")
        self.assertEqual(msg['lon'], 181.0)

    def test_str_invalid(self):
        with self.assertRaises(InvalidNMEAMessageException):
            decode_msg("AIVDM,1,1,,A")

    def test_decode_total_garbage(self):
        def should_raise(msg):
            with self.assertRaises(InvalidNMEAMessageException):
                decode_msg(msg)

        should_raise("")
        should_raise("1234567890")
        should_raise("Foo")
        should_raise("sdfdsfsdfsfdf")

        should_raise(",1,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        should_raise("!AIVDM,,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        should_raise("!AIVDM,1,,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        should_raise("!AIVDM,1,1,,A,,0*28")
        should_raise("!AIVDM,1,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,")

        should_raise("!AIVDM,11111111111111,1,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        should_raise("!AIVDM,1,11111111111111111111,,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")
        should_raise("!AIVDM,1,1,111111111,A,403Ovl@000Htt<tSF0l4Q@100`Pq,0*28")

        should_raise(f"!AIVDM,1,1,,A,{'A' * 256},0*28")

        should_raise(f"{'A' * 82}")

    def test_decode_multiline_message(self):
        decoded = decode_msg(
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
            b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
        )

        self.assertIsInstance(decoded, dict)
        self.assertEqual(decoded["mmsi"], "210035000")
        self.assertEqual(decoded["callsign"], "5BXT2")
        self.assertEqual(decoded["shipname"], "NORDIC HAMBURG")
        self.assertEqual(decoded["destination"], "CTT-LAYBY")

    def test_too_many_messages(self):
        with self.assertRaises(TooManyMessagesException) as err:
            decode_msg(
                b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
                b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
                b'!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
                b'!AIVDM,2,2,9,A,F@V@00000000000,2*3D',
            )
        self.assertEqual(str(err.exception), "Got 4 messages, but fragment count is 2")

    def test_multipart_error_message(self):
        """Refer to issue #37"""
        msg_1 = "!AIVDM,2,1,0,A,539p4OT00000@7W3K@08ThiLE8@E:0000000001S0h9135Pl?0R0C@UDQp00,0*68"
        msg_2 = "!AIVDM,2,2,0,A,00000000000,2*24"

        with self.assertRaises(MissingMultipartMessageException) as err:
            decode_msg(msg_1)
        self.assertEqual(str(err.exception), "Missing fragment numbers: [2]")

        with self.assertRaises(MissingMultipartMessageException) as err:
            decode_msg(msg_2)
        self.assertEqual(str(err.exception), "Missing fragment numbers: [1]")

        with self.assertRaises(MissingMultipartMessageException) as err:
            decode_msg(
                "!AIVDM,3,2,0,A,539p4OT00000@7W3K@08ThiLE8@E:0000000001S0h9135Pl?0R0C@UDQp00,0*68",
            )
        self.assertEqual(str(err.exception), "Missing fragment numbers: [1, 3]")

        decode_msg(
            msg_1,
            msg_2
        )

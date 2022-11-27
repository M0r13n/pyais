import unittest

from bitarray import bitarray
from pyais.decode import _assemble_messages

from pyais.exceptions import InvalidNMEAMessageException
from pyais.messages import NMEAMessage
from pyais.util import chk_to_int


class TestNMEA(unittest.TestCase):
    """
    TestCases for NMEA message decoding and assembling.
    """

    def test_values(self):
        """
        Test value count
        """
        a = b"!AIVDM,,A,91b77=h3h00nHt0Q3r@@07000<0b,0*69"

        with self.assertRaises(InvalidNMEAMessageException):
            NMEAMessage(a)

        c = b"!AIVDM,1,1,,B,91b55wi;hbOS@OdQAC062Ch2089h,0*30"
        assert NMEAMessage(c).is_valid

    def test_single(self):
        """
        Test single and multi line messages
        """
        single = b"!AIVDM,1,1,,B,91b55wi;hbOS@OdQAC062Ch2089h,0*30"
        assert NMEAMessage(single).is_single
        assert not NMEAMessage(single).is_multi

    def test_from_str(self):
        old = NMEAMessage(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C").decode()
        new = NMEAMessage.from_string("!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C").decode()

        assert old == new

    def test_message_assembling(self):
        multi = NMEAMessage.assemble_from_iterable(messages=[
            NMEAMessage(b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08"),
            NMEAMessage(b"!AIVDM,2,2,4,A,000000000000000,2*20")
        ])
        assert not multi.is_single
        assert multi.is_multi
        assert multi.is_valid

    def test_talker(self):
        """
        Test talker extraction
        """
        msg = b"!AIVDM,1,1,,B,91b55wi;hbOS@OdQAC062Ch2089h,0*30"
        assert NMEAMessage(msg).talker == "AI"
        msg = b"!AIVDM,1,1,,A,8@30oni?1j020@00,0*23"
        assert NMEAMessage(msg).talker == "AI"

    def test_type(self):
        """
        Test value type
        """
        msg = b"!AIVDM,1,1,,B,91b55wi;hbOS@OdQAC062Ch2089h,0*30"
        assert NMEAMessage(msg).type == "VDM"
        msg = b"!AIVDM,1,1,,A,8@30oni?1j020@00,0*23"
        assert NMEAMessage(msg).type == "VDM"

    def test_attrs(self):
        msg = b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47"
        nmea = NMEAMessage(msg)

        assert nmea.ais_id == 8
        assert nmea.frag_cnt == 1
        assert nmea.frag_num == 1
        assert nmea.seq_id is None
        assert nmea.channel == "A"
        assert nmea.payload == b"85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs"
        assert nmea.checksum == 0x47

    def test_validity(self):
        msg = b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47"
        assert NMEAMessage(msg).is_valid

        msg = b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGt,0*47"
        self.assertFalse(NMEAMessage(msg).is_valid)

    def test_from_bytes(self):
        msg = b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47"
        assert NMEAMessage(msg) == NMEAMessage.from_bytes(msg)

    def test_message_eq_method(self):
        msg = b"!AIVDM,1,1,,B,F030p:j2N2P5aJR0r;6f3rj10000,0*11"

        first_obj = NMEAMessage(msg)
        second_obj = NMEAMessage(msg)

        # make sure they are not the same object
        assert not id(first_obj) == id(second_obj)

        # but make sure they equal
        assert first_obj == second_obj

    def test_wrong_type(self):
        with self.assertRaises(ValueError):
            NMEAMessage("!AIVDM,1,1,,B,F030p:j2N2P5aJR0r;6f3rj10000,0*11")

        with self.assertRaises(ValueError):
            NMEAMessage(123)

    def test_dict(self):
        msg = b"!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B"
        msg = NMEAMessage(msg)

        def serializable(o: object):
            if isinstance(o, bytes):
                return o.decode('utf-8')
            elif isinstance(o, bitarray):
                return o.to01()
            return o

        actual = msg.asdict()
        self.assertEqual(1, actual["ais_id"])
        self.assertEqual("!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B", actual["raw"])
        self.assertEqual("AI", actual["talker"])
        self.assertEqual("VDM", actual["type"])
        self.assertEqual(1, actual["frag_cnt"])
        self.assertEqual(1, actual["frag_num"])
        self.assertEqual(None, actual["seq_id"])
        self.assertEqual("A", actual["channel"])
        self.assertEqual("15Mj23P000G?q7fK>g:o7@1:0L3S", actual["payload"])
        self.assertEqual(0, actual["fill_bits"])
        self.assertEqual(0x1b, actual["checksum"])

    def test_get_item(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B")

        self.assertEqual(1, msg["ais_id"])
        self.assertEqual(b"!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B", msg["raw"])
        self.assertEqual("AI", msg["talker"])
        self.assertEqual("VDM", msg["type"])
        self.assertEqual(1, msg["frag_cnt"])
        self.assertEqual(1, msg["frag_num"])
        self.assertEqual(None, msg["seq_id"])
        self.assertEqual("A", msg["channel"])
        self.assertEqual(b"15Mj23P000G?q7fK>g:o7@1:0L3S", msg["payload"])
        self.assertEqual(0, msg["fill_bits"])
        self.assertEqual(0x1b, msg["checksum"])

    def test_get_item_raises_key_error(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B")

        with self.assertRaises(KeyError):
            _ = msg["foo"]

    def test_get_item_raises_type_error(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B")

        with self.assertRaises(TypeError):
            _ = msg[1]

        with self.assertRaises(TypeError):
            _ = msg[1:3]

    def test_missing_checksum(self):
        msg = b"!AIVDM,1,1,,A,100u3FP04r28t0<WcshcQI<H0H79,0"
        NMEAMessage(msg)

    def test_chk_to_int_with_valid_checksum(self):
        self.assertEqual(chk_to_int(b"0*1B"), (0, 27))
        self.assertEqual(chk_to_int(b"0*FF"), (0, 255))
        self.assertEqual(chk_to_int(b"0*00"), (0, 0))

    def test_chk_to_int_with_fill_bits(self):
        self.assertEqual(chk_to_int(b"1*1B"), (1, 27))
        self.assertEqual(chk_to_int(b"5*1B"), (5, 27))

    def test_chk_to_int_with_missing_checksum(self):
        self.assertEqual(chk_to_int(b"1"), (0, -1))
        self.assertEqual(chk_to_int(b"5*"), (5, -1))

    def test_chk_to_int_with_missing_fill_bits(self):
        self.assertEqual(chk_to_int(b""), (0, -1))
        self.assertEqual(chk_to_int(b"*1B"), (0, 27))

    def test_that_a_valid_checksum_is_correctly_identified(self):
        raw = b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05"
        msg = NMEAMessage(raw)
        self.assertTrue(msg.is_valid)

    def test_that_an_invalid_checksum_is_correctly_identified(self):
        raw = b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*04"
        msg = NMEAMessage(raw)
        self.assertFalse(msg.is_valid)

    def test_that_a_valid_checksum_is_correctly_identified_for_multi_part_msgs(self):
        sentences = [
            b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08",
            b"!AIVDM,2,2,4,A,000000000000000,2*20",
        ]
        msg = _assemble_messages(*sentences)
        self.assertTrue(msg.is_valid)

    def test_that_an_invalid_checksum_is_correctly_identified_for_multi_part_msgs(self):
        # The first sentence has an invalid checksum
        sentences = [
            b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*09",
            b"!AIVDM,2,2,4,A,000000000000000,2*20",
        ]
        msg = _assemble_messages(*sentences)
        self.assertFalse(msg.is_valid)

        # The second sentence has an invalid checksum
        sentences = [
            b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08",
            b"!AIVDM,2,2,4,A,000000000000000,2*21",
        ]
        msg = _assemble_messages(*sentences)
        self.assertFalse(msg.is_valid)

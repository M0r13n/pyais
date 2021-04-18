import unittest

from pyais.exceptions import InvalidNMEAMessageException
from pyais.messages import NMEAMessage, AISMessage


class TestNMEA(unittest.TestCase):
    """
    TestCases for NMEA message decoding and assembling.
    """

    def test_values(self):
        """
        Test value count
        """
        a = b"!AIVDM,,A,91b77=h3h00nHt0Q3r@@07000<0b,0*69"
        b = b"!AIVDM,1,1,,A,91b77=h3h00nHt0Q3r@@07000<0b,0*69,0,3"

        with self.assertRaises(InvalidNMEAMessageException):
            NMEAMessage(a)

        with self.assertRaises(InvalidNMEAMessageException):
            NMEAMessage(b)

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
        old = NMEAMessage(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C").decode().content
        new = NMEAMessage.from_string("!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C").decode().content

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
        assert NMEAMessage(msg).msg_type == "VDM"
        msg = b"!AIVDM,1,1,,A,8@30oni?1j020@00,0*23"
        assert NMEAMessage(msg).msg_type == "VDM"

    def test_attrs(self):
        msg = b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47"
        nmea = NMEAMessage(msg)

        assert nmea.ais_id == 8
        assert nmea.count == 1
        assert nmea.index == 1
        assert nmea.channel == b"A"
        assert nmea.data == b"85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs"
        assert nmea.checksum == 0x47

    def test_validity(self):
        msg = b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47"
        assert NMEAMessage(msg).is_valid

        msg = b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGt,0*47"
        self.assertFalse(NMEAMessage(msg).is_valid)

    def test_from_bytes(self):
        msg = b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47"
        assert NMEAMessage(msg) == NMEAMessage.from_bytes(msg)

    def test_decode(self):
        msg = b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47"
        assert isinstance(NMEAMessage(msg).decode(), AISMessage)

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

    def test_invalid_msg_with_wrong_type(self):
        with self.assertRaises(InvalidNMEAMessageException):
            NMEAMessage(b"GPSD,1,1,,B,F030p:j2N2P5aJR0r;6f3rj10000,0*11")

import unittest

from pyais import NMEAMessage
from pyais.constants import TalkerID


class TestTalkerIds(unittest.TestCase):
    """Test that different Talker IDs can be decoded"""

    def test_ab(self):
        msg = b"!ABVDM,1,1,,B,K5DfMB9FLsM?P00d,0*7B"
        decoded = NMEAMessage(msg)
        self.assertEqual(decoded.talker, TalkerID.Base_Station)

    def test_ad(self):
        msg = b"!ADVDM,1,1,,B,K5DfMB9FLsM?P00d,0*7D"
        decoded = NMEAMessage(msg)
        self.assertEqual(decoded.talker, TalkerID.Dependent_Base_Station)

    def test_ai(self):
        msg = b"!AIVDM,1,1,,B,K5DfMB9FLsM?P00d,0*70"
        decoded = NMEAMessage(msg)
        self.assertEqual(decoded.talker, TalkerID.Mobile_Station)

    def test_an(self):
        msg = b"!ANVDM,1,1,,B,K5DfMB9FLsM?P00d,0*77"
        decoded = NMEAMessage(msg)
        self.assertEqual(decoded.talker, TalkerID.Navigation_Station)

    def test_ar(self):
        msg = b"!ARVDM,1,1,,B,K5DfMB9FLsM?P00d,0*6B"
        decoded = NMEAMessage(msg)
        self.assertEqual(decoded.talker, TalkerID.Receiving_Station)

    def test_as(self):
        msg = b"!ASVDM,1,1,,B,K5DfMB9FLsM?P00d,0*6A"
        decoded = NMEAMessage(msg)
        self.assertEqual(decoded.talker, TalkerID.Limited_Base_Station)

    def test_at(self):
        msg = b"!ATVDM,1,1,,B,K5DfMB9FLsM?P00d,0*6D"
        decoded = NMEAMessage(msg)
        self.assertEqual(decoded.talker, TalkerID.Transmitting_Station)

    def test_ax(self):
        msg = b"!AXVDM,1,1,,B,K5DfMB9FLsM?P00d,0*61"
        decoded = NMEAMessage(msg)
        self.assertEqual(decoded.talker, TalkerID.Repeater_Station)

    def test_bs(self):
        msg = b"!BSVDM,1,1,,B,K5DfMB9FLsM?P00d,0*69"
        decoded = NMEAMessage(msg)
        self.assertEqual(decoded.talker, TalkerID.Base_Station_Deprecated)

    def test_sa(self):
        msg = b"!SAVDM,1,1,,B,K5DfMB9FLsM?P00d,0*6A"
        decoded = NMEAMessage(msg)
        self.assertEqual(decoded.talker, TalkerID.Physical_Shore_Station)

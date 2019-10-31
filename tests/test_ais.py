import unittest
from pyais.messages import NMEAMessage
from pyais.ais_types import AISType
from pyais.constants import ManeuverIndicator, NavigationStatus, ShipType
from bitarray import bitarray


class TestAIS(unittest.TestCase):
    """
    TestCases for AIS message decoding and assembling.
    """

    def test_nmea(self):
        """
        Test if ais message still contains the original nmea message
        """
        nmea = NMEAMessage(b"!AIVDM,1,1,,B,91b55wi;hbOS@OdQAC062Ch2089h,0*30")
        assert nmea.decode().nmea == nmea

    def test_msg_type(self):
        """
        Test if msg type is correct
        """
        nmea = NMEAMessage(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")
        assert nmea.decode().msg_type == AISType.POS_CLASS_A1

        nmea = NMEAMessage(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
        assert nmea.decode().msg_type == AISType.POS_CLASS_A1

        nmea = NMEAMessage.assemble_from_iterable(messages=[
            NMEAMessage(b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08"),
            NMEAMessage(b"!AIVDM,2,2,4,A,000000000000000,2*20")
        ])
        assert nmea.decode().msg_type == AISType.STATIC_AND_VOYAGE

    def test_msg_getitem(self):
        """
        Test if one can get items
        """
        msg = NMEAMessage(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05").decode()
        assert msg['repeat'] == 0

    def test_msg_type_1(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C").decode()
        assert msg.content == {'type': 1, 'repeat': 0, 'mmsi': 366053209,
                               'status': NavigationStatus.RestrictedManoeuverability, 'turn': 0,
                               'speed': 0,
                               'accuracy': 0,
                               'lon': -122.34161833333333, 'lat': 37.80211833333333, 'course': 219.3,
                               'heading': 1,
                               'second': 59, 'maneuver': ManeuverIndicator.NotAvailable, 'raim': False,
                               'radio': 2281}

    def test_msg_type_4(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,403OviQuMGCqWrRO9>E6fE700@GO,0*4D").decode()
        assert round(msg['lon'], 4) == -76.3524
        assert round(msg['lat'], 4) == 36.8838
        assert msg['accuracy'] == 1
        assert msg['year'] == 2007
        assert msg['month'] == 5
        assert msg['day'] == 14
        assert msg['minute'] == 57
        assert msg['second'] == 39

    def test_msg_type_5(self):
        msg = NMEAMessage.assemble_from_iterable(messages=[
            NMEAMessage(b"!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C"),
            NMEAMessage(b"!AIVDM,2,2,1,A,88888888880,2*25")
        ]).decode()
        assert msg['callsign'] == "3FOF8"
        assert msg['shipname'] == "EVER DIADEM"
        assert msg['shiptype'] == ShipType.Cargo
        assert msg['to_bow'] == 225
        assert msg['to_stern'] == 70
        assert msg['to_port'] == 1
        assert msg['to_starboard'] == 31
        assert msg['draught'] == 12.2
        assert msg['destination'] == "NEW YORK"

    def test_msg_type_6(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,B,6B?n;be:cbapalgc;i6?Ow4,2*4A").decode()
        assert msg['seqno'] == 3
        assert msg['dest_mmsi'] == 313240222
        assert msg['dac'] == 669
        assert msg['fid'] == 11

    def test_msg_type_7(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,702R5`hwCjq8,0*6B").decode()
        assert msg['mmsi1'] == 265538450

    def test_msg_type_8(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47").decode()

        assert msg.nmea.is_valid
        assert msg['repeat'] == 0
        assert msg.msg_type == AISType.BINARY_BROADCAST
        assert msg['mmsi'] == 366999712
        assert msg['dac'] == 366
        assert msg['fid'] == 56
        assert msg['data'] == bitarray(
            "0011101001010011110110111011011110111110010010100111011100110001001101111111100001111101011110110000010001000"
            "1011111000001000000110111101010000001011101100100111111010110010011011110000011000110010100101011101001101110"
            "01110110011101101111100000010111111011")

    def test_msg_type_9(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,B,91b55wi;hbOS@OdQAC062Ch2089h,0*30").decode()
        assert msg.msg_type == AISType.SAR_AIRCRAFT_POS
        assert msg['repeat'] == 0
        assert msg['mmsi'] == 111232511
        assert msg['alt'] == 303
        assert msg['speed'] == 42
        assert msg['accuracy'] == 0
        assert round(msg['lon'], 5) == -6.27884
        assert round(msg['lat'], 5) == 58.144
        assert msg['course'] == 154.5
        assert msg['second'] == 15
        assert msg['dte'] == 1
        assert msg['radio'] == 33392

    def test_msg_type_18(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,B52KlJP00=l4be5ItJ6r3wVUWP06,0*7C").decode()
        assert msg.content == {'type': 18, 'repeat': 0, 'mmsi': 338097258, 'speed': 0, 'accuracy': False,
                               'lon': -122.27014333333334, 'lat': 37.786295, 'course': 297.6,
                               'heading': 511,
                               'second': 13, 'regional': 0, 'cs': True, 'display': False, 'dsc': True,
                               'band': True,
                               'msg22': False, 'assigned': False, 'raim': True, 'radio': 917510}

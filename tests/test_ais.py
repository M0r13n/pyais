import unittest
from pyais.messages import NMEAMessage
from pyais.ais_types import AISType
from pyais.constants import ManeuverIndicator, NavigationStatus, ShipType
from bitarray import bitarray


class TestAIS(unittest.TestCase):
    """
    TestCases for AIS message decoding and assembling.

    The Test messages are from multiple sources and are scrambled together.
    Raw messages are decoded by either hand or some online decoder.
    As my main source of AIS messages I used this dumb:
    https://www.aishub.net/ais-dispatcher

    As my main decoder I used this decoder:
    http://ais.tbsalling.dk

    The latter sometimes is a bit weird and therefore I used aislib to verify my results.
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

    def test_msg_type_10(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,B,:5MlU41GMK6@,0*6C").decode()
        assert msg['dest_mmsi'] == 366832740

        msg = NMEAMessage(b"!AIVDM,1,1,,B,:6TMCD1GOS60,0*5B").decode()
        assert msg['dest_mmsi'] == 366972000

    def test_msg_type_11(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,B,;4R33:1uUK2F`q?mOt@@GoQ00000,0*5D").decode()
        assert round(msg['lon'], 4) == -94.4077
        assert round(msg['lat'], 4) == 28.4091
        assert msg['accuracy'] == 1
        assert msg['type'] == 11
        assert msg['year'] == 2009
        assert msg['month'] == 5
        assert msg['day'] == 22
        assert msg['hour'] == 2
        assert msg['minute'] == 22
        assert msg['second'] == 40

    def test_msg_type_12(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,<5?SIj1;GbD07??4,0*38").decode()
        assert msg['type'] == 12
        assert msg['repeat'] == 0
        assert msg['mmsi'] == 351853000
        assert msg['seqno'] == 0
        assert msg['dest_mmsi'] == 316123456
        assert msg['retransmit'] == 0
        assert msg['text'] == "GOOD"

        msg = NMEAMessage(b"!AIVDM,1,1,,A,<42Lati0W:Ov=C7P6B?=Pjoihhjhqq0,2*2B").decode()
        assert msg['type'] == 12
        assert msg['repeat'] == 0
        assert msg['mmsi'] == 271002099
        assert msg['seqno'] == 0
        assert msg['dest_mmsi'] == 271002111
        assert msg['retransmit'] == 1
        assert msg['text'] == "MSG FROM 271002099"

    def test_msg_type_13(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,=39UOj0jFs9R,0*65").decode()
        assert msg['type'] == 13
        assert msg['repeat'] == 0
        assert msg['mmsi'] == 211378120
        assert msg['mmsi1'] == 211217560

    def test_msg_type_14(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,>5?Per18=HB1U:1@E=B0m<L,2*51").decode()
        assert msg['type'] == 14
        assert msg['repeat'] == 0
        assert msg['mmsi'] == 351809000
        assert msg['text'] == "RCVD YR TEST MSG"

    def test_msg_type_15(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,?5OP=l00052HD00,2*5B").decode()
        assert msg['type'] == 15
        assert msg['repeat'] == 0
        assert msg['mmsi'] == 368578000
        assert msg['offset1_1'] == 0

        msg = NMEAMessage(b"!AIVDM,1,1,,B,?h3Ovn1GP<K0<P@59a0,2*04").decode()
        assert msg['type'] == 15
        assert msg['repeat'] == 3
        assert msg['mmsi'] == 3669720
        assert msg['mmsi1'] == 367014320
        assert msg['type1_1'] == 3

        assert msg['mmsi2'] == 0
        assert msg['type1_2'] == 5
        assert msg['offset1_2'] == 617

    def test_msg_type_16(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,@01uEO@mMk7P<P00,0*18").decode()
        assert msg['type'] == 16
        assert msg['repeat'] == 0
        assert msg['mmsi'] == 2053501
        assert msg['mmsi1'] == 224251000
        assert msg['offset1'] == 200
        assert msg['increment1'] == 0

        assert msg['mmsi2'] == 0
        assert msg['offset2'] == 0
        assert msg['increment1'] == 0

    def test_msg_type_17(self):
        msg = NMEAMessage.assemble_from_iterable(messages=[
            NMEAMessage(b"!AIVDM,2,1,5,A,A02VqLPA4I6C07h5Ed1h<OrsuBTTwS?r:C?w`?la<gno1RTRwSP9:BcurA8a,0*3A"),
            NMEAMessage(b"!AIVDM,2,2,5,A,:Oko02TSwu8<:Jbb,0*11")
        ]).decode()
        n = 0x7c0556c07031febbf52924fe33fa2933ffa0fd2932fdb7062922fe3809292afde9122929fcf7002923ffd20c29aaaa
        assert msg['type'] == 17
        assert msg['repeat'] == 0
        assert msg['mmsi'] == 2734450
        assert msg['lon'] == 17478
        assert msg['lat'] == 35992
        assert msg['data'] == n

        msg = NMEAMessage(b"!AIVDM,1,1,,A,A0476BQ>J8`<h2JpH:4P0?j@2mTEw8`=DP1DEnqvj0,0*79").decode()
        assert msg['type'] == 17
        assert msg['repeat'] == 0
        assert msg['mmsi'] == 4310602
        assert msg['lat'] == 20582
        assert msg['lon'] == 80290
        assert msg['data'] == 14486955885545814640451754168044205828166539334830080

    def test_msg_type_18(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,B52KlJP00=l4be5ItJ6r3wVUWP06,0*7C").decode()
        assert msg.content == {'type': 18, 'repeat': 0, 'mmsi': 338097258, 'speed': 0, 'accuracy': False,
                               'lon': -122.27014333333334, 'lat': 37.786295, 'course': 297.6,
                               'heading': 511,
                               'second': 13, 'regional': 0, 'cs': True, 'display': False, 'dsc': True,
                               'band': True,
                               'msg22': False, 'assigned': False, 'raim': True, 'radio': 917510}

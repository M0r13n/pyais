import unittest

from pyais import decode_msg
from pyais.ais_types import AISType
from pyais.constants import ManeuverIndicator, NavigationStatus, ShipType, NavAid, EpfdType
from pyais.exceptions import UnknownMessageException
from pyais.messages import AISMessage, NMEAMessage
from pyais.stream import ByteStream


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

    def test_to_json(self):
        json_dump = NMEAMessage(b"!AIVDM,1,1,,A,15NPOOPP00o?b=bE`UNv4?w428D;,0*24").decode().to_json()
        text = """{
    "nmea": {
        "ais_id": 1,
        "raw": "!AIVDM,1,1,,A,15NPOOPP00o?b=bE`UNv4?w428D;,0*24",
        "talker": "AI",
        "type": "VDM",
        "message_fragments": 1,
        "fragment_number": 1,
        "message_id": null,
        "channel": "A",
        "payload": "15NPOOPP00o?b=bE`UNv4?w428D;",
        "fill_bits": 0,
        "checksum": 36,
        "bit_array": "000001000101011110100000011111011111100000100000000000000000110111001111101010001101101010010101101000100101011110111110000100001111111111000100000010001000010100001011"
    },
    "decoded": {
        "type": 1,
        "repeat": 0,
        "mmsi": "367533950",
        "status": 0,
        "turn": -128,
        "speed": 0.0,
        "accuracy": 1,
        "lon": -122.40823166666667,
        "lat": 37.808418333333336,
        "course": 360.0,
        "heading": 511,
        "second": 34,
        "maneuver": 0,
        "raim": 1,
        "radio": 34059
    }
}"""
        self.assertEqual(json_dump, text)

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
        assert msg.content == {'type': 1, 'repeat': 0, 'mmsi': "366053209",
                               'status': NavigationStatus.RestrictedManoeuverability, 'turn': 0,
                               'speed': 0,
                               'accuracy': 0,
                               'lon': -122.34161833333333, 'lat': 37.80211833333333, 'course': 219.3,
                               'heading': 1,
                               'second': 59, 'maneuver': ManeuverIndicator.NotAvailable, 'raim': False,
                               'radio': 2281}

        msg = NMEAMessage(b"!AIVDM,1,1,,A,15NPOOPP00o?b=bE`UNv4?w428D;,0*24").decode()
        assert msg['type'] == 1
        assert msg['mmsi'] == "367533950"
        assert msg['repeat'] == 0
        assert msg['status'] == NavigationStatus.UnderWayUsingEngine
        assert msg['turn'] == -128
        assert msg['speed'] == 0
        assert msg['accuracy'] == 1
        assert round(msg['lat'], 4) == 37.8084
        assert round(msg['lon'], 4) == -122.4082
        assert msg['course'] == 360
        assert msg['heading'] == 511
        assert msg['second'] == 34
        assert msg['maneuver'] == ManeuverIndicator.NotAvailable
        assert msg['raim']

        msg = NMEAMessage(b"!AIVDM,1,1,,B,181:Kjh01ewHFRPDK1s3IRcn06sd,0*08").decode()
        assert msg['course'] == 87.0
        assert msg['mmsi'] == "538090443"
        assert msg['speed'] == 10.9

    def test_decode_pos_1_2_3(self):
        # weired message of type 0 as part of issue #4
        msg: NMEAMessage = NMEAMessage(b"!AIVDM,1,1,,B,0S9edj0P03PecbBN`ja@0?w42cFC,0*7C")

        assert msg.is_valid
        content: AISMessage = msg.decode(silent=False)
        assert msg

        assert content['repeat'] == 2
        assert content['mmsi'] == "211512520"
        assert content['turn'] == -128
        assert content['speed'] == 0.3
        assert round(content['lat'], 4) == 53.5427
        assert round(content['lon'], 4) == 9.9794
        assert round(content['course'], 1) == 0.0

        msg: NMEAMessage = NMEAMessage(b"!AIVDM,1,1,,B,0S9edj0P03PecbBN`ja@0?w42cFC,0*7C")
        assert msg.decode().to_json()

    def test_msg_type_3(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,35NSH95001G?wopE`beasVk@0E5:,0*6F").decode()
        assert msg['type'] == 3
        assert msg['mmsi'] == "367581220"
        assert msg['repeat'] == 0
        assert msg['status'] == NavigationStatus.Moored
        assert msg['turn'] == 0
        assert msg['speed'] == 0.1
        assert msg['accuracy'] == 0
        assert round(msg['lat'], 4) == 37.8107
        assert round(msg['lon'], 4) == -122.3343
        assert round(msg['course'], 1) == 254.2
        assert msg['heading'] == 217
        assert msg['second'] == 40
        assert msg['maneuver'] == ManeuverIndicator.NotAvailable
        assert not msg['raim']

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

        msg = NMEAMessage(b"!AIVDM,1,1,,B,403OtVAv>lba;o?Ia`E`4G?02H6k,0*44").decode()
        assert round(msg['lon'], 4) == -122.4648
        assert round(msg['lat'], 4) == 37.7943
        assert msg['mmsi'] == "003669145"
        assert msg['accuracy'] == 1
        assert msg['year'] == 2019
        assert msg['month'] == 11
        assert msg['day'] == 9
        assert msg['hour'] == 10
        assert msg['minute'] == 41
        assert msg['second'] == 11

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
        assert msg['dte'] == 0

    def test_msg_type_6(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,B,6B?n;be:cbapalgc;i6?Ow4,2*4A").decode()
        assert msg['seqno'] == 3
        assert msg['dest_mmsi'] == "313240222"
        assert msg['dac'] == 669
        assert msg['fid'] == 11

    def test_msg_type_7(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,702R5`hwCjq8,0*6B").decode()
        assert msg['mmsi1'] == "265538450"

    def test_msg_type_8(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47").decode()

        assert msg.nmea.is_valid
        assert msg['repeat'] == 0
        assert msg.msg_type == AISType.BINARY_BROADCAST
        assert msg['mmsi'] == "366999712"
        assert msg['dac'] == 366
        assert msg['fid'] == 56
        assert msg['data'] == "00111010010100111101101110110111101111100100101001110111001100010011011111111" \
                              "00001111101011110110000010001000101111100000100000011011110101000000101110110" \
                              "01001111110101100100110111100000110001100101001010111010011011100111011001110" \
                              "1101111100000010111111011"

    def test_msg_type_9(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,B,91b55wi;hbOS@OdQAC062Ch2089h,0*30").decode()
        assert msg.msg_type == AISType.SAR_AIRCRAFT_POS
        assert msg['repeat'] == 0
        assert msg['mmsi'] == "111232511"
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
        assert msg['dest_mmsi'] == "366832740"

        msg = NMEAMessage(b"!AIVDM,1,1,,B,:6TMCD1GOS60,0*5B").decode()
        assert msg['dest_mmsi'] == "366972000"

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
        assert msg['mmsi'] == "351853000"
        assert msg['seqno'] == 0
        assert msg['dest_mmsi'] == "316123456"
        assert msg['retransmit'] == 0
        assert msg['text'] == "GOOD"

        msg = NMEAMessage(b"!AIVDM,1,1,,A,<42Lati0W:Ov=C7P6B?=Pjoihhjhqq0,2*2B").decode()
        assert msg['type'] == 12
        assert msg['repeat'] == 0
        assert msg['mmsi'] == "271002099"
        assert msg['seqno'] == 0
        assert msg['dest_mmsi'] == "271002111"
        assert msg['retransmit'] == 1
        assert msg['text'] == "MSG FROM 271002099"

    def test_msg_type_13(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,=39UOj0jFs9R,0*65").decode()
        assert msg['type'] == 13
        assert msg['repeat'] == 0
        assert msg['mmsi'] == "211378120"
        assert msg['mmsi1'] == "211217560"

    def test_msg_type_14(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,>5?Per18=HB1U:1@E=B0m<L,2*51").decode()
        assert msg['type'] == 14
        assert msg['repeat'] == 0
        assert msg['mmsi'] == "351809000"
        assert msg['text'] == "RCVD YR TEST MSG"

    def test_msg_type_15(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,?5OP=l00052HD00,2*5B").decode()
        assert msg['type'] == 15
        assert msg['repeat'] == 0
        assert msg['mmsi'] == "368578000"
        assert msg['offset1_1'] == 0

        msg = NMEAMessage(b"!AIVDM,1,1,,B,?h3Ovn1GP<K0<P@59a0,2*04").decode()
        assert msg['type'] == 15
        assert msg['repeat'] == 3
        assert msg['mmsi'] == "003669720"
        assert msg['mmsi1'] == "367014320"
        assert msg['type1_1'] == 3
        assert msg['type1_2'] == 5
        assert msg['offset1_2'] == 617
        assert msg['offset1_1'] == 516

    def test_msg_type_16(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,@01uEO@mMk7P<P00,0*18").decode()
        assert msg['type'] == 16
        assert msg['repeat'] == 0
        assert msg['mmsi'] == "002053501"
        assert msg['mmsi1'] == "224251000"
        assert msg['offset1'] == 200
        assert msg['increment1'] == 0

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
        assert msg['mmsi'] == "002734450"
        assert msg['lon'] == 17478
        assert msg['lat'] == 35992
        assert msg['data'] == n

        msg = NMEAMessage(b"!AIVDM,1,1,,A,A0476BQ>J8`<h2JpH:4P0?j@2mTEw8`=DP1DEnqvj0,0*79").decode()
        assert msg['type'] == 17
        assert msg['repeat'] == 0
        assert msg['mmsi'] == "004310602"
        assert msg['lat'] == 20582
        assert msg['lon'] == 80290
        assert msg['data'] == 14486955885545814640451754168044205828166539334830080

    def test_msg_type_18(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,B5NJ;PP005l4ot5Isbl03wsUkP06,0*76").decode()
        assert msg['type'] == 18
        assert msg['mmsi'] == "367430530"
        assert msg['speed'] == 0
        assert msg['accuracy'] == 0
        assert round(msg['lat'], 2) == 37.79
        assert round(msg['lon'], 2) == -122.27
        assert msg['course'] == 0
        assert msg['heading'] == 511
        assert msg['second'] == 55
        assert msg['regional'] == 0
        assert msg['cs'] == 1
        assert msg['display'] == 0
        assert msg['dsc'] == 1
        assert msg['msg22'] == 1
        assert msg['raim'] == 0

    def test_msg_type_19(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,B,C5N3SRgPEnJGEBT>NhWAwwo862PaLELTBJ:V00000000S0D:R220,0*0B").decode()
        assert msg['type'] == 19
        assert msg['mmsi'] == "367059850"
        assert round(msg['speed'], 1) == 8.7
        assert msg['accuracy'] == 0
        assert round(msg['lat'], 2) == 29.54
        assert round(msg['lon'], 2) == -88.81
        assert round(msg['course'], 2) == 335.9
        assert msg['heading'] == 511
        assert msg['second'] == 46
        assert msg['shipname'] == "CAPT.J.RIMES"
        assert msg['shiptype'] == ShipType(70)
        assert msg['to_bow'] == 5
        assert msg['to_stern'] == 21
        assert msg['to_port'] == 4
        assert msg['to_starboard'] == 4

    def test_msg_type_20(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,D028rqP<QNfp000000000000000,2*0C").decode()
        assert msg['type'] == 20
        assert msg['mmsi'] == "002243302"
        assert msg['offset1'] == 200
        assert msg['number1'] == 5
        assert msg['timeout1'] == 7
        assert msg['increment1'] == 750

        # All other values are zero
        for k, v in msg.content.items():
            if k not in ('type', 'mmsi', 'offset1', 'number1', 'timeout1', 'increment1'):
                assert not v

    def test_msg_type_21(self):
        msg = NMEAMessage.assemble_from_iterable(messages=[
            NMEAMessage(b"!AIVDM,2,1,7,B,E4eHJhPR37q0000000000000000KUOSc=rq4h00000a,0*4A"),
            NMEAMessage(b"!AIVDM,2,2,7,B,@20,4*54")
        ]).decode()
        assert msg['type'] == 21
        assert msg['mmsi'] == "316021442"
        assert msg['aid_type'] == NavAid.REFERENCE_POINT
        assert msg['name'] == "DFO2"
        assert msg['accuracy'] == 1
        assert round(msg['lat'], 2) == 48.65
        assert round(msg['lon'], 2) == -123.43
        assert not msg['to_bow']
        assert not msg['to_stern']
        assert not msg['to_port']
        assert not msg['to_starboard']

        assert msg['off_position']
        assert msg['regional'] == 0
        assert msg['raim']
        assert msg['virtual_aid'] == 0
        assert msg['assigned'] == 0
        assert msg['name_extension'] == ""

    def test_msg_type_22(self):
        # Broadcast
        msg = NMEAMessage(b"!AIVDM,1,1,,B,F030p:j2N2P5aJR0r;6f3rj10000,0*11").decode()
        assert msg['type'] == 22
        assert msg['mmsi'] == "003160107"
        assert msg['channel_a'] == 2087
        assert msg['channel_b'] == 2088
        assert msg['power'] == 0

        assert msg['ne_lon'] == -7710.0
        assert msg['ne_lat'] == 3300.0
        assert msg['sw_lon'] == -8020.0
        assert msg['sw_lat'] == 3210

        assert msg['band_a'] == 0
        assert msg['band_b'] == 0
        assert msg['zonesize'] == 2

        assert 'dest1' not in msg.content.keys()
        assert 'dest2' not in msg.content.keys()

        # Addressed
        msg = NMEAMessage(b"!AIVDM,1,1,,A,F@@W>gOP00PH=JrN9l000?wB2HH;,0*44").decode()
        assert msg['type'] == 22
        assert msg['mmsi'] == "017419965"
        assert msg['channel_a'] == 3584
        assert msg['channel_b'] == 8
        assert msg['power'] == 1
        assert msg['addressed'] == 1

        assert msg['dest1'] == "028144881"
        assert msg['dest2'] == "268435519"

        assert msg['band_a'] == 0
        assert msg['band_b'] == 0
        assert msg['zonesize'] == 4

        assert 'ne_lon' not in msg.content.keys()
        assert 'ne_lat' not in msg.content.keys()
        assert 'sw_lon' not in msg.content.keys()
        assert 'sw_lat' not in msg.content.keys()

    def test_msg_type_23(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,B,G02:Kn01R`sn@291nj600000900,2*12").decode()
        assert msg['type'] == 23
        assert msg['mmsi'] == "002268120"
        assert msg['ne_lon'] == 157.8
        assert msg['shiptype'] == ShipType.NotAvailable
        assert round(msg['ne_lat'], 1) == 3064.2
        assert round(msg['sw_lon'], 1) == 109.6
        assert round(msg['sw_lat'], 1) == 3040.8

    def test_msg_type_24(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,H52KMeDU653hhhi0000000000000,0*1A").decode()
        assert msg['type'] == 24
        assert msg['mmsi'] == "338091445"
        assert msg['partno'] == 1
        assert msg['shiptype'] == ShipType.PleasureCraft
        assert msg['vendorid'] == "FEC"
        assert msg['callsign'] == ""
        assert msg['to_bow'] == 0
        assert msg['to_stern'] == 0
        assert msg['to_port'] == 0
        assert msg['to_starboard'] == 0
        assert msg['mothership_mmsi'] == "000000000"

    def test_msg_type_25(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,I6SWo?8P00a3PKpEKEVj0?vNP<65,0*73").decode()

        assert msg['type'] == 25
        assert msg['addressed']
        assert not msg['structured']
        assert msg['dest_mmsi'] == "134218384"

    def test_msg_type_26(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,A,JB3R0GO7p>vQL8tjw0b5hqpd0706kh9d3lR2vbl0400,2*40").decode()
        assert msg['type'] == 26
        assert msg['addressed']
        assert msg['structured']
        assert msg['dest_mmsi'] == "838351848"

        msg = NMEAMessage(b"!AIVDM,1,1,,A,J0@00@370>t0Lh3P0000200H:2rN92,4*14").decode()
        assert msg['type'] == 26
        assert not msg['addressed']
        assert not msg['structured']

    def test_msg_type_27(self):
        msg = NMEAMessage(b"!AIVDM,1,1,,B,KC5E2b@U19PFdLbMuc5=ROv62<7m,0*16").decode(silent=False)
        assert msg
        assert msg['type'] == 27
        assert msg['mmsi'] == "206914217"
        assert msg['accuracy'] == 0
        assert msg['raim'] == 0
        assert msg['status'] == NavigationStatus.NotUnderCommand
        assert round(msg['lon'], 3) == 137.023
        assert round(msg['lat'], 2) == 4.84
        assert msg['speed'] == 57
        assert msg['course'] == 167
        assert msg['gnss'] == 0

    def test_broken_messages(self):
        # Undefined epfd
        assert NMEAMessage(b"!AIVDM,1,1,,B,4>O7m7Iu@<9qUfbtm`vSnwvH20S8,0*46").decode()['epfd'] == EpfdType.Undefined

    def test_multiline_message(self):
        # these messages caused issue #3
        msg_1_part_0 = b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07'
        msg_1_part_1 = b'!AIVDM,2,2,1,A,F@V@00000000000,2*35'

        assert NMEAMessage.assemble_from_iterable(
            messages=[
                NMEAMessage(msg_1_part_0),
                NMEAMessage(msg_1_part_1)
            ]
        ).decode().to_json()

        msg_2_part_0 = b'!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F'
        msg_2_part_1 = b'!AIVDM,2,2,9,A,F@V@00000000000,2*3D'

        assert NMEAMessage.assemble_from_iterable(
            messages=[
                NMEAMessage(msg_2_part_0),
                NMEAMessage(msg_2_part_1)
            ]
        ).decode().to_json()

    def test_byte_stream(self):
        messages = [
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
            b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
            b'!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
            b'!AIVDM,2,2,9,A,F@V@00000000000,2*3D',
        ]
        counter = 0
        for msg in ByteStream(messages):
            decoded = msg.decode()
            assert decoded['shipname'] == 'NORDIC HAMBURG'
            assert decoded['mmsi'] == "210035000"
            assert decoded
            counter += 1
        assert counter == 2

    def test_fail_silently(self):
        # this tests combines testing for an UnknownMessageException and the silent param at once
        msg = b"!AIVDM,1,1,,A,U31<0OOP000CshrMdl600?wP00SL,0*43"
        nmea = NMEAMessage(msg)

        with self.assertRaises(UnknownMessageException):
            nmea.decode(silent=False)

        # by default errors are ignored and an empty AIS message is returned
        assert nmea.decode() is not None
        assert isinstance(nmea.decode(), AISMessage)
        text = """{
    "nmea": {
        "ais_id": 37,
        "raw": "!AIVDM,1,1,,A,U31<0OOP000CshrMdl600?wP00SL,0*43",
        "talker": "AI",
        "type": "VDM",
        "message_fragments": 1,
        "fragment_number": 1,
        "message_id": null,
        "channel": "A",
        "payload": "U31<0OOP000CshrMdl600?wP00SL",
        "fill_bits": 0,
        "checksum": 67,
        "bit_array": "100101000011000001001100000000011111011111100000000000000000000000010011111011110000111010011101101100110100000110000000000000001111111111100000000000000000100011011100"
    },
    "decoded": {}
}"""
        self.assertEqual(nmea.decode().to_json(), text)

    def test_empty_channel(self):
        msg = b"!AIVDO,1,1,,,B>qc:003wk?8mP=18D3Q3wgTiT;T,0*13"

        self.assertEqual(NMEAMessage(msg).channel, "")

        content = decode_msg(msg)
        self.assertEqual(content["type"], 18)
        self.assertEqual(content["repeat"], 0)
        self.assertEqual(content["mmsi"], "1000000000")
        self.assertEqual(format(content["speed"], ".1f"), "102.3")
        self.assertEqual(content["accuracy"], 0)
        self.assertEqual(str(content["lon"]), "181.0")
        self.assertEqual(str(content["lat"]), "91.0")
        self.assertEqual(str(content["course"]), "360.0")
        self.assertEqual(content["heading"], 511)
        self.assertEqual(content["second"], 31)
        self.assertEqual(content["regional"], 0)
        self.assertEqual(content["cs"], 1)
        self.assertEqual(content["display"], 0)
        self.assertEqual(content["band"], 1)
        self.assertEqual(content["radio"], 410340)

    def test_msg_with_more_that_82_chars_payload(self):
        content = decode_msg(
            "!AIVDM,1,1,,B,53ktrJ82>ia4=50<0020<5=@Dhv0t8T@u<0000001PV854Si0;mR@CPH13p0hDm1C3h0000,2*35"
        )

        self.assertEqual(content["type"], 5)
        self.assertEqual(content["mmsi"], "255801960")
        self.assertEqual(content["repeat"], 0)
        self.assertEqual(content["ais_version"], 2)
        self.assertEqual(content["imo"], 9356945)
        self.assertEqual(content["callsign"], "CQPC")
        self.assertEqual(content["shipname"], "CASTELO OBIDOS")
        self.assertEqual(content["shiptype"], ShipType.NotAvailable)
        self.assertEqual(content["to_bow"], 12)
        self.assertEqual(content["to_stern"], 38)
        self.assertEqual(content["to_port"], 8)
        self.assertEqual(content["to_starboard"], 5)
        self.assertEqual(content["epfd"], EpfdType.GPS)
        self.assertEqual(content["month"], 2)
        self.assertEqual(content["day"], 7)
        self.assertEqual(content["hour"], 17)
        self.assertEqual(content["minute"], 0)
        self.assertEqual(content["draught"], 4.7)
        self.assertEqual(content["destination"], "VIANA DO CASTELO")

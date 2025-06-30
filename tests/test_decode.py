import base64
import datetime
import itertools
import json
import textwrap
import typing
import unittest

from pyais import NMEAMessage, encode_dict, encode_msg
from pyais.ais_types import AISType
from pyais.constants import (
    EpfdType,
    InlandLoadedType,
    ManeuverIndicator,
    NavAid,
    NavigationStatus,
    ShipType,
    StationType,
    SyncState,
    TransmitMode,
    TurnRate,
)
from pyais.decode import decode, decode_nmea_and_ais, decode_nmea_line
from pyais.exceptions import (
    InvalidNMEAChecksum,
    InvalidNMEAMessageException,
    MissingMultipartMessageException,
    TooManyMessagesException,
    UnknownMessageException,
    NonPrintableCharacterException,
)
from pyais.messages import (
    MSG_CLASS,
    AISSentence,
    GatehouseSentence,
    MessageType16DestinationA,
    MessageType16DestinationAB,
    MessageType5,
    MessageType6,
    MessageType8Dac200Fid10,
    MessageType18,
    MessageType22Addressed,
    MessageType22Broadcast,
    MessageType24PartA,
    MessageType24PartB,
    MessageType25AddressedStructured,
    MessageType25AddressedUnstructured,
    MessageType25BroadcastStructured,
    MessageType25BroadcastUnstructured,
    MessageType26AddressedStructured,
    MessageType26BroadcastStructured,
    MessageType26BroadcastUnstructured,
)
from pyais.stream import ByteStream, IterMessages
from pyais.util import b64encode_str, bits2bytes, bytes2bits, decode_into_bit_array
from pyais.exceptions import MissingPayloadException


def ensure_type_for_msg_dict(msg_dict: typing.Dict[str, typing.Any]) -> None:
    cls = MSG_CLASS[msg_dict["msg_type"]]
    for field in cls.fields():
        try:
            attr = msg_dict[field.name]
        except KeyError:
            if field.name.startswith('spare'):
                # spare fields may be missing
                continue
            raise
        if attr is None:
            continue
        err_msg = (
            f"Invalid type for Typ: {msg_dict['msg_type']} and field '{field.name}'."
        )
        err_msg += f"Expected type '{field.metadata['d_type']}', but got {type(attr)}"
        assert isinstance(attr, field.metadata["d_type"]), err_msg


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

    maxDiff = None

    def test_to_json(self):
        json_dump = decode(b"!AIVDM,1,1,,A,15NPOOPP00o?b=bE`UNv4?w428D;,0*24").to_json(ignore_spare=False)
        text = textwrap.dedent(
            """{
    "msg_type": 1,
    "repeat": 0,
    "mmsi": 367533950,
    "status": 0,
    "turn": -128.0,
    "speed": 0.0,
    "accuracy": true,
    "lon": -122.408232,
    "lat": 37.808418,
    "course": 360.0,
    "heading": 511,
    "second": 34,
    "maneuver": 0,
    "raim": true,
    "radio": 34059
}"""
        )
        self.assertEqual(json_dump, text)

    def test_msg_type(self):
        """
        Test if msg type is correct
        """
        nmea = NMEAMessage(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")
        assert nmea.decode().msg_type == AISType.POS_CLASS_A1

        nmea = NMEAMessage(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
        assert nmea.decode().msg_type == AISType.POS_CLASS_A1

        nmea = NMEAMessage.assemble_from_iterable(
            messages=[
                NMEAMessage(
                    b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08"
                ),
                NMEAMessage(b"!AIVDM,2,2,4,A,000000000000000,2*20"),
            ]
        )
        assert nmea.decode().msg_type == AISType.STATIC_AND_VOYAGE

    def test_msg_type_1_a(self):
        result = decode(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C").asdict()

        assert result == {
            "msg_type": 1,
            "repeat": 0,
            "mmsi": 366053209,
            "status": NavigationStatus.RestrictedManoeuverability,
            "turn": 0,
            "speed": 0.0,
            "accuracy": False,
            "lon": -122.341618,
            "lat": 37.802118,
            "course": 219.3,
            "heading": 1,
            "second": 59,
            "maneuver": ManeuverIndicator.NotAvailable,
            "raim": False,
            "radio": 2281,
        }

    def test_msg_type_1_b(self):
        msg = decode(b"!AIVDM,1,1,,A,15NPOOPP00o?b=bE`UNv4?w428D;,0*24").asdict()
        assert msg["msg_type"] == 1
        assert msg["mmsi"] == 367533950
        assert msg["repeat"] == 0
        assert msg["status"] == NavigationStatus.UnderWayUsingEngine
        assert msg["turn"] == TurnRate.NO_TI_DEFAULT
        assert msg["speed"] == 0
        assert msg["accuracy"] == 1
        assert round(msg["lat"], 4) == 37.8084
        assert round(msg["lon"], 4) == -122.4082
        assert msg["course"] == 360
        assert msg["heading"] == 511
        assert msg["second"] == 34
        assert msg["maneuver"] == ManeuverIndicator.NotAvailable
        assert msg["raim"]
        assert isinstance(msg["raim"], bool)

    def test_msg_type_1_c(self):
        msg = decode(b"!AIVDM,1,1,,B,181:Kjh01ewHFRPDK1s3IRcn06sd,0*08")

        content = msg.asdict()

        assert content["course"] == 87.0
        assert content["mmsi"] == 538090443
        assert content["speed"] == 10.9
        assert content["turn"] == 0

        ensure_type_for_msg_dict(content)

    def test_decode_pos_1_2_3(self):
        # weired message of type 0 as part of issue #4
        msg = decode(b"!AIVDM,1,1,,B,0S9edj0P03PecbBN`ja@0?w42cFC,0*7C")

        content = msg.asdict()

        assert content["repeat"] == 2
        assert content["mmsi"] == 211512520
        assert content["turn"] == TurnRate.NO_TI_DEFAULT
        assert content["speed"] == 0.3
        assert round(content["lat"], 4) == 53.5427
        assert round(content["lon"], 4) == 9.9794
        assert round(content["course"], 1) == 0.0

        assert decode(b"!AIVDM,1,1,,B,0S9edj0P03PecbBN`ja@0?w42cFC,0*7C").to_json()

    def test_decode_1_speed(self):
        content = decode(b"!AIVDM,1,1,,A,13@nePh01>PjcO4PGReoJEmL0HJg,0*67").asdict()

        assert content["speed"] == 7.8
        assert content["msg_type"] == 1

    def test_msg_type_3(self):
        msg = decode(b"!AIVDM,1,1,,A,35NSH95001G?wopE`beasVk@0E5:,0*6F").asdict()
        assert msg["msg_type"] == 3
        assert msg["mmsi"] == 367581220
        assert msg["repeat"] == 0
        assert msg["status"] == NavigationStatus.Moored
        assert msg["turn"] == 0
        assert msg["speed"] == 0.1
        assert msg["accuracy"] == 0
        assert round(msg["lat"], 4) == 37.8107
        assert round(msg["lon"], 4) == -122.3343
        assert round(msg["course"], 1) == 254.2
        assert msg["heading"] == 217
        assert msg["second"] == 40
        assert msg["maneuver"] == ManeuverIndicator.NotAvailable
        assert not msg["raim"]

        ensure_type_for_msg_dict(msg)

    def test_msg_type_4_a(self):
        msg = decode(b"!AIVDM,1,1,,A,403OviQuMGCqWrRO9>E6fE700@GO,0*4D").asdict()
        assert msg["lon"] == -76.352362
        assert msg["lat"] == 36.883767
        assert msg["accuracy"] == 1
        assert msg["year"] == 2007
        assert msg["month"] == 5
        assert msg["day"] == 14
        assert msg["minute"] == 57
        assert msg["second"] == 39

        ensure_type_for_msg_dict(msg)

    def test_msg_type_4_b(self):
        msg = decode(b"!AIVDM,1,1,,B,403OtVAv>lba;o?Ia`E`4G?02H6k,0*44").asdict()
        assert round(msg["lon"], 4) == -122.4648
        assert round(msg["lat"], 4) == 37.7943
        assert msg["mmsi"] == 3669145
        assert msg["accuracy"] == 1
        assert msg["year"] == 2019
        assert msg["month"] == 11
        assert msg["day"] == 9
        assert msg["hour"] == 10
        assert msg["minute"] == 41
        assert msg["second"] == 11
        assert msg["epfd"] == 15
        assert msg["epfd"] == EpfdType.Internal_GNSS

        ensure_type_for_msg_dict(msg)

    def test_msg_type_5(self):
        msg = decode(
            "!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C",
            "!AIVDM,2,2,1,A,88888888880,2*25",
        ).asdict()
        assert msg["callsign"] == "3FOF8"
        assert msg["shipname"] == "EVER DIADEM"
        assert msg["ship_type"] == ShipType.Cargo
        assert msg["to_bow"] == 225
        assert msg["to_stern"] == 70
        assert msg["to_port"] == 1
        assert msg["to_starboard"] == 31
        assert msg["draught"] == 12.2
        assert msg["destination"] == "NEW YORK"
        assert msg["dte"] == 0
        assert msg["epfd"] == EpfdType.GPS

        ensure_type_for_msg_dict(msg)

    def test_msg_type_6(self):
        msg = decode(b"!AIVDM,1,1,,B,6B?n;be:cbapalgc;i6?Ow4,2*4A").asdict()
        assert msg["seqno"] == 3
        assert msg["dest_mmsi"] == 313240222
        assert msg["mmsi"] == 150834090
        assert msg["dac"] == 669
        assert msg["fid"] == 11
        assert not msg["retransmit"]
        assert msg["data"] == b"\xeb/\x11\x8f\x7f\xf1"

        ensure_type_for_msg_dict(msg)

    def test_msg_type_7(self):
        msg = decode(b"!AIVDM,1,1,,A,702R5`hwCjq8,0*6B").asdict()
        assert msg["mmsi"] == 2655651
        assert msg["msg_type"] == 7
        assert msg["mmsi1"] == 265538450
        assert msg["mmsiseq1"] == 0
        assert msg["mmsi2"] is None
        assert msg["mmsi3"] is None
        assert msg["mmsi4"] is None

        ensure_type_for_msg_dict(msg)

    def test_msg_type_8(self):
        msg = decode(
            b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47"
        ).asdict()

        assert msg["repeat"] == 0
        assert msg["mmsi"] == 366999712
        assert msg["dac"] == 366
        assert msg["fid"] == 56
        assert msg["data"] == b"\x3a\x53\xdb\xb7\xbe\x4a\x77\x31\x37\xf8\x7d\x7b\x04\x45\xf0\x40\xde\xa0\x5d\x93\xf5\x93\x78\x31\x94\xae\x9b\x9d\x9d\xbe\x05\xfb"

        ensure_type_for_msg_dict(msg)

    def test_msg_type_8_multipart(self):
        msgs = [
            "!AIVDO,2,1,,A,8=?eN>0000:C=4B1KTTsgLoUelGetEo0FoWr8jo=?045TNv5Tge6sAUl4MKWo,0*5F",
            "!AIVDO,2,2,,A,vhOL9NIPln:BsP0=BLOiiCbE7;SKsSJfALeATapHfdm6Tl,2*79",
        ]

        msg = decode(*msgs).asdict()

        assert msg["repeat"] == 0
        assert msg["mmsi"] == 888888888
        assert msg["dac"] == 0
        assert msg["fid"] == 0
        assert msg["data"] == b"\x02\x934D\x81nI;\xbd\xcd\xe5\xb7E\xed\xf1]\xc0[y\xfa#-\xcd<\x01\x05\x91\xef\x85\x92\xfbF\xed\x19t\x11\xd6\xe7\xdf\xec\x1fp\x97\x99\x83M\x8aK\xb8\x005'\x1f\xc7\x14\xeaTr\xe3o\xb8\xda\xb9\x17-FJxb\xeb5\x1aM"

        ensure_type_for_msg_dict(msg)

    def test_msg_type_8_inland(self):
        # example from norwegion public AIS feed
        decoded = decode(b"!BSVDM,1,1,,B,83m;Fa0j2d<<<<<<<0@pUg`50000,0*11")
        msg = decoded.asdict()

        assert msg["repeat"] == 0
        assert msg["mmsi"] == 257087140
        assert msg["dac"] == 200
        assert msg["fid"] == 10
        # inland aIS data should be present
        assert isinstance(decoded, MessageType8Dac200Fid10)
        assert "beam" in msg
        # and correct
        assert msg["beam"] == 7.5

    def test_msg_type_8_inland_2(self):
        decoded = decode("!AIVDO,1,1,,A,85M67F@j2U=7EW=RAkQkBDITMV=e,0*51")
        msg = decoded.asdict()

        assert msg['mmsi'] == 366053209
        assert msg["dac"] == 200
        assert msg["fid"] == 10
        assert msg["length"] == 180.6
        assert msg["beam"] == 42
        assert msg["loaded"] == InlandLoadedType.NotAvailable

    def test_msg_type_9(self):
        msg = decode(b"!AIVDM,1,1,,B,91b55wi;hbOS@OdQAC062Ch2089h,0*30").asdict()
        assert msg["msg_type"] == 9
        assert msg["repeat"] == 0
        assert msg["mmsi"] == 111232511
        assert msg["alt"] == 303
        assert msg["speed"] == 42
        assert msg["accuracy"] == 0
        assert round(msg["lon"], 5) == -6.27884
        assert round(msg["lat"], 5) == 58.144
        assert msg["course"] == 154.5
        assert msg["second"] == 15
        assert msg["dte"] == 1
        assert msg["radio"] == 33392
        assert not msg["raim"]
        assert isinstance(msg["raim"], bool)

        ensure_type_for_msg_dict(msg)

    def test_msg_type_10_a(self):
        msg = decode(b"!AIVDM,1,1,,B,:5MlU41GMK6@,0*6C").asdict()
        assert msg["dest_mmsi"] == 366832740
        assert msg["repeat"] == 0

    def test_msg_type_10_b(self):
        msg = decode(b"!AIVDM,1,1,,B,:6TMCD1GOS60,0*5B").asdict()
        assert msg["dest_mmsi"] == 366972000
        assert msg["repeat"] == 0

    def test_msg_type_11(self):
        msg = decode(b"!AIVDM,1,1,,B,;4R33:1uUK2F`q?mOt@@GoQ00000,0*5D").asdict()
        assert round(msg["lon"], 4) == -94.4077
        assert round(msg["lat"], 4) == 28.4091
        assert msg["accuracy"] == 1
        assert msg["msg_type"] == 11
        assert msg["year"] == 2009
        assert msg["month"] == 5
        assert msg["day"] == 22
        assert msg["hour"] == 2
        assert msg["minute"] == 22
        assert msg["second"] == 40

    def test_msg_type_12_a(self):
        msg = decode(b"!AIVDM,1,1,,A,<5?SIj1;GbD07??4,0*38").asdict()
        assert msg["msg_type"] == 12
        assert msg["repeat"] == 0
        assert msg["mmsi"] == 351853000
        assert msg["seqno"] == 0
        assert msg["dest_mmsi"] == 316123456
        assert msg["retransmit"] == 0
        assert msg["text"] == "GOOD"

    def test_msg_type_12_b(self):
        msg = decode(b"!AIVDM,1,1,,A,<42Lati0W:Ov=C7P6B?=Pjoihhjhqq0,2*2B")
        assert msg.msg_type == 12

        assert msg.repeat == 0
        assert msg.mmsi == 271002099
        assert msg.seqno == 0
        assert msg.dest_mmsi == 271002111
        assert msg.retransmit == 1

        ensure_type_for_msg_dict(msg.asdict())

    def test_msg_type_13(self):
        msg = decode(b"!AIVDM,1,1,,A,=39UOj0jFs9R,0*65").asdict()
        assert msg["msg_type"] == 13
        assert msg["repeat"] == 0
        assert msg["mmsi"] == 211378120
        assert msg["mmsi1"] == 211217560

        ensure_type_for_msg_dict(msg)

    def test_msg_type_14(self):
        msg = decode(b"!AIVDM,1,1,,A,>5?Per18=HB1U:1@E=B0m<L,2*51").asdict()
        assert msg["msg_type"] == 14
        assert msg["repeat"] == 0
        assert msg["mmsi"] == 351809000
        assert msg["text"] == "RCVD YR TEST MSG"

        ensure_type_for_msg_dict(msg)

    def test_msg_type_15_a(self):
        msg = decode(b"!AIVDM,1,1,,A,?5OP=l00052HD00,2*5B").asdict()
        assert msg["msg_type"] == 15
        assert msg["repeat"] == 0
        assert msg["mmsi"] == 368578000
        assert msg["offset1_1"] == 0
        assert msg["mmsi1"] == 5158
        assert msg["offset1_2"] is None
        assert msg["mmsi2"] is None

        ensure_type_for_msg_dict(msg)

    def test_msg_type_15_b(self):
        msg = decode(b"!AIVDM,1,1,,B,?h3Ovn1GP<K0<P@59a0,2*04").asdict()
        assert msg["msg_type"] == 15
        assert msg["repeat"] == 3
        assert msg["mmsi"] == 3669720
        assert msg["mmsi1"] == 367014320
        assert msg["mmsi2"] == 0
        assert msg["type1_1"] == 3
        assert msg["type1_2"] == 5
        assert msg["offset1_2"] == 617
        assert msg["offset1_1"] == 516

        ensure_type_for_msg_dict(msg)

    def test_msg_type_16_short(self):
        msg = decode(b"!AIVDM,1,1,,A,@01uEO@mMk7P<P00,0*18").asdict()

        assert msg["msg_type"] == 16
        assert msg["repeat"] == 0
        assert msg["mmsi"] == 2053501
        assert msg["mmsi1"] == 224251000
        assert msg["offset1"] == 200
        assert msg["increment1"] == 0
        assert 'mmsi2' not in msg
        assert 'offset2' not in msg
        assert 'increment2' not in msg

        ensure_type_for_msg_dict(msg)

    def test_msg_type_16_long(self):
        msg = decode(b"!AIVDO,1,1,,A,@@07Ql@01Qat005h0gN<@00e,0*46").asdict()

        assert msg["msg_type"] == 16
        assert msg["repeat"] == 1
        assert msg["mmsi"] == 123345
        assert msg["mmsi1"] == 99999
        assert msg["offset1"] == 0
        assert msg["increment1"] == 23
        assert msg["mmsi2"] == 777777
        assert msg["offset2"] == 0
        assert msg["increment2"] == 45

        ensure_type_for_msg_dict(msg)

    def test_msg_type_16_types(self):
        short = decode(b"!AIVDM,1,1,,A,@01uEO@mMk7P<P00,0*18")
        long = decode(b"!AIVDO,1,1,,A,@@07Ql@01Qat005h0gN<@00e,0*46")

        # Ensure each message has the expected class
        self.assertIsInstance(short, MessageType16DestinationA)
        self.assertIsInstance(long, MessageType16DestinationAB)

        # Both instances have a MMSI
        self.assertEqual(short.mmsi, 2053501)
        self.assertEqual(long.mmsi, 123345)

        # Both instances have a MMSI1
        self.assertEqual(short.mmsi1, 224251000)
        self.assertEqual(long.mmsi1, 99999)

        # Only the "long" message has a MMSI2
        self.assertFalse(hasattr(short, 'mmsi2'))
        self.assertTrue(hasattr(long, 'mmsi2'))
        self.assertEqual(long.mmsi2, 777777)

    def test_msg_type_17_a(self):
        msg = decode(
            b"!AIVDM,2,1,5,A,A02VqLPA4I6C07h5Ed1h<OrsuBTTwS?r:C?w`?la<gno1RTRwSP9:BcurA8a,0*3A",
            b"!AIVDM,2,2,5,A,:Oko02TSwu8<:Jbb,0*11",
        ).asdict()

        assert msg["msg_type"] == 17
        assert msg["repeat"] == 0
        assert msg["mmsi"] == 2734450
        assert msg["lon"] == 1747.8
        assert msg["lat"] == 3599.2

        data = msg["data"]
        bits = bytes2bits(data).to01()

        assert data == b'|\x05V\xc0p1\xfe\xbb\xf5)$\xfe3\xfa)3\xff\xa0\xfd)2\xfd\xb7\x06)"\xfe8\t)*\xfd\xe9\x12))\xfc\xf7\x00)#\xff\xd2\x0c)\xaa\xaa'
        assert bits == "0111110000000101010101101100000001110000001100011111111010111011111101010010100100100100111111100011001111111010001010010011001111111111101000001111110100101001001100101111110110110111000001100010100100100010111111100011100000001001001010010010101011111101111010010001001000101001001010011111110011110111000000000010100100100011111111111101001000001100001010011010101010101010"

        ensure_type_for_msg_dict(msg)

    def test_msg_type_17_b(self):
        msg = decode(
            b"!AIVDM,1,1,,A,A0476BQ>J8`<h2JpH:4P0?j@2mTEw8`=DP1DEnqvj0,0*79"
        ).asdict()
        assert msg["msg_type"] == 17
        assert msg["repeat"] == 0
        assert msg["mmsi"] == 4310602
        assert msg["lat"] == 2058.2
        assert msg["lon"] == 8029.0

        data = msg["data"]
        bits = bytes2bits(data).to01()

        assert data == b"&\xb8`\xa1 \x00\xfc\x90\x0bY\x15\xfc\x8a\rR\x00TWn~\xc8\x00"
        assert bits == "00100110101110000110000010100001001000000000000011111100100100000000101101011001000101011111110010001010000011010101001000000000010101000101011101101110011111101100100000000000"

        ensure_type_for_msg_dict(msg)

    def test_msg_type_18(self):
        msg = decode(b"!AIVDM,1,1,,A,B5NJ;PP005l4ot5Isbl03wsUkP06,0*76").asdict()
        assert msg["msg_type"] == 18
        assert msg["mmsi"] == 367430530
        assert msg["speed"] == 0.0
        assert msg["accuracy"] == 0
        assert round(msg["lat"], 2) == 37.79
        assert round(msg["lon"], 2) == -122.27
        assert msg["course"] == 0
        assert msg["heading"] == 511
        assert msg["second"] == 55
        assert msg["reserved_2"] == 0
        assert msg["cs"] == 1
        assert msg["display"] == 0
        assert msg["dsc"] == 1
        assert msg["band"] == 1
        assert msg["msg22"] == 1
        assert not msg["assigned"]
        assert not msg["raim"]
        assert isinstance(msg["raim"], bool)

        assert isinstance(msg["lat"], float)
        assert isinstance(msg["lon"], float)
        assert isinstance(msg["speed"], float)
        assert isinstance(msg["course"], float)

        ensure_type_for_msg_dict(msg)

    def test_msg_type_18_speed(self):
        msg = decode(b"!AIVDO,1,1,,A,B5NJ;PP2aUl4ot5Isbl6GwsUkP06,0*35").asdict()

        assert msg["speed"] == 67.8
        assert msg["course"] == 10.1

        ensure_type_for_msg_dict(msg)

    def test_msg_type_19(self):
        msg = decode(
            b"!AIVDM,1,1,,B,C5N3SRgPEnJGEBT>NhWAwwo862PaLELTBJ:V00000000S0D:R220,0*0B"
        ).asdict()
        assert msg["msg_type"] == 19
        assert msg["mmsi"] == 367059850
        assert msg["speed"] == 8.7
        assert msg["accuracy"] == 0
        assert msg["lat"] == 29.543695
        assert msg["lon"], 2 == -88.810394
        assert round(msg["course"], 2) == 335.9
        assert msg["heading"] == 511
        assert msg["second"] == 46
        assert msg["shipname"] == "CAPT.J.RIMES"
        assert msg["ship_type"] == ShipType(70)
        assert msg["ship_type"] == ShipType.Cargo
        assert msg["to_bow"] == 5
        assert msg["to_stern"] == 21
        assert msg["to_port"] == 4
        assert msg["to_starboard"] == 4
        assert msg["epfd"] == EpfdType.GPS
        assert msg["dte"] == 0
        assert msg["assigned"] == 0

        ensure_type_for_msg_dict(msg)

    def test_msg_type_20(self):
        msg = decode(b"!AIVDM,1,1,,A,D028rqP<QNfp000000000000000,2*0C").asdict(ignore_spare=False)
        assert msg["msg_type"] == 20
        assert msg["mmsi"] == 2243302
        assert msg["offset1"] == 200
        assert msg["number1"] == 5
        assert msg["timeout1"] == 7
        assert msg["increment1"] == 750
        assert msg["spare_1"] == b"\x00"

        # All other values are zero
        for k, v in msg.items():
            if k not in (
                "msg_type",
                "mmsi",
                "offset1",
                "number1",
                "timeout1",
                "increment1",
                "spare_1",
            ):
                assert not v

        ensure_type_for_msg_dict(msg)

    def test_msg_type_21(self):
        msg = decode(
            b"!AIVDM,2,1,7,B,E4eHJhPR37q0000000000000000KUOSc=rq4h00000a,0*4A",
            b"!AIVDM,2,2,7,B,@20,4*54",
        ).asdict()
        assert msg["msg_type"] == 21
        assert msg["mmsi"] == 316021442
        assert msg["aid_type"] == NavAid.REFERENCE_POINT
        assert msg["name"] == "DFO2"
        assert msg["accuracy"] == 1
        assert msg["lat"] == 48.65457
        assert msg["lon"] == -123.429155
        assert not msg["to_bow"]
        assert not msg["to_stern"]
        assert not msg["to_port"]
        assert not msg["to_starboard"]

        assert msg["off_position"]
        assert msg["reserved_1"] == 0
        assert msg["raim"]
        assert msg["virtual_aid"] == 0
        assert msg["assigned"] == 0
        assert msg["name_ext"] is None
        assert msg["epfd"] == EpfdType.GPS

        ensure_type_for_msg_dict(msg)

    def test_msg_type_22_broadcast(self):
        # Broadcast
        msg = decode(b"!AIVDM,1,1,,B,F030p:j2N2P5aJR0r;6f3rj10000,0*11").asdict()
        assert msg["msg_type"] == 22
        assert msg["mmsi"] == 3160107
        assert msg["channel_a"] == 2087
        assert msg["channel_b"] == 2088
        assert msg["power"] == 0

        assert msg["ne_lon"] == -7710.0
        assert msg["ne_lat"] == 3300.0
        assert msg["sw_lon"] == -8020.0
        assert msg["sw_lat"] == 3210.0

        assert msg["band_a"] == 0
        assert msg["band_b"] == 0
        assert msg["zonesize"] == 2

        assert "dest1" not in msg.keys()
        assert "dest2" not in msg.keys()

        assert isinstance(msg["ne_lon"], float)
        assert isinstance(msg["ne_lat"], float)
        assert isinstance(msg["sw_lon"], float)
        assert isinstance(msg["sw_lat"], float)

        ensure_type_for_msg_dict(msg)

    def test_msg_type_22_addressed(self):
        # Addressed
        msg = decode(b"!AIVDM,1,1,,A,F@@W>gOP00PH=JrN9l000?wB2HH;,0*44").asdict()
        assert msg["msg_type"] == 22
        assert msg["mmsi"] == 17419965
        assert msg["channel_a"] == 3584
        assert msg["channel_b"] == 8
        assert msg["power"] == 1
        assert msg["addressed"] == 1

        assert msg["dest1"] == 28144881
        assert msg["dest2"] == 268435519

        assert msg["band_a"] == 0
        assert msg["band_b"] == 0
        assert msg["zonesize"] == 4

        assert "ne_lon" not in msg.keys()
        assert "ne_lat" not in msg.keys()
        assert "sw_lon" not in msg.keys()
        assert "sw_lat" not in msg.keys()

        ensure_type_for_msg_dict(msg)

    def test_msg_type_23(self):
        msg = decode(b"!AIVDM,1,1,,B,G02:Kn01R`sn@291nj600000900,2*12").asdict()
        assert msg["msg_type"] == 23
        assert msg["mmsi"] == 2268120
        assert msg["ne_lon"] == 157.8
        assert msg["ship_type"] == ShipType.NotAvailable
        assert msg["ne_lat"] == 3064.2
        assert msg["sw_lon"] == 109.6
        assert msg["sw_lat"] == 3040.8
        assert msg["station_type"] == StationType.REGIONAL
        assert msg["txrx"] == TransmitMode.TXA_TXB_RXA_RXB
        assert msg["interval"] == 9
        assert msg["quiet"] == 0

        ensure_type_for_msg_dict(msg)

    def test_msg_type_24(self):
        msg = decode(b"!AIVDM,1,1,,A,H52KMeDU653hhhi0000000000000,0*1A").asdict()
        assert msg["msg_type"] == 24
        assert msg["mmsi"] == 338091445
        assert msg["partno"] == 1
        assert msg["ship_type"] == ShipType.PleasureCraft
        assert msg["vendorid"] == "FEC"
        assert msg["callsign"] == ""
        assert msg["to_bow"] == 0
        assert msg["to_stern"] == 0
        assert msg["to_port"] == 0
        assert msg["to_starboard"] == 0

        ensure_type_for_msg_dict(msg)

    def test_msg_type_24_with_160_bits(self):
        msg = decode(b"!AIVDO,1,1,,A,H1mg=5@EP4m0hF1<PU000000000,2*77").asdict(ignore_spare=False)
        assert msg["msg_type"] == 24
        assert msg["partno"] == 0
        assert msg["mmsi"] == 123456789
        assert msg["spare_1"] is None

    def test_msg_type_24_with_168_bits(self):
        msg = decode(b"!AIVDO,1,1,,A,H1mg=5@EP4m0hF1<PU0000000000,0*45").asdict(ignore_spare=False)
        assert msg["msg_type"] == 24
        assert msg["partno"] == 0
        assert msg["mmsi"] == 123456789
        assert msg["spare_1"] == b"\x00"

    def test_msg_type_25_a(self):
        msg = decode(b"!AIVDM,1,1,,A,I6SWo?8P00a3PKpEKEVj0?vNP<65,0*73").asdict(ignore_spare=False)

        assert msg["msg_type"] == 25
        assert msg["addressed"]
        assert not msg["structured"]
        assert msg["dest_mmsi"] == 134218384

        ensure_type_for_msg_dict(msg)

    def test_msg_type_25_b(self):
        msg = decode(b"!AIVDO,1,1,,A,I6SWo?<P00a00;Cwwwwwwwwwwww0,0*4A").asdict()
        assert msg == {
            "addressed": 1,
            "data": b"?\xff\xff\xff\xff\xff\xff\xff\xff\xf0\x00",
            "dest_mmsi": 134218384,
            "mmsi": 440006460,
            "repeat": 0,
            "structured": 1,
            "app_id": 45,
            "msg_type": 25,
        }

        ensure_type_for_msg_dict(msg)

    def test_msg_type_25_c(self):
        msg = decode(b"!AIVDO,1,1,,A,I6SWo?8P00a0003wwwwwwwwwwww0,0*35").asdict()
        assert msg == {
            "addressed": 1,
            "data": b"\x00\x00?\xff\xff\xff\xff\xff\xff\xff\xff\xf0\x00",
            "dest_mmsi": 134218384,
            "mmsi": 440006460,
            "repeat": 0,
            "structured": 0,
            "msg_type": 25,
        }

        ensure_type_for_msg_dict(msg)

    def test_msg_type_26_a(self):
        msg = decode(
            b"!AIVDM,1,1,,A,JB3R0GO7p>vQL8tjw0b5hqpd0706kh9d3lR2vbl0400,2*40"
        ).asdict()
        assert msg["msg_type"] == 26
        assert msg["addressed"]
        assert msg["structured"]
        assert msg["dest_mmsi"] == 838351848
        assert msg["data"] == b"\xcc\xbf\x02\xa1p\xe7\x8b\x00\x1c\x01\xb3\xc0\x9b\x03\xd2 \xbe\xab@\x04\x00\x00"

        ensure_type_for_msg_dict(msg)

    def test_msg_type_26_b(self):
        msg = decode(b"!AIVDM,1,1,,A,J0@00@370>t0Lh3P0000200H:2rN92,4*14").asdict()
        assert msg["msg_type"] == 26
        assert not msg["addressed"]
        assert not msg["structured"]
        assert (
            int.from_bytes(msg["data"], "big") == 0xC700EF007300E0000000080018282E9E24
        )

        ensure_type_for_msg_dict(msg)

    def test_msg_type_27(self):
        msg = decode(b"!AIVDM,1,1,,B,KC5E2b@U19PFdLbMuc5=ROv62<7m,0*16").asdict()
        assert msg["msg_type"] == 27
        assert msg["mmsi"] == 206914217
        assert msg["accuracy"] == 0
        assert msg["raim"] == 0
        assert msg["status"] == NavigationStatus.NotUnderCommand
        assert msg["lon"] == 137.023333
        assert msg["lat"] == 4.84
        assert msg["speed"] == 57
        assert msg["course"] == 167
        assert msg["gnss"] == 0

        ensure_type_for_msg_dict(msg)

    def test_msg_type_27_signed(self):
        msg = decode("!AIVDO,1,1,,A,K01;FQh?PbtE3P00,0*75").asdict()
        assert msg["mmsi"] == 1234567
        assert msg["lon"] == -13.368333
        assert msg["lat"] == -50.121667

    def test_broken_messages(self):
        # Undefined epfd
        assert decode(b"!AIVDM,1,1,,B,4>O7m7Iu@<9qUfbtm`vSnwvH20S8,0*46").asdict()["epfd"] == EpfdType.Undefined

    def test_multiline_message(self):
        # these messages caused issue #3
        msg_1_part_0 = b"!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07"
        msg_1_part_1 = b"!AIVDM,2,2,1,A,F@V@00000000000,2*35"

        assert decode(msg_1_part_0, msg_1_part_1).to_json()

        msg_2_part_0 = b"!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F"
        msg_2_part_1 = b"!AIVDM,2,2,9,A,F@V@00000000000,2*3D"

        assert decode(msg_2_part_0, msg_2_part_1).to_json()

    def test_byte_stream(self):
        messages = [
            b"!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07",
            b"!AIVDM,2,2,1,A,F@V@00000000000,2*35",
            b"!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F",
            b"!AIVDM,2,2,9,A,F@V@00000000000,2*3D",
        ]
        counter = 0
        for msg in ByteStream(messages):
            decoded = msg.decode().asdict()
            assert decoded["shipname"] == "NORDIC HAMBURG"
            assert decoded["mmsi"] == 210035000
            assert decoded
            counter += 1
        assert counter == 2

    def test_empty_channel(self):
        msg = b"!AIVDO,1,1,,,B>qc:003wk?8mP=18D3Q3wgTiT;T,0*13"

        self.assertEqual(NMEAMessage(msg).channel, "")

        content = decode(msg).asdict()
        self.assertEqual(content["msg_type"], 18)
        self.assertEqual(content["repeat"], 0)
        self.assertEqual(content["mmsi"], 1000000000)
        self.assertEqual(content["speed"], 102.3)
        self.assertEqual(content["accuracy"], 0)
        self.assertEqual(str(content["lon"]), "181.0")
        self.assertEqual(str(content["lat"]), "91.0")
        self.assertEqual(str(content["course"]), "360.0")
        self.assertEqual(content["heading"], 511)
        self.assertEqual(content["second"], 31)
        self.assertEqual(content["reserved_2"], 0)
        self.assertEqual(content["cs"], 1)
        self.assertEqual(content["display"], 0)
        self.assertEqual(content["band"], 1)
        self.assertEqual(content["radio"], 410340)

    def test_msg_with_more_that_82_chars_payload(self):
        content = decode(
            "!AIVDM,1,1,,B,53ktrJ82>ia4=50<0020<5=@Dhv0t8T@u<0000001PV854Si0;mR@CPH13p0hDm1C3h0000,2*35"
        ).asdict()

        self.assertEqual(content["msg_type"], 5)
        self.assertEqual(content["mmsi"], 255801960)
        self.assertEqual(content["repeat"], 0)
        self.assertEqual(content["ais_version"], 2)
        self.assertEqual(content["imo"], 9356945)
        self.assertEqual(content["callsign"], "CQPC")
        self.assertEqual(content["shipname"], "CASTELO OBIDOS")
        self.assertEqual(content["ship_type"], ShipType.NotAvailable)
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

    def test_nmea_decode(self):
        nmea = NMEAMessage(b"!AIVDO,1,1,,,B>qc:003wk?8mP=18D3Q3wgTiT;T,0*13")
        decoded = nmea.decode()
        assert decoded.msg_type == 18
        assert isinstance(decoded, MessageType18)

    def test_nmea_decode_unknown_msg(self):
        with self.assertRaises(UnknownMessageException):
            nmea = NMEAMessage(b"!AIVDO,1,1,,,B>qc:003wk?8mP=18D3Q3wgTiT;T,0*13")
            nmea.ais_id = 28
            nmea.decode()

    def test_decode_out_of_order(self):
        parts = [
            b"!AIVDM,2,2,4,A,000000000000000,2*20",
            b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08",
        ]

        decoded = decode(*parts)

        assert decoded.asdict()["mmsi"] == 368060190

    def test_issue_46_a(self):
        msg = b"!ARVDM,2,1,3,B,E>m1c1>9TV`9WW@97QUP0000000F@lEpmdceP00003b,0*5C"
        decoded = NMEAMessage(msg).decode()

        self.assertEqual(decoded.msg_type, 21)
        self.assertEqual(decoded.repeat, 0)
        self.assertEqual(decoded.mmsi, 995126020)
        self.assertEqual(decoded.aid_type, NavAid.ISOLATED_DANGER)
        self.assertEqual(decoded.name, "SIMPSON ROCK")
        self.assertEqual(decoded.accuracy, True)
        self.assertEqual(decoded.lon, 175.119987)
        self.assertEqual(decoded.lat, -36.0075)
        self.assertEqual(decoded.to_bow, 0)
        self.assertEqual(decoded.to_stern, 0)
        self.assertEqual(decoded.to_port, 0)
        self.assertEqual(decoded.to_starboard, 0)
        self.assertEqual(decoded.epfd, EpfdType.Surveyed)
        self.assertEqual(decoded.second, 10)

        # The following fields are None
        self.assertIsNone(decoded.off_position)
        self.assertIsNone(decoded.reserved_1)
        self.assertIsNone(decoded.raim)
        self.assertIsNone(decoded.virtual_aid)
        self.assertIsNone(decoded.assigned)
        self.assertIsNone(decoded.name_ext)

    def test_issue_46_b(self):
        msg = b"!AIVDM,1,1,,B,E>lt;KLab21@1bb@I@@@@@@@@@@D8k2tnmvs000003v0@,2*52"
        decoded = NMEAMessage(msg).decode()

        self.assertEqual(decoded.msg_type, 21)
        self.assertEqual(decoded.repeat, 0)
        self.assertEqual(decoded.mmsi, 995036013)
        self.assertEqual(decoded.aid_type, NavAid.STARBOARD_HAND_MARK)
        self.assertEqual(decoded.name, "STDB CUT 2")
        self.assertEqual(decoded.accuracy, True)
        self.assertEqual(decoded.lon, 115.691833)
        self.assertEqual(decoded.lat, -32.004333)
        self.assertEqual(decoded.to_bow, 0)
        self.assertEqual(decoded.to_stern, 0)
        self.assertEqual(decoded.to_port, 0)
        self.assertEqual(decoded.to_starboard, 0)
        self.assertEqual(decoded.epfd, EpfdType.Surveyed)
        self.assertEqual(decoded.second, 60)
        self.assertEqual(decoded.off_position, False)
        self.assertEqual(decoded.reserved_1, 4)

        # The following fields are None
        self.assertIsNone(decoded.raim)
        self.assertIsNone(decoded.virtual_aid)
        self.assertIsNone(decoded.assigned)
        self.assertIsNone(decoded.name_ext)

    def test_msg_too_short_enum_is_none(self):
        msg = b"!AIVDM,1,1,,B,E>lt;,2*52"
        decoded = NMEAMessage(msg).decode()

        self.assertEqual(decoded.msg_type, 21)
        self.assertEqual(decoded.repeat, 0)
        self.assertEqual(decoded.mmsi, 971714)
        self.assertIsNone(decoded.aid_type)
        self.assertIsNone(decoded.epfd)

        msg = b"!AIVDM,1,1,,B,15M6,0*5C"
        decoded = NMEAMessage(msg).decode()
        self.assertIsNone(decoded.maneuver)

        msg = b"!AIVDM,2,1,1,A,55?MbV02;H,0*00"
        decoded = NMEAMessage(msg).decode()
        self.assertIsNone(decoded.ship_type)
        self.assertIsNone(decoded.epfd)

    def test_to_dict_non_enum(self):
        """Enum types do not use None if the fields are missing when partial decoding"""
        msg = b"!AIVDM,1,1,,B,E>lt;KLab21@1bb@I@@@@@@@@@@D8k2tnmvs000003v0@,2*52"
        decoded = NMEAMessage(msg).decode()

        d = decoded.asdict(enum_as_int=True)
        self.assertEqual(
            d,
            {
                "accuracy": True,
                "aid_type": 25,
                "assigned": None,
                "epfd": 7,
                'full_name': 'STDB CUT 2',
                "lat": -32.004333,
                "lon": 115.691833,
                "mmsi": 995036013,
                "msg_type": 21,
                "name_ext": None,
                "off_position": False,
                "raim": None,
                "reserved_1": 4,
                "repeat": 0,
                "second": 60,
                "name": "STDB CUT 2",
                "to_bow": 0,
                "to_port": 0,
                "to_starboard": 0,
                "to_stern": 0,
                "virtual_aid": None,
            },
        )

    def test_decode_and_merge(self):
        msg = b"!AIVDM,1,1,,B,E>lt;KLab21@1bb@I@@@@@@@@@@D8k2tnmvs000003v0@,2*52"
        decoded = NMEAMessage(msg)

        d = decoded.decode_and_merge(enum_as_int=True)
        self.assertEqual(
            d,
            {
                "accuracy": True,
                "aid_type": 25,
                "ais_id": 21,
                "assigned": None,
                "channel": "B",
                "is_valid": True,
                "checksum": 82,
                "epfd": 7,
                "fill_bits": 2,
                "frag_cnt": 1,
                "frag_num": 1,
                'full_name': 'STDB CUT 2',
                "lat": -32.004333,
                "lon": 115.691833,
                "mmsi": 995036013,
                "msg_type": 21,
                "name_ext": None,
                "off_position": False,
                "payload": "E>lt;KLab21@1bb@I@@@@@@@@@@D8k2tnmvs000003v0@",
                "raim": None,
                "raw": "!AIVDM,1,1,,B,E>lt;KLab21@1bb@I@@@@@@@@@@D8k2tnmvs000003v0@,2*52",
                "reserved_1": 4,
                "repeat": 0,
                "second": 60,
                "seq_id": None,
                "name": "STDB CUT 2",
                "talker": "AI",
                "to_bow": 0,
                "to_port": 0,
                "to_starboard": 0,
                "to_stern": 0,
                "type": "VDM",
                "virtual_aid": None,
            },
        )

        d = decoded.decode_and_merge(enum_as_int=False)
        self.assertEqual(
            d,
            {
                "accuracy": True,
                "aid_type": NavAid.STARBOARD_HAND_MARK,
                "ais_id": 21,
                "assigned": None,
                "channel": "B",
                "checksum": 82,
                "is_valid": True,
                "epfd": EpfdType.Surveyed,
                "fill_bits": 2,
                "frag_cnt": 1,
                "frag_num": 1,
                'full_name': 'STDB CUT 2',
                "lat": -32.004333,
                "lon": 115.691833,
                "mmsi": 995036013,
                "msg_type": 21,
                "name_ext": None,
                "off_position": False,
                "payload": "E>lt;KLab21@1bb@I@@@@@@@@@@D8k2tnmvs000003v0@",
                "raim": None,
                "raw": "!AIVDM,1,1,,B,E>lt;KLab21@1bb@I@@@@@@@@@@D8k2tnmvs000003v0@,2*52",
                "reserved_1": 4,
                "repeat": 0,
                "second": 60,
                "seq_id": None,
                "name": "STDB CUT 2",
                "talker": "AI",
                "to_bow": 0,
                "to_port": 0,
                "to_starboard": 0,
                "to_stern": 0,
                "type": "VDM",
                "virtual_aid": None,
            },
        )

    def test_issue_50(self):
        """Refer to PR: https://github.com/M0r13n/pyais/pull/50/files"""
        msg = MessageType5.create(mmsi="123456", ship_type=None, epfd=None)

        dictionary = msg.asdict(enum_as_int=True)

        self.assertIsNone(dictionary["epfd"])
        self.assertIsNone(dictionary["ship_type"])

    def test_none_value_converter_for_creation(self):
        """Make sure that None values can be encoded -> left out"""
        msg = MessageType6.create(mmsi="123456", dest_mmsi=None, data=None)
        self.assertIsNone(msg.data)

    def test_none_value_converter_for_decoding(self):
        """Make sure that None values do not cause any problems when decoding"""
        encoded = encode_dict(
            {"mmsi": "123456", "dest_mmsi": None, "data": None, "msg_type": 6}
        )
        encoded = encoded[0]
        decoded = decode(encoded)
        self.assertIsNone(decoded.data)

    def test_none_values_converter_for_all_messages(self):
        """
        Create the shortest possible message that could potentially occur and try to decode it again.
        This is done to ensure, that there are no hiccups when trying to decode very short messages.
        """
        for mtype in range(28):
            cls = MSG_CLASS[mtype]
            fields = set(f.name for f in cls.fields())
            payload = {f: None for f in fields}
            payload["mmsi"] = 1337
            payload["msg_type"] = mtype
            encoded = encode_dict(payload)

            self.assertIsNotNone(encoded)

            decoded = decode(*encoded)

            for field in fields:
                val = getattr(decoded, field)
                if field == "mmsi":
                    self.assertEqual(val, 1337)
                elif field == "msg_type":
                    self.assertEqual(val, mtype)
                elif field == "repeat":
                    self.assertEqual(val, 0)
                else:
                    self.assertIsNone(val)

    def test_type_25_very_short(self):
        """If the message is very short, an IndexError might o occur"""
        short_msg = b"!AIVDO,1,1,,A,Ig,0*65"
        decoded = decode(short_msg)

        self.assertEqual(decoded.mmsi, 15)

    def test_type_26_very_short(self):
        """If the message is very short, an IndexError might occur"""
        short_msg = b"!AIVDO,1,1,,A,Jgg,4*4E"
        decoded = decode(short_msg)

        self.assertEqual(decoded.mmsi, 62)

    def test_type_22_very_short(self):
        """If the mssage is very short an IndexError might occur"""
        short_msg = b"!AIVDO,1,1,,A,F0001,0*74"
        decoded = decode(short_msg)

        self.assertEqual(decoded.mmsi, 1)

    def test_types_for_messages(self):
        """Make sure that the types are consistent for all messages"""
        types = {}
        for typ, msg in itertools.chain(
            MSG_CLASS.items(),
            [
                (22, MessageType22Addressed),
                (22, MessageType22Broadcast),
                (24, MessageType24PartA),
                (24, MessageType24PartB),
                (25, MessageType25AddressedStructured),
                (25, MessageType25BroadcastStructured),
                (25, MessageType25AddressedUnstructured),
                (25, MessageType25BroadcastUnstructured),
                (26, MessageType26AddressedStructured),
                (26, MessageType26AddressedStructured),
                (26, MessageType26BroadcastStructured),
                (26, MessageType26BroadcastUnstructured),
            ],
        ):
            # Make sure that the same fields have the same datatype for all classes
            # E.g. lat is of type float for all messages
            for field in msg.fields():
                d_type = field.metadata["d_type"]
                f_name = field.name
                if f_name in types:
                    assert (
                        d_type == types[f_name]
                    ), f"{typ}.{f_name}: {d_type} vs. {types[f_name]}"
                else:
                    types[f_name] = d_type

    def test_bits2bytes(self):
        self.assertEqual(bits2bytes("00100110"), b"&")
        self.assertEqual(bits2bytes(""), b"")
        self.assertEqual(bits2bytes("0010011000100110"), b"&&")
        self.assertEqual(bits2bytes("11111111"), b"\xff")
        self.assertEqual(bits2bytes("111100001111"), b"\xf0\xf0")
        self.assertEqual(bits2bytes("1111000011110000"), b"\xf0\xf0")
        self.assertEqual(bits2bytes("1"), b"\x80")
        self.assertEqual(bits2bytes("10000000"), b"\x80")
        self.assertEqual(bits2bytes("0" * 64), b"\x00\x00\x00\x00\x00\x00\x00\x00")
        self.assertEqual(bits2bytes("1" * 64), b"\xff\xff\xff\xff\xff\xff\xff\xff")
        self.assertEqual(bits2bytes("10" * 32), b"\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa")

    def test_bytes2bits(self):
        self.assertEqual(bytes2bits(b"&").to01(), "00100110")
        self.assertEqual(bytes2bits(b"").to01(), "")
        self.assertEqual(bytes2bits(b"&&").to01(), "0010011000100110")
        self.assertEqual(bytes2bits(b"\xff").to01(), "11111111")
        self.assertEqual(
            bytes2bits(b"\x00\x00\x00\x00\x00\x00\x00\x00").to01(), "0" * 64
        )
        self.assertEqual(
            bytes2bits(b"\xff\xff\xff\xff\xff\xff\xff\xff").to01(), "1" * 64
        )
        self.assertEqual(
            bytes2bits(b"\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa").to01(), "10" * 32
        )

    def test_b64encode_str(self):
        in_val = b"\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa"
        cipher = b64encode_str(in_val)
        plain = base64.b64decode(cipher)

        self.assertEqual(in_val, plain)

    def test_b64encode_str_empty(self):
        in_val = int(0).to_bytes(1, "big")
        assert in_val == b"\x00"

        cipher = b64encode_str(in_val)
        plain = base64.b64decode(cipher)

        self.assertEqual(in_val, plain)
        self.assertEqual(cipher, "AA==")

    def test_msg_type_6_to_json(self):
        json_str = decode(b"!AIVDM,1,1,,B,6B?n;be:cbapalgc;i6?Ow4,2*4A").to_json()
        self.assertEqual(
            json_str,
            textwrap.dedent(
                """
        {
            "msg_type": 6,
            "repeat": 1,
            "mmsi": 150834090,
            "seqno": 3,
            "dest_mmsi": 313240222,
            "retransmit": false,
            "dac": 669,
            "fid": 11,
            "data": "6y8Rj3/x"
        }
        """
            ).strip(),
        )

    def test_msg_type_8_to_json(self):
        json_str = decode(
            b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47"
        ).to_json()
        self.assertEqual(
            json_str,
            textwrap.dedent(
                """
        {
            "msg_type": 8,
            "repeat": 0,
            "mmsi": 366999712,
            "dac": 366,
            "fid": 56,
            "data": "OlPbt75KdzE3+H17BEXwQN6gXZP1k3gxlK6bnZ2+Bfs="
        }
        """
            ).strip(),
        )

    def test_msg_type_17_to_json(self):
        json_str = decode(
            b"!AIVDM,2,1,5,A,A02VqLPA4I6C07h5Ed1h<OrsuBTTwS?r:C?w`?la<gno1RTRwSP9:BcurA8a,0*3A",
            b"!AIVDM,2,2,5,A,:Oko02TSwu8<:Jbb,0*11",
        ).to_json()
        self.assertEqual(
            json_str,
            textwrap.dedent(
                """
        {
            "msg_type": 17,
            "repeat": 0,
            "mmsi": 2734450,
            "lon": 1747.8,
            "lat": 3599.2,
            "data": "fAVWwHAx/rv1KST+M/opM/+g/Sky/bcGKSL+OAkpKv3pEikp/PcAKSP/0gwpqqo="
        }
        """
            ).strip(),
        )

    def test_msg_type_25_to_json(self):
        json_str = decode(b"!AIVDM,1,1,,A,I6SWo?8P00a3PKpEKEVj0?vNP<65,0*73").to_json()
        self.assertEqual(
            json_str,
            textwrap.dedent(
                """
        {
            "msg_type": 25,
            "repeat": 0,
            "mmsi": 440006460,
            "addressed": true,
            "structured": false,
            "dest_mmsi": 134218384,
            "data": "4G+FW1ZsgD/noDBhQA=="
        }
        """
            ).strip(),
        )

    def test_msg_type_26_to_json(self):
        json_str = decode(
            b"!AIVDM,1,1,,A,JB3R0GO7p>vQL8tjw0b5hqpd0706kh9d3lR2vbl0400,2*40"
        ).to_json()
        self.assertEqual(
            json_str,
            textwrap.dedent(
                """
        {
            "msg_type": 26,
            "repeat": 1,
            "mmsi": 137920605,
            "addressed": true,
            "structured": true,
            "dest_mmsi": 838351848,
            "app_id": 23587,
            "data": "zL8CoXDniwAcAbPAmwPSIL6rQAQAAA==",
            "radio": null
        }
        """
            ).strip(),
        )

    def test_msg_type_6_json_reverse(self):
        string = textwrap.dedent(
            """
        {
            "msg_type": 6,
            "repeat": 1,
            "mmsi": "150834090",
            "seqno": 3,
            "dest_mmsi": "313240222",
            "retransmit": false,
            "dac": 669,
            "fid": 11,
            "data": "6y8Rj3/x"
        }
        """
        )

        data = json.loads(string)

        assert data["data"] == "6y8Rj3/x"
        assert base64.b64decode(data["data"]) == b"\xeb/\x11\x8f\x7f\xf1"

    def test_rot_encode_yields_expected_values(self):
        encoded = encode_dict({"msg_type": 1, "mmsi": 123, "turn": 25.0})[0]
        assert encoded == "!AIVDO,1,1,,A,10000Nw60000000000000001P000,0*7B"

        encoded = encode_dict({"msg_type": 1, "mmsi": 123, "turn": -16.0})[0]
        assert encoded == "!AIVDO,1,1,,A,10000Nws@000000000000001P000,0*4E"

        encoded = encode_dict({"msg_type": 1, "mmsi": 123, "turn": 4.0})[0]
        assert encoded == "!AIVDO,1,1,,A,10000Nw2@000000000000001P000,0*0F"

        encoded = encode_dict({"msg_type": 1, "mmsi": 123, "turn": -4.0})[0]
        assert encoded == "!AIVDO,1,1,,A,10000Nwuh000000000000001P000,0*60"

        encoded = encode_dict({"msg_type": 1, "mmsi": 123, "turn": -121.0})[0]
        assert encoded == "!AIVDO,1,1,,A,10000Nwk0000000000000001P000,0*26"

        encoded = encode_dict({"msg_type": 1, "mmsi": 123, "turn": 64.0})[0]
        assert encoded == "!AIVDO,1,1,,A,10000Nw9P000000000000001P000,0*14"

    def test_rot_encode_decode(self):
        encoded = encode_dict({"msg_type": 1, "mmsi": 123, "turn": 2.0})[0]
        assert decode(encoded).turn == 2.0

        encoded = encode_dict({"msg_type": 1, "mmsi": 123, "turn": 3.0})[0]
        assert decode(encoded).turn == 3.0

        encoded = encode_dict({"msg_type": 1, "mmsi": 123, "turn": 4.0})[0]
        assert decode(encoded).turn == 4.0

        encoded = encode_dict({"msg_type": 1, "mmsi": 123, "turn": 5.0})[0]
        assert decode(encoded).turn == 5.0

    def test_rot_decode_yields_expected_values(self):
        assert decode(b"!AIVDM,1,1,,A,14QIG<5620KF@Gl:L9DI4o8N0P00,0*28").turn == 26.0
        assert decode(b"!AIVDM,1,1,,B,13u><=gsQj0mQW:Q1<wRL28P0@:4,0*32").turn == -14.0
        assert decode(b"!AIVDM,1,1,,A,14SSRt021O0?bK@MO7H6QUA600Rg,0*12").turn == 3.0
        assert decode(b"!AIVDM,1,1,,2,13aB:Hhuh0PHjEFNKJg@11sH08J=,0*1E").turn == -4.0
        assert decode(b"!AIVDM,1,1,,A,16:VFv0k0I`KQPpFATG4SgvT40:v,0*7B").turn == -121.0
        assert decode(b"!AIVDM,1,1,,B,16:D3F0:15`5ogh<O?bk>1Dd2L1<,0*0B").turn == 71.0

    def test_sotdma_time_conversion(self):
        """Prevent regressions for: https://github.com/M0r13n/pyais/pull/135"""
        decoded = decode('!AIVDM,1,1,,B,133ga6PP0lPPE>4M3G@DpOwTR61p,0*33')
        cs = decoded.get_communication_state()

        assert cs['utc_hour'] == 16
        assert cs['utc_minute'] == 30

    def test_get_sotdma_comm_state_utc_direct(self):
        msg = "!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23"
        decoded = decode(msg)
        actual = decoded.get_communication_state()

        assert decoded.is_sotdma
        assert not decoded.is_itdma

        self.assertEqual(
            actual,
            {
                "received_stations": None,
                "slot_number": None,
                "utc_hour": 11,
                "utc_minute": 30,
                "slot_offset": None,
                "slot_timeout": 1,
                "sync_state": SyncState.UTC_DIRECT,
                "keep_flag": None,
                "slot_increment": None,
                "num_slots": None,
            },
        )

    def test_get_sotdma_comm_state_utc_direct_slot_number(self):
        msg = "!AIVDM,1,1,,B,403OtVAv>lba;o?Ia`E`4G?02H6k,0*44"
        decoded = decode(msg)
        actual = decoded.get_communication_state()

        assert decoded.is_sotdma
        assert not decoded.is_itdma

        self.assertEqual(
            actual,
            {
                "received_stations": None,
                "slot_number": 435,
                "utc_hour": None,
                "utc_minute": None,
                "slot_offset": None,
                "slot_timeout": 6,
                "sync_state": SyncState.UTC_DIRECT,
                "keep_flag": None,
                "slot_increment": None,
                "num_slots": None,
            },
        )

    def test_get_sotdma_comm_state_utc_direct_slot_timeout(self):
        msg = "!AIVDM,1,1,,B,91b55wi;hbOS@OdQAC062Ch2089h,0*30"
        decoded = decode(msg)
        actual = decoded.get_communication_state()

        assert decoded.is_sotdma
        assert not decoded.is_itdma

        self.assertEqual(
            actual,
            {
                "received_stations": None,
                "slot_number": 624,
                "utc_hour": None,
                "utc_minute": None,
                "slot_offset": None,
                "slot_timeout": 2,
                "sync_state": SyncState.UTC_DIRECT,
                "keep_flag": None,
                "slot_increment": None,
                "num_slots": None,
            },
        )

    def test_is_sotdma_or_itdma(self):
        """ Verify that messages are correctly identified as either ITDMA or SOTDMA.
        Details: https://github.com/M0r13n/pyais/issues/136."""

        # 1
        assert decode(b"!AIVDM,1,1,,A,13n3aW0PCkPJS8>Qhc2<urG02D13,0*18").is_sotdma
        assert not decode(b"!AIVDM,1,1,,A,13n3aW0PCkPJS8>Qhc2<urG02D13,0*18").is_itdma
        # 2
        assert decode(b"!AIVDM,1,1,,A,23aFfl0P00PCR?0MEB@h0?w020S7,0*68").is_sotdma
        assert not decode(b"!AIVDM,1,1,,A,23aFfl0P00PCR?0MEB@h0?w020S7,0*68").is_itdma
        # 3
        assert not decode(b"!AIVDM,1,1,,B,33UTPD5000G<@aTL3:?0010j0000,0*2A").is_sotdma
        assert decode(b"!AIVDM,1,1,,B,33UTPD5000G<@aTL3:?0010j0000,0*2A").is_itdma
        # 4
        assert decode(b"!AIVDM,1,1,,B,4h2=aCAuho;QNOUQrvQ6?a1000S:,0*5D").is_sotdma
        assert not decode(b"!AIVDM,1,1,,B,4h2=aCAuho;QNOUQrvQ6?a1000S:,0*5D").is_itdma
        # 9
        assert decode(b"!AIVDM,1,1,,A,91b55vRCQvOo4PLLww<3cGh20@Br,0*79").is_sotdma
        assert not decode(b"!AIVDM,1,1,,A,91b55vRCQvOo4PLLww<3cGh20@Br,0*79").is_itdma
        # 11
        assert decode(b"!AIVDM,1,1,,A,;03t=KQuho;QM`d:WFAtwnW00000,0*7C").is_sotdma
        assert not decode(b"!AIVDM,1,1,,A,;03t=KQuho;QM`d:WFAtwnW00000,0*7C").is_itdma
        # 18
        assert decode(b" !AIVDM,1,1,,A,B6:a?;03wk?8mP=18D3Q3wP61P06,0*7F").is_sotdma
        assert not decode(b" !AIVDM,1,1,,A,B6:a?;03wk?8mP=18D3Q3wP61P06,0*7F").is_itdma

    def test_get_comm_state_type_18_itdma_base_indirect(self):
        msg = "!AIVDM,1,1,,A,B5NJ;PP005l4ot5Isbl03wsUkP06,0*76"
        decoded = decode(msg)

        assert decoded.communication_state_raw == 393222
        assert decoded.is_itdma
        assert not decoded.is_sotdma

        comm_state = decoded.get_communication_state()

        assert isinstance(comm_state, dict)
        assert comm_state["received_stations"] is None
        assert comm_state["slot_number"] is None
        assert comm_state["utc_hour"] is None
        assert comm_state["utc_minute"] is None
        assert comm_state["slot_offset"] is None
        assert comm_state["slot_timeout"] is None
        assert comm_state["sync_state"] == SyncState.BASE_INDIRECT
        assert comm_state["keep_flag"] == 0
        assert comm_state["slot_increment"] == 0
        assert comm_state["num_slots"] == 3

    def test_get_comm_state_type_18_sotdma_utc_direct(self):
        msg = "!AIVDM,1,1,,A,B69A5U@3wk?8mP=18D3Q3wSRPD00,0*5C"
        decoded = decode(msg)

        assert decoded.communication_state_raw == 81920
        assert not decoded.is_itdma
        assert decoded.is_sotdma

        comm_state = decoded.get_communication_state()

        assert isinstance(comm_state, dict)
        assert comm_state["received_stations"] == 0
        assert comm_state["slot_number"] is None
        assert comm_state["utc_hour"] is None
        assert comm_state["utc_minute"] is None
        assert comm_state["slot_offset"] is None
        assert comm_state["slot_timeout"] == 5
        assert comm_state["sync_state"] == SyncState.UTC_DIRECT
        assert comm_state["keep_flag"] is None
        assert comm_state["slot_increment"] is None
        assert comm_state["num_slots"] is None

        # Also test decode_nmea_and_ais
        _, decoded_2 = decode_nmea_and_ais(msg)
        self.assertEqual(decoded_2, decoded)

    def test_get_comm_state_type_18_sotdma_base_inidrect(self):
        msg = "!AIVDM,1,1,,A,B69Gk3h071tpI02lT2ek?wg61P06,0*1F"
        decoded = decode(msg)

        assert decoded.communication_state_raw == 393222
        assert not decoded.is_itdma
        assert decoded.is_sotdma

        comm_state = decoded.get_communication_state()

        assert isinstance(comm_state, dict)
        assert comm_state["received_stations"] is None
        assert comm_state["slot_number"] is None
        assert comm_state["utc_hour"] is None
        assert comm_state["utc_minute"] is None
        assert comm_state["slot_offset"] == 6
        assert comm_state["slot_timeout"] == 0
        assert comm_state["sync_state"] == SyncState.BASE_INDIRECT
        assert comm_state["keep_flag"] is None
        assert comm_state["slot_increment"] is None
        assert comm_state["num_slots"] is None

    def test_static_data_report(self):
        msg_a = b"!ANVDM,1,1,,B,H5NuKGTUCBD8SaUG4:omol0hC33t,0*54"
        decoded_a = decode(msg_a)

        self.assertEqual(decoded_a.msg_type, 24)
        self.assertEqual(decoded_a.repeat, 0)
        self.assertEqual(decoded_a.mmsi, 368008030)
        self.assertEqual(decoded_a.partno, 1)
        self.assertEqual(decoded_a.ship_type, ShipType.PleasureCraft)
        self.assertEqual(decoded_a.vendorid, "SRT")
        self.assertEqual(decoded_a.callsign, "WDJ7574")
        self.assertEqual(decoded_a.to_bow, 6)
        self.assertEqual(decoded_a.to_stern, 19)
        self.assertEqual(decoded_a.to_port, 3)
        self.assertEqual(decoded_a.to_starboard, 3)

        msg_b = b"!ANVDM,1,1,,A,H5NuKGTUCBD8SaUG4:omol0hC33t,0*57"
        decoded_b = decode(msg_b)

        self.assertEqual(decoded_a, decoded_b)

    def test_special_position_report(self):
        msg = b"!ANVDM,1,1,,A,35O5WS1000r9FSHF@jBoLCACp000,0*42"
        decoded = decode(msg)

        self.assertEqual(decoded.msg_type, 3)
        self.assertEqual(decoded.repeat, 0)
        self.assertEqual(decoded.mmsi, 368142220)
        self.assertEqual(decoded.status, NavigationStatus.AtAnchor)
        self.assertEqual(decoded.turn, 0)
        self.assertEqual(decoded.speed, 0)
        self.assertEqual(decoded.accuracy, 1)
        self.assertEqual(decoded.lon, -81.84302)
        self.assertEqual(decoded.lat, 38.906152)
        self.assertEqual(decoded.course, 190.5)
        self.assertEqual(decoded.heading, 104)
        self.assertEqual(decoded.second, 41)
        self.assertEqual(decoded.raim, 0)

    def test_decode_does_not_raise_an_error_if_error_if_checksum_invalid_is_false(self):
        raw = b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*FF"
        msg = decode(raw, error_if_checksum_invalid=False)
        self.assertIsNotNone(
            msg,
        )

    def test_decode_does_not_raise_an_error_by_default(self):
        raw = b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*FF"
        msg = decode(raw)
        self.assertIsNotNone(msg)

    def test_decode_does_raise_an_error_if_error_if_checksum_invalid_is_true(self):
        raw = b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*FF"
        with self.assertRaises(InvalidNMEAChecksum):
            _ = decode(raw, error_if_checksum_invalid=True)

    def test_that_the_payload_does_not_change_when_encoding_decoding(self):
        """Refer to https://github.com/M0r13n/pyais/issues/86"""
        nmea = NMEAMessage(b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23")
        ais = nmea.decode()
        orig_bits = nmea.bit_array.to01()
        actual_bits = ais.to_bitarray().to01()

        self.assertEqual(orig_bits, actual_bits)

    def test_issue_88(self):
        """There was a decoding bug when the NMEA payload contains special characters"""
        raw = b"!AIVDM,1,1,,B,3815;`100!PhmnPPwL=3OmUd0Dg:,0*45"
        nmea = NMEAMessage(raw)
        ais = nmea.decode()
        self.assertIsNotNone(ais)

    def test_decode_into_bit_array_with_non_printable_characters(self):
        payload = b"3815;`100!Phmn\x1fPPwL=3OmUd0Dg:"
        with self.assertRaises(NonPrintableCharacterException):
            _ = decode_into_bit_array(payload)

        payload = b"3815;`100!Phmn\x7fPPwL=3OmUd0Dg:"
        with self.assertRaises(NonPrintableCharacterException):
            _ = decode_into_bit_array(payload)

    def test_gh_ais_message_decode(self):
        a = b"$PGHP,1,2008,5,9,0,0,0,10,338,2,,1,09*17"
        b = b"!AIVDM,1,1,,B,15NBj>PP1gG>1PVKTDTUJOv00<0M,0*09"

        # This should work and only return the AIS message
        decoded = decode(a, b)
        self.assertEqual(decoded.msg_type, 1)

        # This should return None as GH messages are only used to encapsulate NMEA messages.
        # Therefore, these are worthless without a NMEA message to encapsulate.
        with self.assertRaises(MissingMultipartMessageException):
            decode(
                a,
            )

    def test_common_invalid_inputs_to_the_decode_function(self):
        # A user could pass an currently unsupported message
        with self.assertRaises(UnknownMessageException):
            decode("$ANABK,,B,8,5,3*17")

        # A user could pass None
        with self.assertRaises(TypeError):
            decode(None)

        # A user could pass an NMEA instance, because he misread the documentation
        with self.assertRaises(TypeError):
            decode(AISSentence(b"!AIVDM,1,1,,B,15NBj>PP1gG>1PVKTDTUJOv00<0M,0*09"))

        # A user could pass some arbitrary bytes
        with self.assertRaises(UnknownMessageException):
            decode(b"AAA")

        with self.assertRaises(UnknownMessageException):
            decode(b"$AAA")

        with self.assertRaises(UnknownMessageException):
            decode(b"?!?!")

        with self.assertRaises(InvalidNMEAMessageException):
            decode(b"$AIVDM,")

        with self.assertRaises(InvalidNMEAMessageException):
            decode(b"$AIVDM,,,,,,")

        with self.assertRaises(InvalidNMEAMessageException):
            decode(b"")

    def test_messages_with_proprietary_suffix(self):
        msg = "!AIVDM,1,1,,B,181:Kjh01ewHFRPDK1s3IRcn06sd,0*08,raishub,1342569600"
        decoded = decode(msg)

        self.assertEqual(decoded.course, 87.0)
        self.assertEqual(decoded.msg_type, 1)
        self.assertEqual(decoded.mmsi, 538090443)
        self.assertEqual(decoded.speed, 10.9)

    def test_timestamp_message(self):
        msg = b"$PGHP,1,2004,12,21,23,59,58,999,219,219000001,219000002,1,6D*56"
        pghp: GatehouseSentence = decode_nmea_line(msg)

        self.assertIsInstance(pghp, GatehouseSentence)
        self.assertEqual(pghp.country, "219")
        self.assertEqual(pghp.region, "219000001")
        self.assertEqual(pghp.pss, "219000002")
        self.assertEqual(pghp.online_data, 1)
        self.assertEqual(
            pghp.timestamp, datetime.datetime(2004, 12, 21, 23, 59, 58, 999000)
        )

    def test_invalid_timestamp_message(self):
        with self.assertRaises(InvalidNMEAMessageException):
            decode_nmea_line(b"$PGHP,0,21")

        with self.assertRaises(InvalidNMEAMessageException):
            decode_nmea_line(b"$PGHP,1,11,11,11,11,11,58,999,219,11,1,6D*56")

        with self.assertRaises(UnknownMessageException):
            decode_nmea_line(b",n:4,r:35435435435,foo bar 200")

    def test_that_lat_and_long_are_rounded_correctly(self):
        """Original Issue: https://github.com/M0r13n/pyais/issues/107
        TL;DR: There was a rounding issue with certain values for lat and lon.
        Decoding, encoding and then decoding again led to slight changes to lat/lon."""

        orig = "!AIVDM,1,1,,A,100u3g@0291Q1>BW6uDUwDk00LE@,0*74"

        first_decode = decode(orig)
        encoded = encode_msg(first_decode)[0]
        second_decode = decode(encoded)

        self.assertEqual(first_decode, second_decode)

    def test_that_decode_nmea_and_ais_works_with_proprietary_messages(self):
        msg = "!AIVDM,1,1,,B,181:Kjh01ewHFRPDK1s3IRcn06sd,0*08,raishub,1342569600"
        nmea, decoded = decode_nmea_and_ais(msg)

        self.assertIsInstance(nmea, NMEAMessage)
        self.assertEqual(decoded.course, 87.0)
        self.assertEqual(decoded.msg_type, 1)
        self.assertEqual(decoded.mmsi, 538090443)
        self.assertEqual(decoded.speed, 10.9)

    def test_that_decode_works_for_fragmented_messages_with_empty_payloads(self):
        """Issue: https://github.com/M0r13n/pyais/issues/157"""
        # WHEN decoding a fragmented message where the second message has an empty payload.
        decoded = decode(
            b"!AIVDM,2,1,0,A,8@2R5Ph0GhRbUqe?n>KS?wvlFR06EuOwiOl?wnSwe7wvlOwwsAwwnSGmwvwt,0*4E",
            b"!AIVDM,2,2,0,A,,0*16",
        )
        # THEN the message is decoded without an error
        # Verified against https://www.aggsoft.com/ais-decoder.htm
        self.assertEqual(decoded.msg_type, 8)
        self.assertEqual(decoded.repeat, 1)
        self.assertEqual(decoded.mmsi, 2655619)
        self.assertEqual(decoded.data, b'\x08\xaa\x97\x9bO\xd8\xe6\xe3?\xff\xb4Z \x06W\xd7\xff\xc5\xfd\x0f\xffh\xff\xb4\x7f\xfe\xd1\xff\xff\xed\x1f\xff\xda5\xf5\xff\xef\xfc')

    def test_decode_with_empty_payload(self):
        """Variation of test_that_decode_works_for_fragmented_messages_with_empty_payloads"""
        # WHEN decoding message without payload an exception is raised
        with self.assertRaises(MissingPayloadException) as err:
            _ = decode(
                b"!AIVDM,1,1,0,A,,0*16",
            )

        self.assertEqual(str(err.exception), '!AIVDM,1,1,0,A,,0*16')

    def test_decode_type_21_full_name(self):
        raw = b"!AIVDM,1,1,,B,E>jHDL1W73nWaanah7S39T7a2h;wror=@5nL`A2AISd002CQ1PDS@0,4*39"
        decoded = decode(raw)

        assert decoded.full_name == "NNG-OSS-S OFFSHORE WINDFARM"

    def test_decode_fragment_count_0(self):
        msg = b"!AAVDM,0,1,,B,16UK7Fi0?w4tQF0l4Q@>401v1PS;,0*0F"

        # decode() should raise a TooManyMessagesException
        with self.assertRaises(TooManyMessagesException):
            decode(msg)

        # IterMessages should just skip it
        decoded = list(IterMessages([msg]))
        self.assertEqual(decoded, [])


if __name__ == '__main__':
    unittest.main()

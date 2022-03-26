import unittest

import bitarray

from pyais import encode_dict, encode_msg
from pyais.decode import decode
from pyais.encode import data_to_payload, get_ais_type
from pyais.exceptions import UnknownPartNoException
from pyais.messages import MessageType1, MessageType26BroadcastUnstructured, MessageType26AddressedUnstructured, \
    MessageType26BroadcastStructured, MessageType26AddressedStructured, MessageType25BroadcastUnstructured, \
    MessageType25AddressedUnstructured, MessageType25BroadcastStructured, MessageType25AddressedStructured, \
    MessageType24PartB, MessageType24PartA, MessageType22Broadcast, MessageType22Addressed, MessageType27, \
    MessageType23, MessageType21, MessageType20, MessageType19, MessageType18, MessageType17, MessageType16, \
    MessageType15, MessageType4, MessageType5, MessageType6, MessageType7, MessageType8, MessageType2, MessageType3, \
    MSG_CLASS
from pyais.util import decode_bin_as_ascii6, decode_into_bit_array, str_to_bin, int_to_bin, to_six_bit, encode_ascii_6, \
    int_to_bytes


def test_widths():
    tot_width = sum(field.metadata['width'] for field in MessageType1.fields())
    assert tot_width == 168

    tot_width = sum(field.metadata['width'] for field in MessageType4.fields())
    assert tot_width == 168

    tot_width = sum(field.metadata['width'] for field in MessageType5.fields())
    assert tot_width == 424

    tot_width = sum(field.metadata['width'] for field in MessageType6.fields())
    assert tot_width == 1008

    tot_width = sum(field.metadata['width'] for field in MessageType7.fields())
    assert tot_width == 168

    tot_width = sum(field.metadata['width'] for field in MessageType8.fields())
    assert tot_width == 1008

    tot_width = sum(field.metadata['width'] for field in MessageType15.fields())
    assert tot_width == 160

    tot_width = sum(field.metadata['width'] for field in MessageType15.fields())
    assert tot_width == 160

    tot_width = sum(field.metadata['width'] for field in MessageType16.fields())
    assert tot_width == 144

    tot_width = sum(field.metadata['width'] for field in MessageType17.fields())
    assert tot_width == 816

    tot_width = sum(field.metadata['width'] for field in MessageType18.fields())
    assert tot_width == 168

    tot_width = sum(field.metadata['width'] for field in MessageType19.fields())
    assert tot_width == 312

    tot_width = sum(field.metadata['width'] for field in MessageType20.fields())
    assert tot_width == 160

    tot_width = sum(field.metadata['width'] for field in MessageType21.fields())
    assert tot_width == 360

    tot_width = sum(field.metadata['width'] for field in MessageType23.fields())
    assert tot_width == 160

    tot_width = sum(field.metadata['width'] for field in MessageType27.fields())
    assert tot_width == 96


def test_variable_message_length_width():
    # 22
    tot_width = sum(field.metadata['width'] for field in MessageType22Addressed.fields())
    assert tot_width == 168

    tot_width = sum(field.metadata['width'] for field in MessageType22Broadcast.fields())
    assert tot_width == 168

    # 24
    tot_width = sum(field.metadata['width'] for field in MessageType24PartA.fields())
    assert tot_width == 168

    tot_width = sum(field.metadata['width'] for field in MessageType24PartB.fields())
    assert tot_width == 168

    # 25
    tot_width = sum(field.metadata['width'] for field in MessageType25AddressedStructured.fields())
    assert tot_width == 168

    tot_width = sum(field.metadata['width'] for field in MessageType25BroadcastStructured.fields())
    assert tot_width == 168

    tot_width = sum(field.metadata['width'] for field in MessageType25AddressedUnstructured.fields())
    assert tot_width == 168

    tot_width = sum(field.metadata['width'] for field in MessageType25BroadcastUnstructured.fields())
    assert tot_width == 168

    # 26
    classes = [MessageType26AddressedStructured, MessageType26BroadcastStructured,
               MessageType26AddressedUnstructured, MessageType26BroadcastUnstructured]

    for cls in classes:
        tot_width = sum(field.metadata['width'] for field in cls.fields())
        assert tot_width == 1064


def test_encode_msg_table():
    """
    Make sure that each message number as the correct Message class associated
    """
    for k, v in list(MSG_CLASS.items())[1:]:
        if k < 10:
            assert str(k) == v.__name__[-1:]
        else:
            assert str(k) == v.__name__[-2:]


def test_invalid_talker_id():
    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_dict({'mmsi': 123456}, talker_id="AIDDD")

    assert str(err.exception) == "talker_id must be any of ['AIVDM', 'AIVDO']"

    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_dict({'mmsi': 123456}, talker_id=None)

    assert str(err.exception) == "talker_id must be any of ['AIVDM', 'AIVDO']"


def test_encode_payload_invalid_talker_id():
    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_msg({'mmsi': 123456}, talker_id="AIDDD")

    assert str(err.exception) == "talker_id must be any of ['AIVDM', 'AIVDO']"

    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_msg({'mmsi': 123456}, talker_id=None)

    assert str(err.exception) == "talker_id must be any of ['AIVDM', 'AIVDO']"


def test_invalid_radio_channel():
    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_dict({'mmsi': 123456}, radio_channel="C")

    assert str(err.exception) == "radio_channel must be any of ['A', 'B']"

    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_dict({'mmsi': 123456}, radio_channel=None)

    assert str(err.exception) == "radio_channel must be any of ['A', 'B']"


def test_encode_payload_error_radio():
    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_msg({'mmsi': 123456}, radio_channel="C")

    assert str(err.exception) == "radio_channel must be any of ['A', 'B']"

    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_msg({'mmsi': 123456}, radio_channel=None)

    assert str(err.exception) == "radio_channel must be any of ['A', 'B']"


def test_data_to_payload():
    assert data_to_payload(0, {'mmsi': 123}).__class__ == MessageType1
    assert data_to_payload(1, {'mmsi': 123}).__class__ == MessageType1
    assert data_to_payload(2, {'mmsi': 123}).__class__ == MessageType2
    assert data_to_payload(3, {'mmsi': 123}).__class__ == MessageType3
    assert data_to_payload(4, {'mmsi': 123}).__class__ == MessageType4
    assert data_to_payload(5, {'mmsi': 123}).__class__ == MessageType5
    assert data_to_payload(6, {'mmsi': 123, 'dest_mmsi': 1234}).__class__ == MessageType6
    assert data_to_payload(7, {'mmsi': 123}).__class__ == MessageType7
    assert data_to_payload(8, {'mmsi': 123}).__class__ == MessageType8

    with unittest.TestCase().assertRaises(ValueError):
        data_to_payload(28, {'mmsi': 123})


def test_get_ais_type():
    ais_type = get_ais_type({'type': 1})
    assert ais_type == 1

    ais_type = get_ais_type({'type': '1'})
    assert ais_type == 1

    ais_type = get_ais_type({'msg_type': 1})
    assert ais_type == 1

    ais_type = get_ais_type({'msg_type': '1'})
    assert ais_type == 1

    with unittest.TestCase().assertRaises(ValueError) as err:
        get_ais_type({})
    assert str(err.exception) == "Missing or invalid AIS type. Must be a number."

    with unittest.TestCase().assertRaises(ValueError) as err:
        get_ais_type({'typee': 1})
    assert str(err.exception) == "Missing or invalid AIS type. Must be a number."


def test_str_to_bin():
    # Test that Hello is correctly converted
    string = str_to_bin("Hello", 5 * 6).to01()
    assert string == "001000000101001100001100001111"
    assert len(string) == 30

    # Test that at most width characters are encoded
    string = str_to_bin("Hello World", 5 * 6).to01()
    assert string == "001000000101001100001100001111"
    assert len(string) == 30

    # Test that trailing @'s are added
    string = str_to_bin("Hello", 96).to01()
    assert string == "001000000101001100001100001111000000000000000000000000000000000000000000000000000000000000000000"
    assert len(string) == 96


def test_int_to_bin():
    num = int_to_bin(0, 10).to01()
    assert num == "0000000000"
    assert len(num) == 10

    num = int_to_bin(6, 10).to01()
    assert num == "0000000110"
    assert len(num) == 10

    num = int_to_bin(128, 7).to01()
    assert num == "1111111"
    assert len(num) == 7

    num = int_to_bin(255, 8).to01()
    assert num == "11111111"
    assert len(num) == 8


@unittest.skip("TODO")
def test_decode_encode():
    """Create each message with default values and test that it can be decoded again"""
    mmsi = 123
    for typ in MSG_CLASS.keys():
        encoded = encode_dict({'mmsi': mmsi, 'dest_mmsi': 656634123, 'type': typ})
        decoded = decode(*encoded).asdict()

        assert decoded['mmsi'] == '000000123'
        if 'dest_mmsi' in decoded:
            assert decoded['dest_mmsi'] == '656634123'


def test_encode_type_27():
    data = {
        'accuracy': 0,
        'course': 167,
        'gnss': 0,
        'lat': 4.84,
        'lon': 137.02333333333334,
        'mmsi': '206914217',
        'raim': 0,
        'repeat': 0,
        'speed': 57,
        'status': 2,
        'type': 27
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,K35E2b@U19PFdLbL,0*71"


def test_encode_type_26():
    data = {
        'addressed': 0,
        'data': b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xc0",
        'mmsi': '016777280',
        'radio': 647746,
        'repeat': 0,
        'structured': 0,
        'type': 26
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,3,1,,A,J0@00@0000000000000000000000000000000000000000000000000000000,4*68"
    assert encoded[1] == "!AIVDO,3,2,,A,0000000000000000000000000000000000000000000000000000000000000,4*11"
    assert encoded[2] == "!AIVDO,3,3,,A,000000000000000000000000000000000000003wwwwwwwwwwww0WR@2,4*54"


def test_encode_type_25_b():
    data = {
        'addressed': 1,
        'data': b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xc0",
        'dest_mmsi': '134218384',
        'mmsi': '440006460',
        'repeat': 0,
        'structured': 1,
        'app_id': 45,
        'type': 25
    }
    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,I6SWo?<P00a00;Cwwwwwwwwwwww0,0*4A"


def test_encode_type_25_a():
    data = {
        'addressed': 1,
        'data': b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xc0",
        'dest_mmsi': '134218384',
        'mmsi': '440006460',
        'repeat': 0,
        'structured': 0,
        'type': 25
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,I6SWo?8P00a0003wwwwwwwwwwww0,0*35"


def test_encode_type_24_partno_invalid():
    # Should not raise an error
    encode_dict({'mmsi': 123, 'partno': 1, 'type': 24})

    with unittest.TestCase().assertRaises(UnknownPartNoException):
        encode_dict({'mmsi': 123, 'partno': 2, 'type': 24})

    with unittest.TestCase().assertRaises(UnknownPartNoException):
        encode_dict({'mmsi': 123, 'partno': 3, 'type': 24})


def test_encode_type_24_a():
    data = {
        'type': 24,
        'mmsi': '338091445',
        'partno': 0,
        'shipname': "HMS FooBar",
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,H52KMe@Pm>0Htt85800000000000,0*36"


def test_encode_type_24_b():
    data = {
        'callsign': '',
        'mmsi': '338091445',
        'model': 12,
        'mothership_mmsi': '000000000',
        'partno': 1,
        'repeat': 0,
        'serial': 199729,
        'ship_type': 37,  # PleasureCraft
        'to_bow': 0,
        'to_port': 0,
        'to_starboard': 0,
        'to_stern': 0,
        'type': 24,
        'vendorid': 'FEC'
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,H52KMeDU653hhhi0000000000000,0*18"


def test_encode_type_23():
    data = {
        'interval': 9,
        'mmsi': '002268120',
        'ne_lat': 3064.2000000000003,
        'ne_lon': 157.8,
        'quiet': 0,
        'repeat': 0,
        'shiptype': 0,
        'station_type': 6,
        'sw_lat': 3040.8,
        'sw_lon': 109.60000000000001,
        'txrx': 0,
        'type': 23
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,G02:Kn01R`sn@291nj600000900,2*13"


def test_encode_type_22_b():
    data = {
        'addressed': 1,
        'band_a': 0,
        'band_b': 0,
        'channel_a': 3584,
        'channel_b': 8,
        'dest1': '028144881',
        'dest2': '268435519',
        'mmsi': '017419965',
        'power': 1,
        'repeat': 0,
        'txrx': 1,
        'type': 22,
        'zonesize': 4
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,F0@W>gCP00PH=JrN84000?hB0000,0*75"


def test_encode_type_22_a():
    data = {
        'addressed': 0,
        'band_a': 0,
        'band_b': 0,
        'channel_a': 2087,
        'channel_b': 2088,
        'mmsi': '003160107',
        'ne_lat': 3300.0,
        'ne_lon': -7710.0,
        'power': 0,
        'repeat': 0,
        'sw_lat': 3210.0,
        'sw_lon': -8020.0,
        'txrx': 0,
        'type': 22,
        'zonesize': 2
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,F030p:j2N2P5aJR0r;6f3rj10000,0*10"


def test_encode_type_21():
    data = {
        'accuracy': 1,
        'aid_type': 1,  # Reference point
        'assigned': 0,
        'epfd': 1,  # GPS
        'lat': 48.65457,
        'lon': -123.429155,
        'mmsi': '316021442',
        'name': 'DFO2',
        'name_extension': '',
        'off_position': 1,
        'raim': 1,
        'regional': 0,
        'repeat': 0,
        'second': 18,
        'to_bow': 0,
        'to_port': 0,
        'to_starboard': 0,
        'to_stern': 0,
        'type': 21,
        'virtual_aid': 0
    }

    encoded = encode_dict(data)
    # Validated using: http://ais.tbsalling.dk/
    assert encoded[0] == "!AIVDO,1,1,,A,E4eHJhPR37q0000000000000000KUOSc=rq4h00000a@2000000000000000,4*39"

    data['regional'] = 255
    encoded = encode_dict(data)
    # Validated using: http://ais.tbsalling.dk/
    assert encoded[0] == "!AIVDO,1,1,,A,E4eHJhPR37q0000000000000000KUOSc=rq4h00000aOv000000000000000,4*72"


def test_encode_type_20():
    data = {
        'increment1': 750,
        'increment2': 0,
        'increment3': 0,
        'increment4': 0,
        'mmsi': '002243302',
        'number1': 5,
        'number2': 0,
        'number3': 0,
        'number4': 0,
        'offset1': 200,
        'offset2': 0,
        'offset3': 0,
        'offset4': 0,
        'repeat': 0,
        'timeout1': 7,
        'timeout2': 0,
        'timeout3': 0,
        'timeout4': 0,
        'type': 20
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,D028rqP<QNfp000000000000000,2*0E"


def test_encode_type_19():
    data = {
        'accuracy': 0,
        'assigned': 0,
        'course': 335.90000000000003,
        'dte': 0,
        'epfd': 1,  # GPS
        'heading': 511,
        'lat': 29.543695,
        'lon': -88.81039166666666,
        'mmsi': '367059850',
        'raim': 0,
        'regional': 4,
        'repeat': 0,
        'second': 46,
        'shipname': 'CAPT.J.RIMES',
        'ship_type': 70,  # CARGO
        'speed': 5.5,
        'to_bow': 5,
        'to_port': 4,
        'to_starboard': 4,
        'to_stern': 21,
        'type': 19
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,C5N3SRP0=nJGEBT>NhWAwwo862PaLELTBJ:V00000000S0D:R220,0*25"

    data['ship_type'] = 255
    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,C5N3SRP0=nJGEBT>NhWAwwo862PaLELTBJ:V0000000000D:R220,0*46"


def test_encode_type_18_with_speed_and_course():
    data = {
        'accuracy': 0,
        'assigned': 0,
        'band': 1,
        'course': 10.1,
        'cs': 1,
        'display': 0,
        'dsc': 1,
        'heading': 511,
        'lat': 37.785035,
        'lon': -122.26732,
        'mmsi': '367430530',
        'msg22': 1,
        'radio': 917510,
        'raim': 0,
        'regional': 0,
        'repeat': 0,
        'second': 55,
        'speed': 67.85,
        'type': 18
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,B5NJ;PP2aUl4ot5Isbl6GwsUkP06,0*35"


def test_encode_type_18():
    data = {
        'accuracy': 0,
        'assigned': 0,
        'band': 1,
        'course': 0.0,
        'cs': 1,
        'display': 0,
        'dsc': 1,
        'heading': 511,
        'lat': 37.785035,
        'lon': -122.26732,
        'mmsi': '367430530',
        'msg22': 1,
        'radio': 917510,
        'raim': 0,
        'regional': 0,
        'repeat': 0,
        'second': 55,
        'speed': 0.0,
        'type': 18
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,B5NJ;PP005l4ot5Isbl03wsUkP06,0*74"

    data['heading'] = 123
    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,B5NJ;PP005l4ot5Isbl00usUkP06,0*75"


def test_encode_type_17_b():
    data = {
        'data': 14486955885545814640451754168044205828166539334830080,
        'lat': 2058.2,
        'lon': 8029.2,
        'mmsi': '004310602',
        'repeat': 0,
        'type': 17
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,3,1,,A,A0476BQ>J@`<h000000000000000000000000000000000000000000000000,0*71"
    assert encoded[1] == "!AIVDO,3,2,,A,0000000000000000000000000000000000000000000000Vf62Q803tT0eI5O,0*3D"
    assert encoded[2] == "!AIVDO,3,3,,A,j:3E80E5MfOdP0,0*1A"


def test_encode_type_17_a():
    data = {
        'data': 74564674320211730832670193178193588797084406868345488138198505092899590740876957371807575026797147834907158489770,
        'lat': 3599.2,
        'lon': 1747.8,
        'mmsi': '002734450',
        'repeat': 0,
        'type': 17
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,3,1,,A,A02VqLPA4I6C0000000000000000000000000000000000000000000000000,0*27"
    assert encoded[1] == "!AIVDO,3,2,,A,0000000000007h5Ed1h<OrsuBTTwS?r:C?w`?la<gno1RTRwSP9:BcurA8a:O,0*7B"
    assert encoded[2] == "!AIVDO,3,3,,A,ko02TSwu8<:Jbb,0*53"


def test_encode_type_16():
    data = {
        'increment1': 0,
        'increment2': 0,
        'mmsi': '002053501',
        'mmsi1': '224251000',
        'mmsi2': '000000000',
        'offset1': 200,
        'offset2': 0,
        'repeat': 0,
        'type': 16
    }
    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,@01uEO@mMk7P<P0000000000,0*1A"


def test_encode_type_15_a():
    data = {
        'mmsi': '003669720',
        'mmsi1': '367014320',
        'mmsi2': '000000000',
        'offset1_1': 516,
        'offset1_2': 617,
        'offset2_1': 0,
        'repeat': 3,
        'type': 15,
        'type1_1': 3,
        'type1_2': 5,
        'type2_1': 0
    }
    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,?h3Ovn1GP<K0<P@59a000000000,2*05"


def test_encode_type_15():
    data = {
        'mmsi': '368578000',
        'mmsi1': '000005158',
        'mmsi2': '000000000',
        'offset1_1': 0,
        'offset1_2': 0,
        'offset2_1': 0,
        'repeat': 0,
        'type': 15,
        'type1_1': 5,
        'type1_2': 0,
        'type2_1': 0
    }
    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,?5OP=l00052HD00000000000000,2*59"


def test_encode_type_14():
    data = {'mmsi': '351809000', 'repeat': 0, 'text': 'RCVD YR TEST MSG', 'type': 14}
    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,3,1,,A,>5?Per18=HB1U:1@E=B0m<L00000000000000000000000000000000000000,2*51"
    assert encoded[1] == "!AIVDO,3,2,,A,0000000000000000000000000000000000000000000000000000000000000,2*17"
    assert encoded[2] == "!AIVDO,3,3,,A,0000000000000000000000000000000000000000000000,2*26"


def test_encode_type_13():
    data = {
        'mmsi': '211378120',
        'mmsi1': '211217560',
        'mmsi2': '000000000',
        'mmsi3': '000000000',
        'mmsi4': '000000000',
        'mmsiseq1': 2,
        'mmsiseq2': 0,
        'mmsiseq3': 0,
        'mmsiseq4': 0,
        'repeat': 0,
        'type': 13
    }
    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,739UOj0jFs9R0000000000000000,0*6D"


def test_encode_type_12():
    data = {
        'dest_mmsi': '271002111',
        'mmsi': '271002099',
        'repeat': 0,
        'retransmit': 1,
        'seqno': 0,
        'text': 'MSG FROM 271002099',
        'type': 12
    }
    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,3,1,,A,<42Lati0W:Ov=C7P6B?=Pjoihhjhqq0000000000000000000000000000000,0*29"
    assert encoded[1] == "!AIVDO,3,2,,A,0000000000000000000000000000000000000000000000000000000000000,0*15"
    assert encoded[2] == "!AIVDO,3,3,,A,0000000000000000000000000000000000000000000000,0*24"


def test_encode_type_11():
    data = {
        'accuracy': 1,
        'day': 22,
        'epfd': 1,
        'hour': 2,
        'lat': 28.409117,
        'lon': -94.40768,
        'minute': 22,
        'mmsi': '304137000',
        'month': 5,
        'radio': 0,
        'raim': 0,
        'repeat': 0,
        'second': 40,
        'type': 11,
        'year': 2009
    }
    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,44R33:1uUK2F`q?mP0@@GoQ00000,0*08"


def test_encode_type_10():
    data = {'dest_mmsi': '366972000', 'mmsi': '440882000', 'repeat': 0, 'type': 10}
    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,:6TMCD1GOS60,0*5A"


def test_encode_type_9():
    data = {
        'accuracy': 0,
        'alt': 303,
        'assigned': 0,
        'course': 154.5,
        'dte': 1,
        'lat': 58.144,
        'lon': -6.2788434,
        'mmsi': '111232511',
        'radio': 33392,
        'raim': 0,
        'repeat': 0,
        'second': 15,
        'speed': 42,
        'type': 9
    }
    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,91b55wi;hbOS@OdQAC062Ch2089h,0*31"


def test_encode_type_8():
    data = {
        'dac': 366,
        'data': 0x3a53dbb7be4a773137f87d7b0445f040dea05d93f593783194ae9b9d9dbe05fb,
        'fid': 56,
        'mmsi': '366999712',
        'repeat': 0,
        'type': 8
    }
    encoded = encode_dict(data, radio_channel="B", talker_id="AIVDM")
    assert encoded[0] == "!AIVDM,3,1,,B,85Mwp`1Kf0000000000000000000000000000000000000000000000000000,0*1C"
    assert encoded[1] == "!AIVDM,3,2,,B,0000000000000000000000000000000000000000000000000000000000000,0*14"
    assert encoded[2] == "!AIVDM,3,3,,B,0003aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*4F"


def test_encode_type_7():
    data = {
        'mmsi': '002655651',
        'mmsi1': '265538450',
        'mmsi2': '000000000',
        'mmsiseq1': 0,
        'mmsiseq2': 0,
        'repeat': 0,
        'type': 7
    }
    encoded_part_1 = encode_dict(data, radio_channel="B", talker_id="AIVDM")[0]
    assert encoded_part_1 == "!AIVDM,1,1,,B,702R5`hwCjq80000000000000000,0*68"


def test_encode_type_6_bytes():
    data = {
        'dac': 669,
        'data': b'\x03\xac\xbcF=\xff\xc4',
        'dest_mmsi': '313240222',
        'fid': 11,
        'mmsi': '150834090',
        'repeat': 1,
        'retransmit': 0,
        'seqno': 3,
        'type': 6
    }
    encoded = encode_dict(data, radio_channel="B", talker_id="AIVDM")
    assert encoded[0] == "!AIVDM,3,1,,B,6B?n;be:cbapald0000000000000000000000000000000000000000000000,0*7D"
    assert encoded[1] == "!AIVDM,3,2,,B,0000000000000000000000000000000000000000000000000000000000000,0*14"
    assert encoded[2] == "!AIVDM,3,3,,B,00000000000000000000000000000000000003c;i6?Ow4,0*12"


def test_encode_type_6():
    data = {
        'dac': 669,
        'data': 0x3acbc463dffc4,
        'dest_mmsi': '313240222',
        'fid': 11,
        'mmsi': '150834090',
        'repeat': 1,
        'retransmit': 0,
        'seqno': 3,
        'type': 6
    }
    encoded = encode_dict(data, radio_channel="B", talker_id="AIVDM")
    assert encoded[0] == "!AIVDM,3,1,,B,6B?n;be:cbapald0000000000000000000000000000000000000000000000,0*7D"
    assert encoded[1] == "!AIVDM,3,2,,B,0000000000000000000000000000000000000000000000000000000000000,0*14"
    assert encoded[2] == "!AIVDM,3,3,,B,00000000000000000000000000000000000003c;i6?Ow4,0*12"


def test_encode_type_4():
    data = {
        'accuracy': 1,
        'day': 14,
        'epfd': 7,
        'hour': 19,
        'lat': 36.88376,
        'lon': -76.3523,
        'minute': 57,
        'mmsi': '003669702',
        'month': 5,
        'radio': 67039,
        'raim': 0,
        'repeat': 0,
        'second': 39,
        'type': 4,
        'year': 2007
    }
    encoded_part_1 = encode_dict(data, radio_channel="B", talker_id="AIVDM")[0]

    assert encoded_part_1 == "!AIVDM,1,1,,B,403OviQuMGCqWrRO:HE6fD700@GO,0*3A"


def test_encode_type_5_issue_59():
    """https://github.com/M0r13n/pyais/issues/59"""
    data = {
        'ais_version': 0,
        'callsign': '3FOF8',
        'day': 15,
        'destination': 'NEW YORK',
        'draught': 12.8,
        'dte': 0,
        'epfd': 1,
        'hour': 14,
        'imo': 9134270,
        'minute': 0,
        'mmsi': '351759000',
        'month': 5,
        'repeat': 0,
        'shipname': 'EVER DIADEM',
        'shiptype': 70,
        'to_bow': 225,
        'to_port': 1,
        'to_starboard': 31,
        'to_stern': 70,
        'type': 5
    }

    encoded_part_1 = encode_dict(data, radio_channel="B", talker_id="AIVDM")[0]
    encoded_part_2 = encode_dict(data, radio_channel="B", talker_id="AIVDM")[1]
    assert encoded_part_1 == "!AIVDM,2,1,,B,55?MbV02;H;s<HtKP00EHE:0@T4@Dl0000000000L961O5Gf0P3QEp6ClRh00,2*77"
    assert encoded_part_2 == "!AIVDM,2,2,,B,0000000000,2*27"


def test_encode_type_5():
    """
    Verified using http://ais.tbsalling.dk/.
    """
    data = {
        'ais_version': 0,
        'callsign': '3FOF8',
        'day': 15,
        'destination': 'NEW YORK',
        'draught': 12.2,
        'dte': 0,
        'epfd': 1,
        'hour': 14,
        'imo': 9134270,
        'minute': 0,
        'mmsi': '351759000',
        'month': 5,
        'repeat': 0,
        'shipname': 'EVER DIADEM',
        'shiptype': 70,
        'to_bow': 225,
        'to_port': 1,
        'to_starboard': 31,
        'to_stern': 70,
        'type': 5
    }

    encoded_part_1 = encode_dict(data, radio_channel="B", talker_id="AIVDM")[0]
    encoded_part_2 = encode_dict(data, radio_channel="B", talker_id="AIVDM")[1]  #
    assert encoded_part_1 == "!AIVDM,2,1,,B,55?MbV02;H;s<HtKP00EHE:0@T4@Dl0000000000L961O5Gf0NSQEp6ClRh00,2*09"
    assert encoded_part_2 == "!AIVDM,2,2,,B,0000000000,2*27"


def test_encode_type_5_default():
    """
    Verified using http://ais.tbsalling.dk/.
    """
    data = {'mmsi': 123456789, 'type': 5}
    encoded_part_1 = encode_dict(data, radio_channel="B", talker_id="AIVDM")[0]
    encoded_part_2 = encode_dict(data, radio_channel="B", talker_id="AIVDM")[1]
    assert encoded_part_1 == "!AIVDM,2,1,,B,51mg=5@000000000000000000000000000000000000000000000000000000,2*62"
    assert encoded_part_2 == "!AIVDM,2,2,,B,0000000000,2*27"


def test_encode_msg_type2():
    data = {
        'accuracy': 1,
        'course': 0.0,
        'heading': 511,
        'lat': 53.542675,
        'lon': 9.979428333333333,
        'mmsi': '211512520',
        'raim': 1,
        'repeat': 2,
        'second': 34,
        'speed': 0.3,
        'turn': -128,
        'type': 2
    }

    encoded = encode_dict(data)[0]
    assert encoded == "!AIVDO,1,1,,A,1S9edj0P03PecbBN`ja@0?w42000,0*2A"


def test_encode_msg_type_3():
    data = {
        'accuracy': 0,
        'course': 254.20000000000002,
        'heading': 217,
        'lat': 37.81065,
        'lon': -122.3343,
        'mmsi': '367581220',
        'radio': 86346,
        'raim': 0,
        'repeat': 0,
        'second': 40,
        'speed': 0.1,
        'status': 5,
        'turn': 0,
        'type': 3
    }

    encoded = encode_dict(data)[0]
    assert encoded == "!AIVDO,1,1,,A,15NSH95001G?wopE`beasVk@0E5:,0*6F"


def test_encode_type_1_default():
    """
    Verified using http://ais.tbsalling.dk/.
    """
    data = {'mmsi': 123456789, 'type': 1}
    encoded = encode_dict(data)[0]
    assert encoded == "!AIVDO,1,1,,A,11mg=5@000000000000000000000,0*56"


def test_encode_type_1():
    """
    Verified using http://ais.tbsalling.dk/.
    """
    data = {
        'accuracy': 0,
        'course': 219.3,
        'heading': 1,
        'lat': 37.80211833333333,
        'lon': -122.34161833333333,
        'maneuver': 0,
        'mmsi': '366053209',
        'radio': 2281,
        'raim': 0,
        'repeat': 0,
        'second': 59,
        'speed': 7.8,
        'status': 3,
        'turn': 0,
        'type': 1
    }

    encoded = encode_dict(data, radio_channel="B", talker_id="AIVDM")[0]
    assert encoded == "!AIVDM,1,1,,B,15M67FC01>G?ufbE`FepT@3n00Sa,0*53"

    encoded = encode_dict(data, radio_channel="B")[0]
    assert encoded == "!AIVDO,1,1,,B,15M67FC01>G?ufbE`FepT@3n00Sa,0*51"


def test_mmsi_too_long():
    msg = MessageType1.create(mmsi=1 << 35)
    encoded = encode_msg(msg)
    assert encoded[0] == "!AIVDO,1,1,,A,1?wwwwh000000000000000000000,0*72"


def test_lon_too_large():
    msg = MessageType1.create(mmsi="123", lon=1 << 30)
    encoded = encode_msg(msg)
    assert encoded[0] == "!AIVDO,1,1,,A,10000Nh000Owwwv0000000000000,0*7D"


def test_ship_name_too_lon():
    msg = MessageType5.create(mmsi="123", shipname="Titanic Titanic Titanic")
    encoded = encode_msg(msg)
    assert encoded[0] == "!AIVDO,2,1,,A,50000Nh000000000001@U@4pT>1@U@4pT>1@U@40000000000000000000000,2*56"
    assert encoded[1] == "!AIVDO,2,2,,A,0000000000,2*26"


def test_int_to_bytes():
    i = int_to_bytes(b'\xff\xff')
    assert i == 65535

    i = int_to_bytes(65535)
    assert i == 65535

    i = int_to_bytes(b'\x00\x00')
    assert i == 0


def test_to_six_bit():
    c = to_six_bit('a')
    assert c == '000001'

    c = to_six_bit('A')
    assert c == '000001'

    c = to_six_bit('9')
    assert c == '111001'

    with unittest.TestCase().assertRaises(ValueError):
        to_six_bit('ä')


def test_encode_ascii_6_bit():
    input_val = '001000000101001100001100001111100000010111001111010010001100000100100001'
    b = bitarray.bitarray(input_val)
    ascii6, padding = encode_ascii_6(b)

    assert ascii6 == "85<<?PG?B<4Q"
    assert padding == 0

    bit_arr = decode_into_bit_array(ascii6.encode())
    assert bit_arr.to01() == input_val
    assert decode_bin_as_ascii6(bit_arr) == "HELLO WORLD!"

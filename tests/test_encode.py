import unittest

import bitarray

from pyais.encode import encode_dict, MessageType4, MessageType1, MessageType5, MessageType6, MessageType7, \
    MessageType8, data_to_payload, MessageType2, MessageType3, get_ais_type, str_to_bin, int_to_bin, encode_payload, \
    int_to_bytes, to_six_bit, encode_ascii_6
from pyais.util import decode_bin_as_ascii6, decode_into_bit_array


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


def test_invalid_talker_id():
    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_dict({'mmsi': 123456}, talker_id="AIDDD")

    assert str(err.exception) == "talker_id must be any of ['AIVDM', 'AIVDO']"

    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_dict({'mmsi': 123456}, talker_id=None)

    assert str(err.exception) == "talker_id must be any of ['AIVDM', 'AIVDO']"


def test_encode_payload_invalid_talker_id():
    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_payload({'mmsi': 123456}, talker_id="AIDDD")

    assert str(err.exception) == "talker_id must be any of ['AIVDM', 'AIVDO']"

    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_payload({'mmsi': 123456}, talker_id=None)

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
        encode_payload({'mmsi': 123456}, radio_channel="C")

    assert str(err.exception) == "radio_channel must be any of ['A', 'B']"

    with unittest.TestCase().assertRaises(ValueError) as err:
        encode_payload({'mmsi': 123456}, radio_channel=None)

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
        data_to_payload(27, {'mmsi': 123})


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
    encoded_part_2 = encode_dict(data, radio_channel="B", talker_id="AIVDM")[1]
    assert encoded_part_1 == "!AIVDM,2,1,,B,55?MbV02;H;s<HtKP00EHE:0@T4@Dl0000000016L961O5Gf0NSQEp6ClRh00,2*0E"
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
        'speed': 0.0,
        'status': 3,
        'turn': 0,
        'type': 1
    }

    encoded = encode_dict(data, radio_channel="B", talker_id="AIVDM")[0]
    assert encoded == "!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C"

    encoded = encode_dict(data, radio_channel="B")[0]
    assert encoded == "!AIVDO,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5E"


def test_mmsi_too_long():
    msg = MessageType1.create(mmsi=1 << 35)
    encoded = encode_payload(msg)
    assert encoded[0] == "!AIVDO,1,1,,A,1?wwwwh000000000000000000000,0*72"


def test_lon_too_large():
    msg = MessageType1.create(mmsi="123", lon=1 << 30)
    encoded = encode_payload(msg)
    assert encoded[0] == "!AIVDO,1,1,,A,10000Nh000Owwwv0000000000000,0*7D"


def test_ship_name_too_lon():
    msg = MessageType5.create(mmsi="123", shipname="Titanic Titanic Titanic")
    encoded = encode_payload(msg)
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

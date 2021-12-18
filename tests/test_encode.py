from pyais.encode import encode_dict


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

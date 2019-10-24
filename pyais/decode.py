from .constants import *
from .util import *
from functools import partial


def decode_msg_1(bit_arr):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_int_from_data(8, 38),
        'status': NavigationStatus(get_int_from_data(38, 42)),
        'turn': get_int_from_data(42, 50, signed=True),
        'speed': get_int_from_data(50, 60),
        'accuracy': bit_arr[60],
        'lon': get_int_from_data(61, 89, signed=True) / 600000.0,
        'lat': get_int_from_data(89, 116, signed=True) / 600000.0,
        'course': get_int_from_data(116, 128) * 0.1,
        'heading': get_int_from_data(128, 137),
        'second': get_int_from_data(137, 143),
        'maneuver': ManeuverIndicator(get_int_from_data(143, 145)),
        'raim': bit_arr[148],
        'radio': get_int_from_data(149, bit_arr.length()),
    }


def decode_msg_2(bit_arr):
    """AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    return decode_msg_1(bit_arr)


def decode_msg_3(bit_arr):
    """
    AIS Vessel position report using ITDMA (Incremental Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    return decode_msg_1(bit_arr)


def decode_msg_4(bit_arr):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_4_base_station_report
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_int_from_data(3, 38),
        'year': get_int_from_data(38, 52),
        'month': get_int_from_data(52, 56),
        'day': get_int_from_data(56, 61),
        'hour': get_int_from_data(61, 66),
        'minute': get_int_from_data(66, 72),
        'second': get_int_from_data(72, 78),
        'accuracy': bit_arr[78],
        'lon': get_int_from_data(79, 106, signed=True) / 600000.0,
        'lat': get_int_from_data(106, 133, signed=True) / 600000.0,
        'epfd': EpfdType(get_int_from_data(134, 138)),
        'raim': bit_arr[148],
        'radio': get_int_from_data(148, len(bit_arr)),
    }


def decode_msg_5(bit_arr):
    get_int_from_data = partial(get_int, bit_arr)
    ship_type = get_int_from_data(232, 240)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_int_from_data(8, 38),
        'ais_version': get_int_from_data(38, 40),
        'imo': get_int_from_data(40, 70),
        'callsign': encode_bin_as_ascii6(bit_arr[70:112]),
        'shipname': encode_bin_as_ascii6(bit_arr[112:232]),
        'shiptype': (ship_type, SHIP_TYPE.get(ship_type, NULL)),
        'to_bow': get_int_from_data(240, 249),
        'to_stern': get_int_from_data(249, 259),
        'to_port': get_int_from_data(258, 264),
        'to_starboard': get_int_from_data(264, 270),
        'epfd': EpfdType(get_int_from_data(270, 274)),
        'month': get_int_from_data(274, 278),
        'day': get_int_from_data(278, 283),
        'hour': get_int_from_data(283, 288),
        'minute': get_int_from_data(288, 294),
        'draught': get_int_from_data(294, 302) / 10.0,
        'destination': encode_bin_as_ascii6(bit_arr[302:422]),
        'dte': bit_arr[-2]
    }


def decode_msg_6(bit_vector):
    pass


def decode_msg_7(bit_vector):
    pass


def decode_msg_8(bit_vector):
    pass


def decode_msg_9(bit_vector):
    pass


def decode_msg_10(bit_vector):
    pass


def decode_msg_11(bit_vector):
    pass


def decode_msg_12(bit_vector):
    pass


def decode_msg_13(bit_vector):
    pass


def decode_msg_14(bit_vector):
    pass


def decode_msg_15(bit_vector):
    pass


def decode_msg_16(bit_vector):
    pass


def decode_msg_17(bit_vector):
    pass


def decode_msg_18(bit_arr):
    """
    Standard Class B CS Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_18_standard_class_b_cs_position_report
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(8, 8),
        'mmsi': get_int_from_data(8, 38),
        'speed': get_int_from_data(46, 55),
        'accuracy': bit_arr[55],
        'lon': get_int_from_data(56, 85, signed=True) / 600000.0,
        'lat': get_int_from_data(85, 112, signed=True) / 600000.0,
        'course': get_int_from_data(112, 124) * 0.1,
        'heading': get_int_from_data(124, 133),
        'second': get_int_from_data(133, 139),
        'regional': get_int_from_data(139, 141),
        'cs': bit_arr[141],
        'display': bit_arr[142],
        'dsc': bit_arr[143],
        'band': bit_arr[144],
        'msg22': bit_arr[145],
        'assigned': bit_arr[146],
        'raim': bit_arr[147],
        'radio': get_int_from_data(148, len(bit_arr)),
    }


def decode_msg_19(bit_vector):
    pass


def decode_msg_20(bit_vector):
    pass


def decode_msg_21(bit_vector):
    pass


def decode_msg_22(bit_vector):
    pass


def decode_msg_23(bit_vector):
    pass


def decode_msg_24(bit_vector):
    pass


# Decoding Lookup Table
DECODE_MSG = [
    None,
    decode_msg_1,
    decode_msg_2,
    decode_msg_3,
    decode_msg_4,
    decode_msg_5,
    decode_msg_6,
    decode_msg_7,
    decode_msg_8,
    decode_msg_9,
    decode_msg_10,
    decode_msg_11,
    decode_msg_12,
    decode_msg_13,
    decode_msg_14,
    decode_msg_15,
    decode_msg_16,
    decode_msg_17,
    decode_msg_18,
    decode_msg_19,
    decode_msg_20,
    decode_msg_21,
    decode_msg_22,
    decode_msg_23,
    decode_msg_24
]


def decode(msg):
    if msg.is_valid and 0 < msg.ais_id < 25:
        return DECODE_MSG[msg.ais_id](msg.bit_array)

    return None

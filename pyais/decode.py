from functools import partial
from typing import Any, Dict, Union

import bitarray  # type: ignore

from pyais.constants import (
    NavigationStatus,
    ManeuverIndicator,
    TransmitMode,
    EpfdType,
    ShipType,
    StationType,
    StationIntervals,
    NavAid
)
from pyais.exceptions import UnknownMessageException
from pyais import messages
from pyais.util import get_int, encode_bin_as_ascii6, get_mmsi


def decode_msg_1(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'status': NavigationStatus(get_int_from_data(38, 42)),
        'turn': get_int_from_data(42, 50, signed=True),
        'speed': get_int_from_data(50, 60) / 10.0,
        'accuracy': bit_arr[60],
        'lon': get_int_from_data(61, 89, signed=True) / 600000.0,
        'lat': get_int_from_data(89, 116, signed=True) / 600000.0,
        'course': get_int_from_data(116, 128) * 0.1,
        'heading': get_int_from_data(128, 137),
        'second': get_int_from_data(137, 143),
        'maneuver': ManeuverIndicator(get_int_from_data(143, 145)),
        'raim': bit_arr[148],
        'radio': get_int_from_data(149, len(bit_arr)),
    }


def decode_msg_2(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    return decode_msg_1(bit_arr)


def decode_msg_3(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    AIS Vessel position report using ITDMA (Incremental Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    return decode_msg_1(bit_arr)


def decode_msg_4(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_4_base_station_report
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'year': get_int_from_data(38, 52),
        'month': get_int_from_data(52, 56),
        'day': get_int_from_data(56, 61),
        'hour': get_int_from_data(61, 66),
        'minute': get_int_from_data(66, 72),
        'second': get_int_from_data(72, 78),
        'accuracy': bit_arr[78],
        'lon': get_int_from_data(79, 107, signed=True) / 600000.0,
        'lat': get_int_from_data(107, 134, signed=True) / 600000.0,
        'epfd': EpfdType(get_int_from_data(134, 138)),
        'raim': bit_arr[148],
        'radio': get_int_from_data(148, len(bit_arr)),
    }


def decode_msg_5(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Static and Voyage Related Data
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_5_static_and_voyage_related_data
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'ais_version': get_int_from_data(38, 40),
        'imo': get_int_from_data(40, 70),
        'callsign': encode_bin_as_ascii6(bit_arr[70:112]),
        'shipname': encode_bin_as_ascii6(bit_arr[112:232]),
        'shiptype': ShipType(get_int_from_data(232, 240)),
        'to_bow': get_int_from_data(240, 249),
        'to_stern': get_int_from_data(249, 258),
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


def decode_msg_6(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Binary Addresses Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_4_base_station_report
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'seqno': get_int_from_data(38, 40),
        'dest_mmsi': get_mmsi(bit_arr, 40, 70),
        'retransmit': bit_arr[70],
        'dac': get_int_from_data(72, 82),
        'fid': get_int_from_data(82, 88),
        'data': bit_arr[88:].to01()
    }


def decode_msg_7(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Binary Acknowledge
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_7_binary_acknowledge
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'mmsi1': get_mmsi(bit_arr, 40, 70),
        'mmsiseq1': get_int_from_data(70, 72),
        'mmsi2': get_mmsi(bit_arr, 72, 102),
        'mmsiseq2': get_int_from_data(102, 104),
        'mmsi3': get_mmsi(bit_arr, 104, 134),
        'mmsiseq3': get_int_from_data(134, 136),
        'mmsi4': get_mmsi(bit_arr, 136, 166),
        'mmsiseq4': get_int_from_data(166, 168)
    }


def decode_msg_8(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Binary Acknowledge
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_8_binary_broadcast_message
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'dac': get_int_from_data(40, 50),
        'fid': get_int_from_data(50, 56),
        'data': bit_arr[56:].to01()
    }


def decode_msg_9(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Standard SAR Aircraft Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_9_standard_sar_aircraft_position_report
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'alt': get_int_from_data(38, 50),
        'speed': get_int_from_data(50, 60),
        'accuracy': bit_arr[60],
        'lon': get_int_from_data(61, 89, signed=True) / 600000.0,
        'lat': get_int_from_data(89, 116, signed=True) / 600000.0,
        'course': get_int_from_data(116, 128) * 0.1,
        'second': get_int_from_data(128, 134),
        'dte': bit_arr[142],
        'assigned': bit_arr[146],
        'raim': bit_arr[147],
        'radio': get_int_from_data(148, 168)
    }


def decode_msg_10(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    UTC/Date Inquiry
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_10_utc_date_inquiry
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'dest_mmsi': get_mmsi(bit_arr, 40, 70)
    }


def decode_msg_11(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    UTC/Date Response
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_11_utc_date_response
    """
    return decode_msg_4(bit_arr)


def decode_msg_12(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Addressed Safety-Related Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_12_addressed_safety_related_message
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'seqno': get_int_from_data(38, 40),
        'dest_mmsi': get_mmsi(bit_arr, 40, 70),
        'retransmit': bit_arr[70],
        'text': encode_bin_as_ascii6(bit_arr[72:])
    }


def decode_msg_13(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Identical to type 7
    """
    return decode_msg_7(bit_arr)


def decode_msg_14(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Safety-Related Broadcast Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_14_safety_related_broadcast_message
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'text': encode_bin_as_ascii6(bit_arr[40:])
    }


def decode_msg_15(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Interrogation
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_15_interrogation
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'mmsi1': get_mmsi(bit_arr, 40, 70),
        'type1_1': get_int_from_data(70, 76),
        'offset1_1': get_int_from_data(76, 88),
        'type1_2': get_int_from_data(90, 96),
        'offset1_2': get_int_from_data(96, 108),
        'mmsi2': get_mmsi(bit_arr, 110, 140),
        'type2_1': get_int_from_data(140, 146),
        'offset2_1': get_int_from_data(146, 157),
    }


def decode_msg_16(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Assignment Mode Command
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_16_assignment_mode_command
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'mmsi1': get_mmsi(bit_arr, 40, 70),
        'offset1': get_int_from_data(70, 82),
        'increment1': get_int_from_data(82, 92),
        'mmsi2': get_mmsi(bit_arr, 92, 122),
        'offset2': get_int_from_data(122, 134),
        'increment2': get_int_from_data(134, 144)
    }


def decode_msg_17(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    DGNSS Broadcast Binary Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_17_dgnss_broadcast_binary_message
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'lon': get_int_from_data(40, 58, signed=True),
        'lat': get_int_from_data(58, 75, signed=True),
        'data': get_int_from_data(80, 816)
    }


def decode_msg_18(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Standard Class B CS Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_18_standard_class_b_cs_position_report
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(8, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'speed': get_int_from_data(46, 56) * 0.1,
        'accuracy': bit_arr[56],
        'lon': get_int_from_data(57, 85, signed=True) / 600000.0,
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


def decode_msg_19(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Extended Class B CS Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_19_extended_class_b_cs_position_report
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(8, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'speed': get_int_from_data(46, 56) * 0.1,
        'accuracy': bit_arr[56],
        'lon': get_int_from_data(57, 85, signed=True) / 600000.0,
        'lat': get_int_from_data(85, 112, signed=True) / 600000.0,
        'course': get_int_from_data(112, 124) * 0.1,
        'heading': get_int_from_data(124, 133),
        'second': get_int_from_data(133, 139),
        'regional': get_int_from_data(139, 143),
        'shipname': encode_bin_as_ascii6(bit_arr[143:263]),
        'shiptype': ShipType(get_int_from_data(263, 271)),
        'to_bow': get_int_from_data(271, 280),
        'to_stern': get_int_from_data(280, 289),
        'to_port': get_int_from_data(289, 295),
        'to_starboard': get_int_from_data(295, 301),
        'epfd': EpfdType(get_int_from_data(301, 305)),
        'raim': bit_arr[305],
        'dte': bit_arr[306],
        'assigned': bit_arr[307],
    }


def decode_msg_20(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Data Link Management Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_20_data_link_management_message
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(8, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),

        'offset1': get_int_from_data(40, 52),
        'number1': get_int_from_data(52, 56),
        'timeout1': get_int_from_data(56, 59),
        'increment1': get_int_from_data(59, 70),

        'offset2': get_int_from_data(70, 82),
        'number2': get_int_from_data(82, 86),
        'timeout2': get_int_from_data(86, 89),
        'increment2': get_int_from_data(89, 100),

        'offset3': get_int_from_data(100, 112),
        'number3': get_int_from_data(112, 116),
        'timeout3': get_int_from_data(116, 119),
        'increment3': get_int_from_data(110, 130),

        'offset4': get_int_from_data(130, 142),
        'number4': get_int_from_data(142, 146),
        'timeout4': get_int_from_data(146, 149),
        'increment4': get_int_from_data(149, 160),
    }


def decode_msg_21(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Aid-to-Navigation Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_21_aid_to_navigation_report
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(8, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),

        'aid_type': NavAid(get_int_from_data(38, 43)),
        'name': encode_bin_as_ascii6(bit_arr[43:163]),
        'accuracy': bit_arr[163],

        'lon': get_int_from_data(164, 192, signed=True) / 600000.0,
        'lat': get_int_from_data(192, 219, signed=True) / 600000.0,

        'to_bow': get_int_from_data(219, 228),
        'to_stern': get_int_from_data(228, 237),
        'to_port': get_int_from_data(237, 243),
        'to_starboard': get_int_from_data(243, 249),

        'epfd': EpfdType(get_int_from_data(249, 253)),
        'second': get_int_from_data(253, 259),
        'off_position': bit_arr[259],
        'regional': get_int_from_data(260, 268),
        'raim': bit_arr[268],
        'virtual_aid': bit_arr[269],
        'assigned': bit_arr[270],
        'name_extension': encode_bin_as_ascii6(bit_arr[272:]),
    }


def decode_msg_22(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Channel Management
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_22_channel_management
    """
    get_int_from_data = partial(get_int, bit_arr)
    data = {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(8, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),

        'channel_a': get_int_from_data(40, 52),
        'channel_b': get_int_from_data(52, 64),
        'txrx': get_int_from_data(64, 68),
        'power': bit_arr[68],
        'addressed': bit_arr[139],
        'band_a': bit_arr[140],
        'band_b': bit_arr[141],
        'zonesize': get_int_from_data(142, 145),
    }

    # Broadcast
    d: Dict[str, Any] = {}
    if data['addressed']:
        d = {
            'dest1': get_mmsi(bit_arr, 69, 99),
            'dest2': get_mmsi(bit_arr, 104, 134),
        }
    # Addressed
    else:
        d = {
            'ne_lon': get_int_from_data(69, 87, signed=True) * 0.1,
            'ne_lat': get_int_from_data(87, 104, signed=True) * 0.1,
            'sw_lon': get_int_from_data(104, 122, signed=True) * 0.1,
            'sw_lat': get_int_from_data(122, 139, signed=True) * 0.1,
        }

    data.update(d)
    return data


def decode_msg_23(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Group Assignment Command
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_23_group_assignment_command
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(8, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),

        'ne_lon': get_int_from_data(40, 58, signed=True) * 0.1,
        'ne_lat': get_int_from_data(58, 75, signed=True) * 0.1,
        'sw_lon': get_int_from_data(75, 93, signed=True) * 0.1,
        'sw_lat': get_int_from_data(93, 110, signed=True) * 0.1,

        'station_type': StationType(get_int_from_data(110, 114)),
        'ship_type': ShipType(get_int_from_data(114, 122)),
        'txrx': TransmitMode(get_int_from_data(144, 146)),
        'interval': StationIntervals(get_int_from_data(146, 150)),
        'quiet': get_int_from_data(150, 154),
    }


def decode_msg_24(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Static Data Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_24_static_data_report
    """
    get_int_from_data = partial(get_int, bit_arr)
    data = {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(8, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),
        'partno': get_int_from_data(38, 40)
    }

    d: Dict[str, Any]
    if not data['partno']:
        # Part A
        d = {
            'shipname': encode_bin_as_ascii6(bit_arr[40: 160])
        }
    else:
        # Part B
        d = {
            'shiptype': ShipType(get_int_from_data(40, 48)),
            'vendorid': encode_bin_as_ascii6(bit_arr[48: 66]),
            'model': get_int_from_data(66, 70),
            'serial': get_int_from_data(70, 90),
            'callsign': encode_bin_as_ascii6(bit_arr[90: 132]),
            'to_bow': get_int_from_data(132, 141),
            'to_stern': get_int_from_data(141, 150),
            'to_port': get_int_from_data(150, 156),
            'to_starboard': get_int_from_data(156, 162),
            'mothership_mmsi': get_mmsi(bit_arr, 132, 162)
        }
    data.update(d)
    return data


def decode_msg_25(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Single Slot Binary Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_25_single_slot_binary_message

    NOTE: This message type is quite uncommon and
    I was not able find any real world occurrence of the type.
    Also documentation seems to vary. Use with caution.
    """
    get_int_from_data = partial(get_int, bit_arr)
    data: Dict[str, Any] = {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(8, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),

        'addressed': bit_arr[38],
        'structured': bit_arr[39],
    }

    d: Dict[str, Any]
    if data['addressed']:
        d = {
            'dest_mmsi': get_mmsi(bit_arr, 40, 70),
        }
        data.update(d)

    lo_ix = 40 if data['addressed'] else 70
    hi_ix = lo_ix + 16

    if data['structured']:
        d = {
            'app_id': get_int_from_data(lo_ix, hi_ix),
            'data': bit_arr[hi_ix:].to01()
        }
    else:
        d = {
            'data': bit_arr[lo_ix:].to01()
        }
    data.update(d)
    return data


def decode_msg_26(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Multiple Slot Binary Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_26_multiple_slot_binary_message

    NOTE: This message type is quite uncommon and
    I was not able find any real world occurrence of the type.
    Also documentation seems to vary. Use with caution.
    """
    get_int_from_data = partial(get_int, bit_arr)
    radio_status_offset = len(bit_arr) - 20

    data = {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(8, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),

        'addressed': bit_arr[38],
        'structured': bit_arr[39],
        'radio': get_int_from_data(radio_status_offset, len(bit_arr))
    }

    d: Dict[str, Any]
    if data['addressed']:
        d = {
            'dest_mmsi': get_mmsi(bit_arr, 40, 70),
        }
        data.update(d)

    lo_ix = 40 if data['addressed'] else 70
    hi_ix = lo_ix + 16

    if data['structured']:
        d = {
            'app_id': get_int_from_data(lo_ix, hi_ix),
            'data': bit_arr[hi_ix:radio_status_offset].to01()
        }
    else:
        d = {
            'data': bit_arr[lo_ix:radio_status_offset].to01()
        }

    data.update(d)
    return data


def decode_msg_27(bit_arr: bitarray.bitarray) -> Dict[str, Any]:
    """
    Long Range AIS Broadcast message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_27_long_range_ais_broadcast_message
    """
    get_int_from_data = partial(get_int, bit_arr)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(8, 8),
        'mmsi': get_mmsi(bit_arr, 8, 38),

        'accuracy': bit_arr[38],
        'raim': bit_arr[39],
        'status': NavigationStatus(get_int_from_data(40, 44)),
        'lon': get_int_from_data(44, 62, signed=True) / 600.0,
        'lat': get_int_from_data(62, 79, signed=True) / 600.0,
        'speed': get_int_from_data(79, 85),
        'course': get_int_from_data(85, 94),
        'gnss': bit_arr[94],
    }


# Decoding Lookup Table
DECODE_MSG = [
    decode_msg_1,  # there are messages with a zero (0) as an id. these seem to be the same as type 1 messages
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
    decode_msg_24,
    decode_msg_25,
    decode_msg_26,
    decode_msg_27,
]


def _decode(msg: "messages.NMEAMessage") -> Dict[str, Any]:
    """
    Decodes a given NMEA message.
    """
    try:
        return DECODE_MSG[msg.ais_id](msg.bit_array)
    except IndexError as e:
        raise UnknownMessageException(f"The message {msg} is not currently supported!") from e


def decode(msg: "messages.NMEAMessage") -> Dict[str, Any]:
    """
    Decodes a given message.

    @param msg: A object of type NMEAMessage to decode
    """
    return _decode(msg)


def decode_raw(msg: Union[str, bytes]) -> Dict[str, Any]:
    """
    Decode single message.
    @param msg: A AIS message, that can be either bytes or str (UTF-8) encoded.
    @return: A dictionary of the decoded key-value pairs.
    """
    if isinstance(msg, bytes):
        return decode(messages.NMEAMessage(msg))
    elif isinstance(msg, str):
        return decode(messages.NMEAMessage.from_string(msg))
    else:
        raise ValueError(f"msg must be of type 'str' or 'bytes', but was '{type(msg)}'")

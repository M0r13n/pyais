from .constants import *
from .util import *
from functools import partial
from typing import Sequence

LAST = None


class NMEAMessage(object):
    __slots__ = (
        'raw',
        'talker',
        'msg_type',
        'count',
        'index',
        'seq_id',
        'channel',
        'data',
        'checksum',
        'bit_array'
    )

    def __init__(self, raw: bytes):
        # Set all values to None initially
        [setattr(self, name, None) for name in self.__slots__]

        # Store raw data
        self.raw = raw

        # An AIS NMEA message consists of seven, comma separated parts
        values = raw.split(b",")

        # Either $ or ! is valid
        start_char = values[0][0]

        # Give up silently
        if start_char not in (b"$", b"!"):
            return

        # A NMEA message can't have more than 82 characters in total
        if len(raw) > 82:
            raise ValueError("Message too long")

        # Unpack NMEA message parts
        (
            head,
            count,
            index,
            seq_id,
            channel,
            data,
            checksum
        ) = values

        # The talker is identified by the next 2 characters
        self.talker = head[1:3]

        # The type of message is then identified by the next 3 characters
        self.msg_type = head[3:]

        # Store other important parts
        self.count = count
        self.index = index
        self.seq_id = seq_id
        self.channel = channel
        self.data = data
        self.checksum = checksum

        # Verify if the checksum is correct
        assert self.is_valid

        # Finally decode the payload into a bitarray
        self.bit_array = decode_into_bit_array(self.data)

    def __str__(self):
        return str(self.raw)

    @classmethod
    def assemble_from_iterable(cls, messages: Sequence):
        raw = b''.join(messages)
        return cls(raw)

    @property
    def is_valid(self) -> bool:
        return self.checksum == compute_checksum(self.raw)

    @property
    def is_single(self) -> bool:
        return not self.seq_id and self.index == self.count == 1

    @property
    def is_multi(self) -> bool:
        return not self.is_single


def decode_msg_1(bit_arr):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    get_int_from_data = partial(get_int, bit_arr)
    status = get_int_from_data(38, 42)
    maneuver = get_int_from_data(143, 145)
    return {
        'type': get_int_from_data(0, 6),
        'repeat': get_int_from_data(6, 8),
        'mmsi': get_int_from_data(8, 38),
        'status': (status, NAVIGATION_STATUS[status]),
        'turn': get_int_from_data(42, 50, signed=True),
        'speed': get_int_from_data(50, 60),
        'accuracy': bit_arr[60],
        'lon': get_int_from_data(61, 89, signed=True) / 600000.0,
        'lat': get_int_from_data(89, 116, signed=True) / 600000.0,
        'course': get_int_from_data(116, 128) * 0.1,
        'heading': get_int_from_data(128, 137),
        'second': get_int_from_data(137, 143),
        'maneuver': (maneuver, MANEUVER_INDICATOR[maneuver]),
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
    epfd = get_int_from_data(134, 138)
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
        'epfd': (epfd, EPFD_TYPE.get(epfd, NULL)),
        'raim': bit_arr[148],
        'radio': get_int_from_data(148, len(bit_arr)),
    }


def decode_msg_5(bit_arr):
    get_int_from_data = partial(get_int, bit_arr)
    epfd = get_int_from_data(270, 274)
    ship_type = get_int_from_data(66, 72)
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
        'epfd': (epfd, EPFD_TYPE.get(epfd, NULL)),
        'month': get_int_from_data(274, 278),
        'day': get_int_from_data(278, 283),
        'hour': get_int_from_data(283, 288),
        'minute': get_int_from_data(288, 294),
        'draught': get_int_from_data(294, 302) / 10.0,
        'destination': encode_bin_as_ascii6(bit_arr[302::])
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
    """
    Decodes an AIS message. This includes checksum validation and sentencing.
    This method requires the full raw AIS message encoded in ASCII or Unicode.
    :param msg: AIS message encoded in ASCII or Unicode
    :return: A dictionary containing the decoded information or None if an error occurs
    """
    m_typ, sentence_total_count, cur_sentence_num, seq_id, channel, data, chcksum = msg.split(b',')
    sentence_total_count = int(sentence_total_count.decode('ascii'))
    cur_sentence_num = int(cur_sentence_num.decode('ascii'))

    # Validate checksum
    expected = int(chcksum[2:].decode('ascii'), 16)
    actual = compute_checksum(msg)
    if expected != actual:
        print(f"{ANSI_RED}Invalid Checksum {actual} != {expected}; dropping message!{ANSI_RESET}")
        return None

    # Assemble multiline messages
    if sentence_total_count != 1:
        global LAST
        if LAST is None and cur_sentence_num != 1:
            print(f"{ANSI_RED}Something is out of order here..{ANSI_RESET}")
            return None

        elif sentence_total_count != cur_sentence_num:
            LAST = data if not LAST else LAST + data
            return None

        data = LAST + data
        LAST = ''

    decoded_data = decode_into_bit_array(data)
    msg_type = get_int(decoded_data, 0, 6)

    if 0 < msg_type < 25:
        return DECODE_MSG[msg_type](decoded_data)

    return None

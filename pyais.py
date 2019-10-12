"""
Decoding AIS messages in Python

General:
----------------------------------------------------

This module contains functions to decode and parse Automatic
Identification System (AIS) serial messages.

Each message has it's own, unique form and thus is treated individually.

Incoming data is converted from normal 8-bit ASCII into a 6-bit binary string.
Each binary string is then decoded according to it's message id.
Decoding is performed by a function of the form decode_msg_XX(bit_string),
where XX is the message id.

Decoded data is returned as a dictionary. Depending on what kind of data is being decoded,
additional context will be added. Such entries will not just contain an single value,
but rather a tuple of values. E.g:

{
'type': 1, # single value without additional context
...
'status': (0, 'Under way using engine'), # tuple of value and context
...
}

Performance considerations:
----------------------------------------------------

Even though performance is not my primary concern, the code shouldn't be too slow.
I tried a few different straight forward approaches for decoding the messages
and compared their performance:

Using native python strings and converting each substring into an integer:
    -> Decoding #8000 messages takes 0.80 seconds

Using bitstring's BitArray and slicing:
    -> Decoding #8000 AIS messages takes 2.5 seconds

Using the bitarray module:
    -> because their is not native to_int method, the code gets utterly cluttered


Note:
----------------------------------------------------
This module is a private project and does not claim to be complete.
Nor has it been designed to be extremely fast or memory efficient.
My primary focus is on readability and maintainability.

The terms message id and message type are used interchangeably and mean the same.

"""

import socket
from math import ceil
from bitstring import BitArray

# Keywords
UNDEFINED = 'Undefined'
RESERVED = 'Reserved'
NULL = 'N/A'
ANSI_RED = '\x1b[31m'
ANSI_RESET = '\x1b[0m'

# Global Variables
LAST = None

# Constants
NAVIGATION_STATUS = {
    0: 'Under way using engine',
    1: 'At anchor',
    2: 'Not under command',
    3: 'Restricted manoeuverability',
    4: 'Constrained by her draught',
    5: 'Moored',
    6: 'Aground',
    7: 'Engaged in Fishing',
    8: 'Under way sailing',
    9: 'Reserved',
    10: 'Reserved',
    11: 'Reserved',
    12: 'Reserved',
    13: 'Reserved',
    14: 'AIS-SART is active',
    15: 'Undefined',
}

MANEUVER_INDICATOR = {
    0: 'Not available',
    1: 'No special maneuver',
    2: 'Special maneuver'
}

EPFD_TYPE = {
    0: 'Undefined',
    1: 'GPS',
    2: 'GLONASS',
    3: 'GPS/GLONASS',
    4: 'Loran-C',
    5: 'Chayka',
    6: 'Integrated navigation system',
    7: 'Surveyed',
    8: 'Galileo',
    15: 'Undefined'
}

SHIP_TYPE = {
    0: 'Not available',
    20: 'Wing in ground (WIG)',
    21: 'Wing in ground (WIG), Hazardous category A',
    22: 'Wing in ground (WIG), Hazardous category B',
    23: 'Wing in ground (WIG), Hazardous category C',
    24: 'Wing in ground (WIG), Hazardous category D',
    25: 'WIG Reserved',
    26: 'WIG Reserved',
    27: 'WIG Reserved',
    28: 'WIG Reserved',
    29: 'WIG Reserved',
    30: 'Fishing',
    31: 'Towing',
    32: 'Towing,length exceeds 200m or breadth exceeds 25m',
    33: 'Dredging or underwater ops',
    34: 'Diving ops',
    35: 'Military ops',
    36: 'Sailing',
    37: 'Pleasure Craft',
    38: 'Reserved',
    39: 'Reserved',
    40: 'High speed craft (HSC)',
    41: 'High speed craft (HSC), Hazardous category A',
    42: 'High speed craft (HSC), Hazardous category B',
    43: 'High speed craft (HSC), Hazardous category C',
    44: 'High speed craft (HSC), Hazardous category D',
    45: 'High speed craft (HSC), Reserved',
    46: 'High speed craft (HSC), Reserved',
    47: 'High speed craft (HSC), Reserved',
    48: 'High speed craft (HSC), Reserved',
    49: 'High speed craft (HSC), No additional information',
    50: 'Pilot Vessel',
    51: 'Search and Rescue vessel',
    52: 'Tug',
    53: 'Port Tender',
    54: 'Anti-pollution equipment',
    55: 'Law Enforcement',
    56: 'Spare - Local Vessel',
    57: 'Spare - Local Vessel',
    58: 'Medical Transport',
    59: 'Noncombatant ship according to RR Resolution No. 18',
    60: 'Passenger',
    61: 'Passenger, Hazardous category A',
    62: 'Passenger, Hazardous category B',
    63: 'Passenger, Hazardous category C',
    64: 'Passenger, Hazardous category D',
    65: 'Passenger, Reserved',
    66: 'Passenger, Reserved',
    67: 'Passenger, Reserved',
    68: 'Passenger, Reserved',
    69: 'Passenger, No additional information',
    70: 'Cargo',
    71: 'Cargo, Hazardous category A',
    72: 'Cargo, Hazardous category B',
    73: 'Cargo, Hazardous category C',
    74: 'Cargo, Hazardous category D',
    75: 'Cargo, Reserved',
    76: 'Cargo, Reserved',
    77: 'Cargo, Reserved',
    78: 'Cargo, Reserved',
    79: 'Cargo, No additional information',
    80: 'Tanker',
    81: 'Tanker, Hazardous category A',
    82: 'Tanker, Hazardous category B',
    83: 'Tanker, Hazardous category C',
    84: 'Tanker, Hazardous category D',
    85: 'Tanker, Reserved ',
    86: 'Tanker, Reserved ',
    87: 'Tanker, Reserved ',
    88: 'Tanker, Reserved ',
    89: 'Tanker, No additional information',
    90: 'Other Type',
    91: 'Other Type, Hazardous category A',
    92: 'Other Type, Hazardous category B',
    93: 'Other Type, Hazardous category C',
    94: 'Other Type, Hazardous category D',
    95: 'Other Type, Reserved',
    96: 'Other Type, Reserved',
    97: 'Other Type, Reserved',
    98: 'Other Type, Reserved',
    99: 'Other Type, No additional information'
}

DAC_FID = {
    '1-12': 'Dangerous cargo indication',
    '1-14': 'Tidal window',
    '1-16': 'Number of persons on board',
    '1-18': 'Clearance time to enter port',
    '1-20': 'Berthing data (addressed)',
    '1-23': 'Area notice (addressed)',
    '1-25': 'Dangerous Cargo indication',
    '1-28': 'Route info addressed',
    '1-30': 'Text description addressed',
    '1-32': 'Tidal Window',
    '200-21': 'ETA at lock/bridge/terminal',
    '200-22': 'RTA at lock/bridge/terminal',
    '200-55': 'Number of persons on board',
    '235-10': 'AtoN monitoring data (UK)',
    '250-10': 'AtoN monitoring data (ROI)',
}


def split_str(string, chunk_size=6):
    """
    Split a string into equal sized chunks and return these as a list.
    The last substring may not have chunk_size chars,
    if len(string) is not a multiple of chunk_size.

    :param string: arbitrary string
    :param chunk_size: chunk_size
    :return: a list of substrings of chunk_size
    """
    chunks = ceil(len(string) / chunk_size)
    lst = [string[i * chunk_size:(i + 1) * chunk_size] for i in range(chunks)]
    return lst


def ascii6_to_bin(data) -> str:
    """
    Convert ASCII into 6 bit binary.
    :param data: ASCII text
    :return: a binary string of 0's and 1's, e.g. 011100 011111 100001
    """
    binary_string = ''

    for c in data:
        c = ord(c)

        if c < 0x30 or c > 0x77 or 0x57 < c < 0x60:
            print("Invalid char")

        else:
            if c < 0x60:
                c = (c - 0x30) & 0x3F
            else:
                c = (c - 0x38) & 0x3F
            binary_string += f'{c:06b}'

    return binary_string


def bin_to_ascii6(data):
    """
    Encode binary data as 6 bit ASCII.
    :param data: binary string
    :return: ASCII String
    """
    string = ""
    for c in split_str(data):

        c = int(c, 2)

        if c < 0x20:
            c += 0x40
        if c == 64:
            break

        string += chr(c)

    return string


def signed(bit_vector):
    """
    Convert bit sequence to signed integer
    :param bit_vector: bit sequence
    :return: singed int
    """
    b = BitArray(bin=bit_vector)
    return b.int


def to_int(bit_string, base=2):
    """
    Convert a sequence of bits into an integer.
    :param bit_string: Sequence of zeros and ones
    :param base: The base
    :return: An integer or 0 if no valid bit_string was provided
    """
    if bit_string:
        return int(bit_string, base)
    return 0


def checksum(msg):
    """
    Compute the checksum of a given message
    :param msg: message
    :return: hex
    """
    c_sum = 0
    for c in msg[1::]:
        if c == '*':
            break
        c_sum ^= ord(c)

    return c_sum


def decode_msg_1(bit_vector):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    status = to_int(bit_vector[38:42], 2)
    maneuver = to_int(bit_vector[143:145], 2)
    return {
        'type': to_int(bit_vector[0:6], 2),
        'repeat': to_int(bit_vector[6:8], 2),
        'mmsi': to_int(bit_vector[8:38], 2),
        'status': (status, NAVIGATION_STATUS.get(status, NULL)),
        'turn': signed(bit_vector[42:50]),
        'speed': to_int(bit_vector[50:60], 2),
        'accuracy': to_int(bit_vector[60], 2),
        'lon': signed(bit_vector[61:89]) / 600000.0,
        'lat': signed(bit_vector[89:116]) / 600000.0,
        'course': to_int(bit_vector[116:128], 2) * 0.1,
        'heading': to_int(bit_vector[128:137], 2),
        'second': to_int(bit_vector[137:143], 2),
        'maneuver': (maneuver, MANEUVER_INDICATOR.get(maneuver, NULL)),
        'raim': bool(to_int(bit_vector[148], 2)),
        'radio': to_int(bit_vector[149::], 2)
    }


def decode_msg_2(bit_vector):
    """AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    return decode_msg_1(bit_vector)


def decode_msg_3(bit_vector):
    """
    AIS Vessel position report using ITDMA (Incremental Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    return decode_msg_1(bit_vector)


def decode_msg_4(bit_vector):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_4_base_station_report
    """
    epfd = to_int(bit_vector[134:138], 2)
    return {
        'type': to_int(bit_vector[0:6], 2),
        'repeat': to_int(bit_vector[6:8], 2),
        'mmsi': to_int(bit_vector[8:38], 2),
        'year': to_int(bit_vector[38:52], 2),
        'month': to_int(bit_vector[52:56]),
        'day': to_int(bit_vector[56:61], 2),
        'hour': to_int(bit_vector[61:66], 2),
        'minute': to_int(bit_vector[66:72], 2),
        'second': to_int(bit_vector[72:78], 2),
        'accuracy': bool(to_int(bit_vector[78], 2)),
        'lon': signed(bit_vector[66:72]) / 600000.0,
        'lat': signed(bit_vector[66:72]) / 600000.0,
        'epfd': (epfd, EPFD_TYPE.get(epfd, NULL)),
        'raim': bool(to_int(bit_vector[148], 2)),
        'radio': to_int(bit_vector[148::], 2)
    }


def decode_msg_5(bit_vector):
    epfd = to_int(bit_vector[270:274], 2)
    ship_type = to_int(bit_vector[66:72], 2)
    return {
        'type': to_int(bit_vector[0:6], 2),
        'repeat': to_int(bit_vector[6:8], 2),
        'mmsi': to_int(bit_vector[8:38], 2),
        'ais_version': to_int(bit_vector[38:40], 2),
        'imo': to_int(bit_vector[40:70], 2),
        'callsign': bin_to_ascii6(bit_vector[70:112]),
        'shipname': bin_to_ascii6(bit_vector[112:232]),
        'shiptype': (ship_type, SHIP_TYPE.get(ship_type, NULL)),
        'to_bow': to_int(bit_vector[240:249], 2),
        'to_stern': to_int(bit_vector[249:258], 2),
        'to_port': to_int(bit_vector[258:264], 2),
        'to_starboard': to_int(bit_vector[264:270], 2),
        'epfd': (epfd, EPFD_TYPE.get(epfd, NULL)),
        'month': to_int(bit_vector[274:278], 2),
        'day': to_int(bit_vector[278:283], 2),
        'hour': to_int(bit_vector[283:288], 2),
        'minute': to_int(bit_vector[288:294], 2),
        'draught': to_int(bit_vector[294:302], 2) / 10.0,
        'destination': bin_to_ascii6(bit_vector[302::])
    }


def decode_msg_6(bit_vector):
    pass


def decode_msg_7(bit_vector):
    pass


def decode_msg_8(bit_vector):
    """
    Binary Broadcast Message
    TODO: data needs to be interpreted depending DAC-FID
    """
    return {
        'type': to_int(bit_vector[0:6], 2),
        'repeat': to_int(bit_vector[6:8], 2),
        'mmsi': to_int(bit_vector[8:38], 2),
        'dac': to_int(bit_vector[40:50], 2),
        'fid': to_int(bit_vector[50:56], 2),
        'data': to_int(bit_vector[56::], 2),
    }


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


def decode_msg_18(bit_vector):
    """
    Standard Class B CS Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_18_standard_class_b_cs_position_report
    """
    return {
        'type': to_int(bit_vector[0:6], 2),
        'repeat': to_int(bit_vector[6:8], 2),
        'mmsi': to_int(bit_vector[8:38], 2),
        'speed': to_int(bit_vector[46:55], 2),
        'accuracy': bool(to_int(bit_vector[55], 2)),
        'lon': signed(bit_vector[56:85]) / 600000.0,
        'lat': signed(bit_vector[85:112]) / 600000.0,
        'course': to_int(bit_vector[112:124], 2) * 0.1,
        'heading': to_int(bit_vector[124:133], 2),
        'second': to_int(bit_vector[133:139], 2),
        'regional': to_int(bit_vector[139:141], 2),
        'cs': bool(to_int(bit_vector[141])),
        'display': bool(to_int(bit_vector[142])),
        'dsc': bool(to_int(bit_vector[143])),
        'band': bool(to_int(bit_vector[144])),
        'msg22': bool(to_int(bit_vector[145])),
        'assigned': bool(to_int(bit_vector[146])),
        'raim': bool(to_int(bit_vector[147])),
        'radio': to_int(bit_vector[148::]),
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
    m_typ, sentence_total_count, cur_sentence_num, seq_id, channel, data, chcksum = msg.split(',')

    # Validate checksum
    if checksum(msg) != int("0x" + chcksum[2::], 16):
        print(f"{ANSI_RED}Invalid Checksum dropping packet!{ANSI_RESET}")
        return None

    # Assemble multiline messages
    if sentence_total_count != '1':
        global LAST
        if LAST is None and cur_sentence_num != '1':
            print(f"{ANSI_RED}Something is out of order here..{ANSI_RESET}")
            return None

        elif sentence_total_count != cur_sentence_num:
            LAST = data if not LAST else LAST + data
            return None

        data = LAST + data
        LAST = ''

    decoded_data = ascii6_to_bin(data)
    msg_type = int(decoded_data[0:6], 2)

    if 0 < msg_type < 25:
        print(msg_type)  # 21, 24, 8
        return DECODE_MSG[msg_type](decoded_data)

    return None


#  ################################# TEST DRIVER #################################


def ais_stream(url="ais.exploratorium.edu", port=80):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((url, port))
    while True:
        for msg in s.recv(4096).decode("utf-8").splitlines():
            yield msg


def test():
    MESSAGES = [
        "!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C",
        "!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05",
        "!AIVDM,1,1,,A,15NJQiPOl=G?m:bE`Gpt<aun00S8,0*56",
        "!AIVDM,1,1,,B,15NPOOPP00o?bIjE`UEv4?wF2HIU,0*31",
        "!AIVDM,1,1,,A,35NVm2gP00o@5k:EbbPJnwwN25e3,0*35",
        "!AIVDM,1,1,,A,B52KlJP00=l4be5ItJ6r3wVUWP06,0*7C",
        "!AIVDM,2,1,1,B,53ku:202=kul=4TS@00<tq@V0<uE84LD00000017R@sEE6TE0GUDk1hP,0*57",
        "!AIVDM,2,1,2,B,55Mwm;P00001L@?;SKE8uT4j0lDh8uE8pD00000l0`A276S<07gUDp3Q,0*0D"
    ]

    import timeit
    import random

    def test():
        decode(MESSAGES[random.randint(0, 7)])

    iterations = 8000
    elapsed_time = timeit.timeit(test, number=iterations)
    print(f"Decoding #{iterations} takes {elapsed_time} seconds")


def main():
    test()

    for msg in ais_stream():
        if msg and msg[0] == "!":
            print(decode(msg))
        else:
            print("Unparsed msg: " + msg)


if __name__ == "__main__":
    main()

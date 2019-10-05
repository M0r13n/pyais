"""
Decoding AIS messages in Python

Work in Progress
"""

import socket
from math import ceil
from bitstring import BitArray


def catch_error(*exceptions):
    def checking(f):
        def checked(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exceptions as ex:
                print(f"\x1b[31mCould not parse AIS packet, because: {str(ex)}!\x1b[0m")

        return checked

    return checking


def decode_ascii6(data):
    """
    Decode AIS_ASCII_6 encoded data and convert it into binary.
    :param data: ASI_ASCII_6 encoded data
    :return: a binary string of 0's and 1's, e.g. 011100 011111 100001
    """
    binary_string = ''

    for c in data:
        c = ord(c) - 48
        if c > 40:
            c -= 8
        binary_string += '{0:06b}'.format(c)

    return binary_string


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


def ascii6(data, ignore_tailing_fillers=True):
    """
    Decode bit sequence into ASCII6.
    :param data: ASI_ASCII_6 encoded data
    :return: ASCII String
    """
    string = ""
    for c in split_str(data):
        c = int(c, 2)
        if c < 32:
            c += 64
        c = chr(c)

        if ignore_tailing_fillers and c == '@':
            return string
        string += c

    return string


def signed(bit_vector):
    """
    convert bit sequence to signed integer
    :param bit_vector: bit sequence
    :return: singed int
    """
    b = BitArray(bin=bit_vector)
    return b.int


def to_int(bit_string, base=2):
    """
    Convert a sequence of bits to int while ignoring empty strings
    :param bit_string: sequence of zeros and ones
    :param base: the base
    :return: a integer or None if no valid bit_string was provided
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
    calc = False
    c_sum = 0
    for c in msg:
        if c == '$' or c == '!':
            calc = True
            continue

        if c == '*':
            break

        if calc:
            c_sum ^= ord(c)
    return c_sum


def decode_msg_1(bit_vector):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    if (len(bit_vector)) != 168:
        print(bit_vector)
    return {
        'type': to_int(bit_vector[0:6], 2),
        'repeat': to_int(bit_vector[6:8], 2),
        'mmsi': to_int(bit_vector[8:38], 2),
        'status': to_int(bit_vector[38:42], 2),
        'turn': signed(bit_vector[42:50]),
        'speed': to_int(bit_vector[50:60], 2),
        'accuracy': to_int(bit_vector[60], 2),
        'lon': signed(bit_vector[61:89]) / 600000.0,
        'lat': signed(bit_vector[89:116]) / 600000.0,
        'course': to_int(bit_vector[116:128], 2) * 0.1,
        'heading': to_int(bit_vector[128:137], 2),
        'second': to_int(bit_vector[137:143], 2),
        'maneuver': to_int(bit_vector[143:145], 2),
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
        'epfd': to_int(bit_vector[134:138], 2),
        'raim': bool(to_int(bit_vector[148], 2)),
        'radio': to_int(bit_vector[148::], 2)
    }


def decode_msg_5(bit_vector):
    return {
        'type': to_int(bit_vector[0:6], 2),
        'repeat': to_int(bit_vector[6:8], 2),
        'mmsi': to_int(bit_vector[8:38], 2),
        'ais_version': to_int(bit_vector[38:40], 2),
        'imo': to_int(bit_vector[40:70], 2),
        'callsign': ascii6(bit_vector[70:112]),
        'shipname': ascii6(bit_vector[112:232]),
        'shiptype': to_int(bit_vector[66:72], 2),
        'to_bow': to_int(bit_vector[240:249], 2),
        'to_stern': to_int(bit_vector[249:258], 2),
        'to_port': to_int(bit_vector[258:264], 2),
        'to_starboard': to_int(bit_vector[264:270], 2),
        'epfd': to_int(bit_vector[270:274], 2),
        'month': to_int(bit_vector[274:278], 2),
        'day': to_int(bit_vector[278:283], 2),
        'hour': to_int(bit_vector[283:288], 2),
        'minute': to_int(bit_vector[288:294], 2),
        'draught': to_int(bit_vector[294:302], 2) / 10.0,
        'destination': ascii6(bit_vector[302::])
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


#  ################################# TEST DRIVER #################################


def ais_stream(url="ais.exploratorium.edu", port=80):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((url, port))
    while True:
        for msg in s.recv(4096).decode("utf-8").splitlines():
            yield msg


def main():
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

    for msg in ais_stream():
        if msg and msg[0] == "!":
            m_typ, n_sentences, sentence_num, seq_id, channel, data, chcksum = msg.split(',')
            decoded_data = decode_ascii6(data)
            msg_type = int(decoded_data[0:6], 2)

            if checksum(msg) != int("0x" + chcksum[2::], 16):
                print(f"\x1b[31mInvalid Checksum dropping packet!\x1b[0m")
                continue

            if 0 < msg_type < 25:
                print(DECODE_MSG[msg_type](decoded_data))


        else:
            print("Unparsed msg: " + msg)


if __name__ == "__main__":
    main()

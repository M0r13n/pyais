"""
Decoding AIS messages in Python

Work in Progress
"""

import socket
from math import ceil
from bitstring import BitArray


def decode_ascii6(data):
    """
    Decode AIS_ASCII_6 encoded data and convert it into binary.
    :param data: ASI_ASCII_& encoded data
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


def signed(bit_vector):
    """
    convert bit sequence to signed integer
    :param bit_vector: bit sequence
    :return: singed int
    """
    b = BitArray(bin=bit_vector)
    return b.int


def decode_msg_1(bit_vector):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: http://www.bosunsmate.org/ais/message1.php
    """
    return {
        'msg_type': int(bit_vector[0:6], 2),
        'repeat_indicator': int(bit_vector[6:8], 2),
        'user_id': int(bit_vector[8:38], 2),
        'nav_status': int(bit_vector[38:42], 2),
        'rot': int(bit_vector[42:50], 2),
        'sog': int(bit_vector[50:60], 2),
        'pos_accuracy': int(bit_vector[60:61], 2),
        'longitude': signed(bit_vector[61:89]) / 600000.0,
        'latitude': signed(bit_vector[89:116]) / 600000.0,
        'cog': int(bit_vector[116:128], 2),
        'hdg': int(bit_vector[128:137], 2),
        'utc': int(bit_vector[137:143], 2),
        'raim': int(bit_vector[148:149], 2),
        'sotdma_sync_state': int(bit_vector[149:151], 2),
        'sotdma_slot_timeout': int(bit_vector[151:154], 2),
        'sotdma_sync_offset': int(bit_vector[154:168], 2),
    }


def decode_msg_2(bit_vector):
    pass


def decode_msg_3(bit_vector):
    pass


def decode_msg_4(bit_vector):
    pass


def decode_msg_5(bit_vector):
    pass


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
    pass


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
            m_typ, n_sentences, sentence_num, seq_id, channel, data, checksum = msg.split(',')
            decoded_data = decode_ascii6(data)
            msg_type = int(decoded_data[0:6], 2)

            if 0 < msg_type < 25:
                print(DECODE_MSG[msg_type](decoded_data))


        else:
            print("Unparsed msg: " + msg)


if __name__ == "__main__":
    main()

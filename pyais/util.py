from bitstring import BitArray
from math import ceil


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

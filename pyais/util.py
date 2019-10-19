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


def decode_into_bin_str(data) -> str:
    """
    Decode AIS message into a binary string
    :param data: AIS message encoded with AIS-ASCII-6
    :return: a binary string of 0's and 1's, e.g. 011100 011111 100001
    """
    binary_string = ''

    for c in data:
        if c < 0x30 or c > 0x77 or 0x57 < c < 0x6:
            raise ValueError("Invalid character")

        c -= 0x30 if (c < 0x60) else 0x38
        c &= 0x3F
        binary_string += f'{c:06b}'

    return binary_string


def encode_bin_as_ascii6(data):
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


def decode_into_bytes(data):
    """
    Decode AIS message into a continuous block of bytes
    :param data: AIS message encoded with AIS-ASCII-6
    :return: An array of bytes

    Example:
    Let data be [63, 62, 61, 60]
    __111111 = 63
    __111110 = 62
    __111101 = 61
    __111100 = 60
    11111111 | 11101111 | 01111100
    """
    byte_arr = bytearray()

    for i, c in enumerate(data):
        if c < 0x30 or c > 0x77 or 0x57 < c < 0x6:
            raise ValueError("Invalid character")

        # Convert 8 bit binary to 6 bit binary
        c -= 0x30 if (c < 0x60) else 0x38
        c &= 0x3F

        # Only add the last 6 bits of each character
        if (i % 4) == 0:
            byte_arr.append(c << 2)

        elif (i % 4) == 1:
            byte_arr[-1] |= c >> 4
            byte_arr.append((c & 15) << 4)

        elif (i % 4) == 2:
            byte_arr[-1] |= c >> 2
            byte_arr.append((c & 3) << 6)

        elif (i % 4) == 3:
            byte_arr[-1] |= c

    return byte_arr


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

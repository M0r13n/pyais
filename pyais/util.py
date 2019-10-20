from bitarray import bitarray
from math import ceil
from functools import partial
from typing import Iterable

from_bytes = partial(int.from_bytes, byteorder="big")
from_bytes_signed = partial(int.from_bytes, byteorder="big", signed=True)


def split_str(string: str, chunk_size=6) -> Iterable[str]:
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


def decode_into_bit_array(data: bytes) -> bitarray:
    """
    Decodes a raw AIS message into a bitarray.
    :param data: Raw AIS message in bytes, as it is received from a TCP socket.
    :return:
    """
    bit_arr = bitarray()

    for i, c in enumerate(data):
        if c < 0x30 or c > 0x77 or 0x57 < c < 0x6:
            raise ValueError("Invalid character")

        # Convert 8 bit binary to 6 bit binary
        c -= 0x30 if (c < 0x60) else 0x38
        c &= 0x3F
        bit_arr += f'{c:06b}'

    return bit_arr


def encode_bin_as_ascii6(bit_arr: bitarray) -> str:
    """
    Encode binary data as 6 bit ASCII.
    :param bit_arr: array of bits
    :return: ASCII String
    """
    string = ""
    for c in split_str(bit_arr.to01()):
        c = int(c, 2)

        if c < 0x20:
            c += 0x40
        if c == 64:
            break

        string += chr(c)

    return string


def get_int(data: bitarray, ix_low, ix_high, signed=False) -> int:
    """
    Cast a subarray of a bitarray into an integer.
    The bitarray module adds tailing zeros when calling tobytes(), if the bitarray is not a multiple of 8.
    So those need to ne shifted away.
    :param data: some bitarray
    :param ix_low: the lower index of the sub-array
    :param ix_high: the upper index of the sub-array
    :param signed: True if the value should be interpreted as a signed integer
    :return: a normal integer (int)
    """
    shift = 8 - ((ix_high - ix_low) % 8)
    if shift == 8:
        shift = 0
    data = data[ix_low:ix_high]
    i = from_bytes_signed(data) if signed else from_bytes(data)
    return i >> shift

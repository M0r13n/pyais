from functools import partial
from typing import Sequence, Iterable

from bitarray import bitarray

from_bytes = partial(int.from_bytes, byteorder="big")
from_bytes_signed = partial(int.from_bytes, byteorder="big", signed=True)


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


def chunks(l: Sequence, n: int) -> Iterable:
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def encode_bin_as_ascii6(bit_arr: bitarray) -> str:
    """
    Encode binary data as 6 bit ASCII.
    :param bit_arr: array of bits
    :return: ASCII String
    """
    string = ""
    for c in chunks(bit_arr, 6):
        n = from_bytes(c.tobytes()) >> 2

        # Last entry may not have 6 bits
        if len(c) != 6:
            n >> (6 - len(c))

        if n < 0x20:
            n += 0x40

        # Break if there is an @
        if n == 64:
            break

        string += chr(n)

    return string.strip()


def get_int(data: bitarray, ix_low, ix_high, signed=False) -> int:
    """
    Cast a subarray of a bitarray into an integer.
    The bitarray module adds tailing zeros when calling tobytes(), if the bitarray is not a multiple of 8.
    So those need to be shifted away.
    :param data: some bitarray
    :param ix_low: the lower index of the sub-array
    :param ix_high: the upper index of the sub-array
    :param signed: True if the value should be interpreted as a signed integer
    :return: a normal integer (int)
    """
    shift = (8 - ((ix_high - ix_low) % 8)) % 8
    data = data[ix_low:ix_high]
    i = from_bytes_signed(data) if signed else from_bytes(data)
    return i >> shift

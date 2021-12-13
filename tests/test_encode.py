import struct
from pprint import pprint

import attr
import bitarray

from pyais import NMEAMessage
from pyais.util import encode_bin_as_ascii6, decode_into_bit_array, chunks, from_bytes

# https://gpsd.gitlab.io/gpsd/AIVDM.html#_aivdmaivdo_payload_armoring
PAYLOAD_ARMOR = {
    0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 10: ':',
    11: ';', 12: '<', 13: '=', 14: '>', 15: '?', 16: '@', 17: 'A', 18: 'B', 19: 'C', 20: 'D',
    21: 'E', 22: 'F', 23: 'G', 24: 'H', 25: 'I', 26: 'J', 27: 'K', 28: 'L', 29: 'M', 30: 'N',
    31: 'O', 32: 'P', 33: 'Q', 34: 'R', 35: 'S', 36: 'T', 37: 'U', 38: 'V', 39: 'W', 40: '`',
    41: 'a', 42: 'b', 43: 'c', 44: 'd', 45: 'e', 46: 'f', 47: 'g', 48: 'h', 49: 'i', 50: 'j',
    51: 'k', 52: 'l', 53: 'm', 54: 'n', 55: 'o', 56: 'p', 57: 'q', 58: 'r', 59: 's', 60: 't',
    61: 'u', 62: 'v', 63: 'w'
}

# https://gpsd.gitlab.io/gpsd/AIVDM.html#_ais_payload_data_types
SIX_BIT_ENCODING = {
    '@': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8, 'I': 9, 'J': 10,
    'K': 11, 'L': 12, 'M': 13, 'N': 14, 'O': 15, 'P': 16, 'Q': 17, 'R': 18, 'S': 19, 'T': 20,
    'U': 21, 'V': 22, 'W': 23, 'X': 24, 'Y': 25, 'Z': 26, '[': 27, '\\': 28, ']': 29, '^': 30,
    '_': 31, ' ': 32, '!': 33, '"': 34, '#': 35, '$': 36, '%': 37, '&': 38, '\'': 39, '(': 40,
    ')': 41, '*': 42, '+': 43, ',': 44, '-': 45, '.': 46, '/': 47, '0': 48, '1': 49, '2': 50,
    '3': 51, '4': 52, '5': 53, '6': 54, '7': 55, '8': 56, '9': 57, ':': 58, ';': 59, '<': 60,
    '=': 61, '>': 62, '?': 63
}


def to_six_bit(char: str) -> str:
    char = char.upper()
    try:
        return SIX_BIT_ENCODING[char]
    except KeyError:
        raise ValueError(f"received char '{char}' that cant be encoded")


def encode_ascii_6(bits: bitarray.bitarray):
    out = ""
    for chunk in chunks(bits, 6):
        num = from_bytes(chunk.tobytes()) >> 2
        armor = PAYLOAD_ARMOR[num]
        out += armor
    return out


def bit_field(width, d_type):
    return attr.ib(metadata={'width': width, 'd_type': d_type})


@attr.s(slots=True)
class MessageType1:
    msg_type = bit_field(6, int)
    repeat = bit_field(2, int)
    mmsi = bit_field(30, int)
    status = bit_field(4, int)
    turn = bit_field(8, int)
    speed = bit_field(10, int)
    accuracy = bit_field(1, int)
    lon = bit_field(28, int)
    lat = bit_field(27, int)
    course = bit_field(12, int)
    heading = bit_field(9, int)
    second = bit_field(6, int)
    maneuver = bit_field(2, int)
    spare = bit_field(3, int)
    raim = bit_field(1, int)
    radio = bit_field(19, int)

    def __attrs_post_init__(self):
        self.speed = int(self.speed * 10)
        self.lon = int(self.lon * 600000)
        self.lat = int(self.lat * 600000)

    @classmethod
    def fields(cls):
        return attr.fields(cls)

    def to_dict(self):
        return attr.asdict(self)


def test_encode_type_1():
    expected = b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C"
    nmea = NMEAMessage(expected).decode()

    del nmea.content['type']

    msg = MessageType1(1, **nmea.content, spare=0)

    out = bitarray.bitarray()
    for field in msg.fields():
        width = field.metadata['width']
        d_type = field.metadata['d_type']

        val = getattr(msg, field.name)

        val = d_type(val)

        val &= 0xffffffff

        bits = bitarray.bitarray(f"{val:0{width}b}")

        out += bits

    print(encode_ascii_6(out))

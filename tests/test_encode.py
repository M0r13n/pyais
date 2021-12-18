import math
from pprint import pprint

import attr
import bitarray

from pyais import NMEAMessage, decode_msg
from pyais.util import chunks, from_bytes, compute_checksum, decode_bin_as_ascii6, decode_into_bit_array

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
        encoding = SIX_BIT_ENCODING[char]
        return f"{encoding:06b}"
    except KeyError:
        raise ValueError(f"received char '{char}' that cant be encoded")


def encode_ascii_6(bits: bitarray.bitarray):
    out = ""
    for chunk in chunks(bits, 6):
        padding = 6 - len(chunk)
        num = from_bytes(chunk.tobytes()) >> 2
        if padding:
            num >> padding
        armor = PAYLOAD_ARMOR[num]
        out += armor
    return out, padding


def bit_field(width, d_type, converter=None, spare=False):
    return attr.ib(converter=converter, metadata={'width': width, 'd_type': d_type, 'spare': spare})


def to_bin(val, width):
    bits = bitarray.bitarray(endian='big')
    n_bits, mod = divmod(width, 8)
    if mod > 0:
        n_bits += 1

    bits.frombytes(val.to_bytes(n_bits, 'big', signed=True))
    return bits[8 - mod if mod else 0:]


def str_to_bin(val, width):
    out = ""

    for _ in range(int(width / 6) - len(val)):
        val += "@"

    for char in val:
        txt = to_six_bit(char)
        out += txt

    return out


@attr.s(slots=True)
class Payload:

    @classmethod
    def fields(cls):
        return attr.fields(cls)

    def to_bitarray(self):
        out = bitarray.bitarray()
        for field in self.fields():
            width = field.metadata['width']
            d_type = field.metadata['d_type']

            val = getattr(self, field.name)
            val = d_type(val)

            if d_type == int:
                bits = to_bin(val, width)
            elif d_type == str:
                bits = str_to_bin(val, width)
            else:
                raise ValueError()

            out += bits

        return out

    def encode(self):
        bit_arr = self.to_bitarray()
        return encode_ascii_6(bit_arr)


@attr.s(slots=True)
class MessageType1(Payload):
    msg_type = bit_field(6, int)
    repeat = bit_field(2, int)
    mmsi = bit_field(30, int)
    status = bit_field(4, int)
    turn = bit_field(8, int)
    speed = bit_field(10, int, converter=lambda v: v * 10.0)
    accuracy = bit_field(1, int)
    lon = bit_field(28, int, converter=lambda v: v * 600000.0)
    lat = bit_field(27, int, converter=lambda v: v * 600000.0)
    course = bit_field(12, int, converter=lambda v: v * 10.0)
    heading = bit_field(9, int)
    second = bit_field(6, int)
    maneuver = bit_field(2, int)
    spare = bit_field(3, int)
    raim = bit_field(1, int)
    radio = bit_field(19, int)

    @classmethod
    def create(cls, **kwargs):
        kwargs['msg_type'] = 1
        kwargs['spare'] = 0
        return cls(**kwargs)


@attr.s(slots=True)
class MessageType5(Payload):
    msg_type = bit_field(6, int)
    repeat = bit_field(2, int)
    mmsi = bit_field(30, int)
    ais_version = bit_field(2, int)
    imo = bit_field(30, int)  # 70
    callsign = bit_field(42, str)
    shipname = bit_field(120, str)
    shiptype = bit_field(8, int)
    to_bow = bit_field(9, int)
    to_stern = bit_field(9, int)
    to_port = bit_field(6, int)
    to_starboard = bit_field(6, int)
    epfd = bit_field(4, int)
    month = bit_field(4, int)
    day = bit_field(5, int)
    hour = bit_field(5, int)
    minute = bit_field(6, int)
    draught = bit_field(8, int, converter=lambda v: v * 10.0)
    destination = bit_field(120, str)
    dte = bit_field(1, int)
    spare = bit_field(1, int)

    @classmethod
    def create(cls, **kwargs):
        kwargs['msg_type'] = 5
        kwargs['spare'] = 0
        return cls(**kwargs)


def encode(payload, prefix="!", talker_id="AI", nmea_type="VDM", channel="A", seq_id=1):
    ais_type = payload.pop('type')

    if ais_type == 1:
        payload, padding = MessageType1.create(**payload).encode()
    elif ais_type == 5:
        payload, padding = MessageType5.create(**payload).encode()
    else:
        raise ValueError(ais_type)

    messages = []
    max_len = 61
    frag_cnt = math.ceil(len(payload) / max_len)

    if seq_id is None:
        seq_id = ''

    for i, chunk in enumerate(chunks(payload, max_len), start=1):
        tpl = "{}{}{},{},{},{},{},{},{}*{:02X}"
        dummy_message = tpl.format(prefix, talker_id, nmea_type, frag_cnt, i, seq_id, channel, chunk, padding, 0)
        checksum = compute_checksum(dummy_message)
        msg = tpl.format(prefix, talker_id, nmea_type, frag_cnt, i, seq_id, channel, chunk, padding, checksum)
        messages.append(msg)
    return messages


def test_encode_type_5():
    msg = NMEAMessage.assemble_from_iterable(messages=[
        NMEAMessage(b"!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C"),
        NMEAMessage(b"!AIVDM,2,2,1,A,88888888880,2*25")
    ]).decode()

    assert False


def test_encode_type_5_a():
    parts = [
        NMEAMessage(b"!AIVDM,2,1,1,B,53Jsir02=tfcTP7?C7@p5HTu>1@5E9E<0000001?H@OF:,0*23"),
        NMEAMessage(b"!AIVDM,2,2,1,B,6MU0ND1@QhP000000000000000,2*2A")
    ]
    msg = NMEAMessage.assemble_from_iterable(parts).decode()

    expected = msg.nmea.bit_array

    for part in encode(msg.content, channel="B"):
        print(part)



def test_encode_type_1():
    expected = b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C"
    nmea = NMEAMessage(expected).decode()

    assert encode(nmea.content, channel="B", seq_id=None)[0] == "!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C"

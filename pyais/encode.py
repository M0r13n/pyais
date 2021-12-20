import abc
import math
import typing

import attr
import bitarray

from pyais.util import chunks, from_bytes, compute_checksum

# Types
DATA_DICT = typing.Dict[str, typing.Union[str, int, float, bytes, bool]]
AIS_SENTENCES = typing.List[str]

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
    """
    Encode a single character as six-bit bitstring.
    @param char: The character to encode
    @return: The six-bit representation as string
    """
    char = char.upper()
    try:
        encoding = SIX_BIT_ENCODING[char]
        return f"{encoding:06b}"
    except KeyError:
        raise ValueError(f"received char '{char}' that cant be encoded")


def encode_ascii_6(bits: bitarray.bitarray) -> typing.Tuple[str, int]:
    """
    Transform the bitarray to an ASCII-encoded bit vector.
    Each character represents six bits of data.
    @param bits: The bitarray to convert to an ASCII-encoded bit vector.
    @return: ASCII-encoded bit vector and the number of fill bits required to pad the data payload to a 6 bit boundary.
    """
    out = ""
    chunk: bitarray.bitarray
    padding = 0
    for chunk in chunks(bits, 6):  # type:ignore
        padding = 6 - len(chunk)
        num = from_bytes(chunk.tobytes()) >> 2
        if padding:
            num >> padding
        armor = PAYLOAD_ARMOR[num]
        out += armor
    return out, padding


def int_to_bytes(val: typing.Union[int, bytes]) -> int:
    """
    Convert a bytes object to an integer. Byteorder is big.

    @param val: A bytes object to convert to an int. If the value is already an int, this is a NO-OP.
    @return: Integer representation of `val`
    """
    if isinstance(val, int):
        return val
    return int.from_bytes(val, 'big')


def int_to_bin(val: typing.Union[int, bool], width: int) -> bitarray.bitarray:
    """
    Convert an integer or boolean value to binary. If the value is too great to fit into
    `width` bits, the maximum possible number that still fits is used.

    @param val:     Any integer or boolean value.
    @param width:   The bit width. If less than width bits are required, leading zeros are added.
    @return:        The binary representation of value with exactly width bits. Type is bitarray.
    """
    # Compute the total number of bytes required to hold up to `width` bits.
    n_bytes, mod = divmod(width, 8)
    if mod > 0:
        n_bytes += 1

    # If the value is too big, return a bitarray of all 1's
    mask = (1 << width) - 1
    if val >= mask:
        return bitarray.bitarray('1' * width)

    bits = bitarray.bitarray(endian='big')
    bits.frombytes(val.to_bytes(n_bytes, 'big', signed=True))
    return bits[8 - mod if mod else 0:]


def str_to_bin(val: str, width: int) -> bitarray.bitarray:
    """
    Convert a string value to binary using six-bit ASCII encoding up to `width` chars.

    @param val:     The string to first convert to six-bit ASCII and then to binary.
    @param width:   The width of the full string. If the string has fewer characters than width, trailing '@' are added.
    @return:        The binary representation of value with exactly width bits. Type is bitarray.
    """
    out = bitarray.bitarray(endian='big')

    # Each char will be converted to a six-bit binary vector.
    # Therefore, the total number of chars is floor(WIDTH / 6).
    num_chars = int(width / 6)

    # Add trailing '@' if the string is shorter than `width`
    for _ in range(num_chars - len(val)):
        val += "@"

    # Encode AT MOST width characters
    for char in val[:num_chars]:
        # Covert each char to six-bit ASCII vector
        txt = to_six_bit(char)
        out += bitarray.bitarray(txt)

    return out


def bit_field(width: int, d_type: typing.Type[typing.Any],
              converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
              default: typing.Optional[typing.Any] = None) -> typing.Any:
    """
    Simple wrapper around the attr.ib interface to be used in conjunction with the Payload class.

    @param width:           The bit-width of the field.
    @param d_type:          The datatype of the fields value.
    @param converter:       Optional converter function to convert values before storing them.
    @param default:         Optional default value to be used when no value is explicitly passed.
    @return:                An attr.ib field instance.
    """
    return attr.ib(converter=converter, metadata={'width': width, 'd_type': d_type, 'default': default})


@attr.s(slots=True)
class Payload(abc.ABC):
    """
    Payload class
    --------------
    This class serves as an abstract base class for all messages.
    Each message shall inherit from Payload and define it's set of field using the `bit_field` method.
    """

    @classmethod
    def fields(cls) -> typing.Tuple[typing.Any]:
        """
        A list of all fields that were added to this class using attrs.
        """
        return attr.fields(cls)  # type:ignore

    def to_bitarray(self) -> bitarray.bitarray:
        """
        Convert a payload to binary.
        """
        out = bitarray.bitarray()
        for field in self.fields():
            width = field.metadata['width']
            d_type = field.metadata['d_type']

            val = getattr(self, field.name)
            val = d_type(val)

            if d_type == int:
                bits = int_to_bin(val, width)
            elif d_type == str:
                bits = str_to_bin(val, width)
            else:
                raise ValueError()
            bits = bits[:width]
            out += bits

        return out

    def encode(self) -> typing.Tuple[str, int]:
        """
        Encode a payload as an ASCII encoded bit vector. The second returned value is the number of fill bits.
        """
        bit_arr = self.to_bitarray()
        return encode_ascii_6(bit_arr)

    @classmethod
    def create(cls, **kwargs: typing.Union[str, float, int, bool, bytes]) -> "Payload":
        """
        Create a new instance of each Payload class.
        @param kwargs: A set of keywords. For each field of `cls` a keyword with the same
                       name is searched.If no matching keyword argument was provided the
                       default value will be used - if one is available.
        @return:
        """
        args = {}

        # Iterate over each field of the payload class and check for a matching keyword argument.
        # If no matching kwarg was provided use a default value
        for field in cls.fields():
            key = field.name
            try:
                args[key] = kwargs[key]
            except KeyError:
                # Check if a default value was provided
                default = field.metadata['default']
                if default is not None:
                    args[key] = default
        return cls(**args)


@attr.s(slots=True)
class MessageType1(Payload):
    msg_type = bit_field(6, int, default=1)
    repeat = bit_field(2, int, default=0)
    mmsi = bit_field(30, int)
    status = bit_field(4, int, default=0)
    turn = bit_field(8, int, default=0)
    speed = bit_field(10, int, converter=lambda v: float(v) * 10.0, default=0)
    accuracy = bit_field(1, int, default=0)
    lon = bit_field(28, int, converter=lambda v: float(v) * 600000.0, default=0)
    lat = bit_field(27, int, converter=lambda v: float(v) * 600000.0, default=0)
    course = bit_field(12, int, converter=lambda v: float(v) * 10.0, default=0)
    heading = bit_field(9, int, default=0)
    second = bit_field(6, int, default=0)
    maneuver = bit_field(2, int, default=0)
    spare = bit_field(3, int, default=0)
    raim = bit_field(1, int, default=0)
    radio = bit_field(19, int, default=0)


class MessageType2(MessageType1):
    msg_type = bit_field(6, int, default=2)


class MessageType3(MessageType1):
    msg_type = bit_field(6, int, default=3)


@attr.s(slots=True)
class MessageType4(Payload):
    msg_type = bit_field(6, int, default=4)
    repeat = bit_field(2, int, default=0)
    mmsi = bit_field(30, int)
    year = bit_field(14, int, default=1970)
    month = bit_field(4, int, default=1)
    day = bit_field(5, int, default=1)
    hour = bit_field(5, int, default=0)
    minute = bit_field(6, int, default=0)
    second = bit_field(6, int, default=0)
    accuracy = bit_field(1, int, default=0)
    lon = bit_field(28, int, converter=lambda v: float(v) * 600000.0, default=0)
    lat = bit_field(27, int, converter=lambda v: float(v) * 600000.0, default=0)
    epfd = bit_field(4, int, default=0)
    spare = bit_field(10, int, default=0)
    raim = bit_field(1, int, default=0)
    radio = bit_field(19, int, default=0)


@attr.s(slots=True)
class MessageType5(Payload):
    msg_type = bit_field(6, int, default=5)
    repeat = bit_field(2, int, default=0)
    mmsi = bit_field(30, int)
    ais_version = bit_field(2, int, default=0)
    imo = bit_field(30, int, default=0)
    callsign = bit_field(42, str, default='')
    shipname = bit_field(120, str, default='')
    shiptype = bit_field(8, int, default=0)
    to_bow = bit_field(9, int, default=0)
    to_stern = bit_field(9, int, default=0)
    to_port = bit_field(6, int, default=0)
    to_starboard = bit_field(6, int, default=0)
    epfd = bit_field(4, int, default=0)
    month = bit_field(4, int, default=0)
    day = bit_field(5, int, default=0)
    hour = bit_field(5, int, default=0)
    minute = bit_field(6, int, default=0)
    draught = bit_field(8, int, converter=lambda v: float(v) * 10.0, default=0)
    destination = bit_field(120, str, default='')
    dte = bit_field(1, int, default=0)
    spare = bit_field(1, int, default=0)


@attr.s(slots=True)
class MessageType6(Payload):
    msg_type = bit_field(6, int, default=6)
    repeat = bit_field(2, int, default=0)
    mmsi = bit_field(30, int)
    seqno = bit_field(2, int, default=0)
    dest_mmsi = bit_field(30, int)
    retransmit = bit_field(1, int, default=0)
    spare = bit_field(1, int, default=0)
    dac = bit_field(10, int, default=0)
    fid = bit_field(6, int, default=0)
    data = bit_field(920, int, default=0, converter=int_to_bytes)


@attr.s(slots=True)
class MessageType7(Payload):
    msg_type = bit_field(6, int, default=7)
    repeat = bit_field(2, int, default=0)
    mmsi = bit_field(30, int)
    spare = bit_field(2, int, default=0)
    mmsi1 = bit_field(30, int, default=0)
    mmsiseq1 = bit_field(2, int, default=0)
    mmsi2 = bit_field(30, int, default=0)
    mmsiseq2 = bit_field(2, int, default=0)
    mmsi3 = bit_field(30, int, default=0)
    mmsiseq3 = bit_field(2, int, default=0)
    mmsi4 = bit_field(30, int, default=0)
    mmsiseq4 = bit_field(2, int, default=0)


@attr.s(slots=True)
class MessageType8(Payload):
    msg_type = bit_field(6, int, default=8)
    repeat = bit_field(2, int, default=0)
    mmsi = bit_field(30, int)
    spare = bit_field(2, int, default=0)
    dac = bit_field(10, int, default=0)
    fid = bit_field(6, int, default=0)
    data = bit_field(952, int, default=0, converter=int_to_bytes)


ENCODE_MSG = {
    0: MessageType1,  # there are messages with a zero (0) as an id. these seem to be the same as type 1 messages
    1: MessageType1,
    2: MessageType2,
    3: MessageType3,
    4: MessageType4,
    5: MessageType5,
    6: MessageType6,
    7: MessageType7,
    8: MessageType8,
}


def get_ais_type(data: DATA_DICT) -> int:
    """
    Get the message type from a set of keyword arguments. The first occurence of either
    `type` or `msg_type` will be used.
    """
    keys = ['type', 'msg_type']
    length = len(keys) - 1
    for i, key in enumerate(keys):
        try:
            ais_type = data[key]
            return int(ais_type)
        except (KeyError, ValueError) as err:
            if i == length:
                raise ValueError("Missing or invalid AIS type. Must be a number.") from err
    raise ValueError("Missing type")


def data_to_payload(ais_type: int, data: DATA_DICT) -> Payload:
    try:
        return ENCODE_MSG[ais_type].create(**data)
    except KeyError as err:
        raise ValueError(f"AIS message type {ais_type} is not supported") from err


def ais_to_nmea_0183(payload: str, ais_talker_id: str, radio_channel: str, fill_bits: int) -> AIS_SENTENCES:
    """
    Splits the AIS payload into sentences, ASCII encodes the payload, creates
    and sends the relevant NMEA 0183 sentences.

    HINT:
        This method takes care of splitting large payloads (larger than 60 characters)
        into multiple sentences. With a total of 80 maximum chars excluding end of line
        per sentence, and 20 chars head + tail in the nmea 0183 carrier protocol, 60
        chars remain for the actual payload.

    @param payload:         Armored AIs payload.
    @param ais_talker_id:   AIS talker ID (AIVDO or AIVDM)
    @param radio_channel:   Radio channel (either A or B)
    @param fill_bits:       The number of fill bits requires to pad the data payload to a 6 bit boundary.
    @return:                A list of relevant AIS sentences.
    """
    messages = []
    max_len = 61
    seq_id = ''
    frag_cnt = math.ceil(len(payload) / max_len)

    if len(ais_talker_id) != 5:
        raise ValueError("AIS talker is must have exactly 6 characters. E.g. AIVDO")

    if len(radio_channel) != 1:
        raise ValueError("Radio channel must be a single character")

    for frag_num, chunk in enumerate(chunks(payload, max_len), start=1):
        tpl = "!{},{},{},{},{},{},{}*{:02X}"
        dummy_message = tpl.format(ais_talker_id, frag_cnt, frag_num, seq_id, radio_channel, chunk, fill_bits, 0)
        checksum = compute_checksum(dummy_message)
        msg = tpl.format(ais_talker_id, frag_cnt, frag_num, seq_id, radio_channel, chunk, fill_bits, checksum)
        messages.append(msg)

    return messages


def encode_dict(data: DATA_DICT, talker_id: str = "AIVDO", radio_channel: str = "A") -> AIS_SENTENCES:
    """
    Takes a dictionary of data and some NMEA specific kwargs and returns the NMEA 0183 encoded AIS sentence.

    Notes:
        - the data dict should also contain the AIS message type (1-27) under the `type` key.
        - different messages take different keywords. Refer to the payload classes above to get a glimpse
          on what fields each AIS message can take.

    @param data: The AIS data as a dictionary.
    @param talker_id: AIS packets have the introducer "AIVDM" or "AIVDO";
                      AIVDM packets are reports from other ships and AIVDO packets are reports from your own ship.
    @param radio_channel: The radio channel. Can be either 'A' (default) or 'B'.
    @return: NMEA 0183 encoded AIS sentences.

    """
    if talker_id not in ("AIVDM", "AIVDO"):
        raise ValueError("talker_id must be any of ['AIVDM', 'AIVDO']")

    if radio_channel not in ('A', 'B'):
        raise ValueError("radio_channel must be any of ['A', 'B']")

    ais_type = get_ais_type(data)
    payload = data_to_payload(ais_type, data)
    armored_payload, fill_bits = payload.encode()
    return ais_to_nmea_0183(armored_payload, talker_id, radio_channel, fill_bits)


def encode_payload(payload: Payload, talker_id: str = "AIVDO", radio_channel: str = "A") -> AIS_SENTENCES:
    if talker_id not in ("AIVDM", "AIVDO"):
        raise ValueError("talker_id must be any of ['AIVDM', 'AIVDO']")

    if radio_channel not in ('A', 'B'):
        raise ValueError("radio_channel must be any of ['A', 'B']")

    armored_payload, fill_bits = payload.encode()
    return ais_to_nmea_0183(armored_payload, talker_id, radio_channel, fill_bits)

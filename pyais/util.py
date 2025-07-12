import base64
import math
import typing
from collections import OrderedDict
from functools import partial, reduce
from operator import xor
from typing import Any, Generator, Hashable, TYPE_CHECKING, Union, Dict

from bitarray import bitarray

from pyais.constants import COUNTRY_MAPPING, SyncState
from pyais.exceptions import NonPrintableCharacterException

if TYPE_CHECKING:
    BaseDict = OrderedDict[Hashable, Any]
else:
    BaseDict = OrderedDict

from_bytes = partial(int.from_bytes, byteorder="big")
from_bytes_signed = partial(int.from_bytes, byteorder="big", signed=True)

T = typing.TypeVar('T')


def decode_into_bit_array(data: bytes, fill_bits: int = 0) -> bitarray:
    """
    Decodes a raw AIS message into a bitarray.
    :param data:        Raw AIS message in bytes
    :param fill_bits:   Number of trailing fill bits to be ignored
    :return:
    """
    bit_str = ''
    length = len(data)

    for i, c in enumerate(data):
        if not 0x20 <= c <= 0x7e:
            raise NonPrintableCharacterException(f"Non printable character: '{hex(c)}'")

        # Convert 8 bit binary to 6 bit binary
        c -= 0x30 if (c < 0x60) else 0x38
        c &= 0x3F

        if i == length - 1 and fill_bits:
            # The last part be shorter than 6 bits and contain fill bits
            c = c >> fill_bits
            bit_str += f'{c:b}'.zfill(6 - fill_bits)
        else:
            bit_str += f'{c:06b}'

    bit_arr = bitarray(bit_str)
    return bit_arr


def chunks(sequence: typing.Sequence[T], n: int) -> Generator[typing.Sequence[T], None, None]:
    """Yield successive n-sized chunks from sequence."""
    return (sequence[i:i + n] for i in range(0, len(sequence), n))


def decode_bin_as_ascii6(bit_arr: bitarray) -> str:
    """
    Decode binary data as 6 bit ASCII.
    :param bit_arr: array of bits
    :return: ASCII String
    """
    string: str = ""
    c: bitarray
    for c in chunks(bit_arr, 6):  # type:ignore
        n: int = from_bytes(c.tobytes()) >> 2

        # Last entry may not have 6 bits
        if len(c) != 6:
            n >>= (6 - len(c))

        if n < 0x20:
            n += 0x40

        # Break if there is an @
        if n == 64:
            break

        string += chr(n)

    return string.strip()


def get_int(data: bitarray, ix_low: int, ix_high: int, signed: bool = False) -> int:
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
    shift: int = (8 - ((ix_high - ix_low) % 8)) % 8
    data = data[ix_low:ix_high]
    i: int = from_bytes_signed(data) if signed else from_bytes(data)
    return i >> shift


def checksum(sentence: bytes) -> int:
    """
    Compute the NMEA checksum for a payload.
    :param sentence: The sentence to compute the checksum for. MUST BE bytes.

    >>> checksum(b's:2573535,c:1671533231')
    8
    """
    checksum = reduce(xor, sentence)
    return checksum


def compute_checksum(msg: Union[str, bytes]) -> int:
    """
    Compute the checksum of a given message.
    This method takes the **whole** message including the leading `!`.

    >>> compute_checksum(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0")
    91

    :param msg: message
    :return: int value of the checksum. Format as hex with `f'{checksum:02x}'`
    """
    if isinstance(msg, str):
        msg = msg.encode()

    msg = msg[1:].split(b'*', 1)[0]
    return reduce(xor, msg)


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


def encode_ascii_6(bits: bitarray) -> typing.Tuple[str, int]:
    """
    Transform the bitarray to an ASCII-encoded bit vector.
    Each character represents six bits of data.
    @param bits: The bitarray to convert to an ASCII-encoded bit vector.
    @return: ASCII-encoded bit vector and the number of fill bits required to pad the data payload to a 6 bit boundary.
    """
    out = ""
    chunk: bitarray
    padding = 0
    for chunk in chunks(bits, 6):  # type:ignore
        padding = 6 - len(chunk)
        num = from_bytes(chunk.tobytes()) >> 2
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


def bits2bytes(bits: typing.Union[str, bitarray]) -> bytes:
    """
    Convert a bitstring or a bitarray to bytes.
    >>> bits2bytes('00100110')
    b'&'
    """
    bits = bitarray(bits)
    return bits.tobytes()


def bytes2bits(in_bytes: bytes, default: typing.Optional[bitarray] = None) -> bitarray:
    """
    Convert a bytes object to a bitarray.

    @param  in_bytes :    The bytes to encode
    @param  default  :    A default value to return if `in_bytes` is *Falseish*

    >>> bytes2bits(b'&')
    bitarray('00100110')
    """
    if default is not None and not in_bytes:
        return default
    bits = bitarray(endian='big')
    bits.frombytes(in_bytes)
    return bits


def b64encode_str(val: bytes, encoding: str = 'utf-8') -> str:
    """BASE64 encoded a bytes string and returns the result as UTF-8 string"""
    return base64.b64encode(val).decode(encoding)


def coerce_val(val: typing.Any, d_type: typing.Type[T]) -> T:
    """Forces a given value in a given datatype"""
    if d_type == bytes and not isinstance(val, bytes):
        raise ValueError(f"Expected bytes, but got: {type(val)}")

    return d_type(val)  # type: ignore


def int_to_bin(val: typing.Union[int, bool], width: int, signed: bool = True) -> bitarray:
    """
    Convert an integer or boolean value to binary. If the value is too great to fit into
    `width` bits, the maximum possible number that still fits is used.

    @param val:     Any integer or boolean value.
    @param width:   The bit width. If less than width bits are required, leading zeros are added.
    @param signed:  Set to True/False if the value is signed or not.
    @return:        The binary representation of value with exactly width bits. Type is bitarray.
    """
    # Compute the total number of bytes required to hold up to `width` bits.
    n_bytes, mod = divmod(width, 8)
    if mod > 0:
        n_bytes += 1

    # If the value is too big, return a bitarray of all 1's
    mask = (1 << width) - 1
    if val >= mask:
        return bitarray('1' * width)

    bits = bitarray(endian='big')
    bits.frombytes(val.to_bytes(n_bytes, 'big', signed=signed))
    return bits[8 - mod if mod else 0:]


def str_to_bin(val: str, width: int, trailing_spaces: bool = False) -> bitarray:
    """
    Convert a string value to binary using six-bit ASCII encoding up to `width` chars.

    @param val:               The string to first convert to six-bit ASCII and then to binary.
    @param width:             The width of the full string
    @param trailing_spaces:   If the string has fewer characters than width, trailing '@' are added
    @return:        The binary representation of value with exactly width bits. Type is bitarray.
    """
    out = bitarray(endian='big')

    # Each char will be converted to a six-bit binary vector.
    # Therefore, the total number of chars is floor(WIDTH / 6).
    num_chars = int(width / 6)

    if trailing_spaces:
        # Add trailing '@' if the string is shorter than `width`
        for _ in range(num_chars - len(val)):
            val += "@"

    # Encode AT MOST width characters
    for char in val[:num_chars]:
        # Covert each char to six-bit ASCII vector
        txt = to_six_bit(char)
        out += bitarray(txt)

    return out


def chk_to_int(chk_str: bytes) -> typing.Tuple[int, int]:
    """
    Converts a checksum string to a tuple of (fillbits, checksum).
    >>> chk_to_int(b"0*1B")
    (0, 27)
    """
    if not len(chk_str):
        return 0, -1

    try:
        a, b = chk_str.split(b'*')
    except ValueError:
        return 0, -1

    try:
        fill_bits: int = int(a)
    except ValueError:
        fill_bits = 0

    try:
        checksum = int(b, 16)
    except (IndexError, ValueError):
        checksum = -1

    return fill_bits, checksum


SYNC_MASK = 0x03
TIMEOUT_MASK = 0x07
MSG_MASK = 0x3fff
SLOT_INCREMENT_MASK = 0x1fff


def get_sotdma_comm_state(radio: int) -> Dict[str, typing.Optional[int]]:
    """
    The SOTDMA communication state is structured as follows:
    +-------------------+----------------------+------------------------------------------------------------------------------------------------+
    | Parameter         |  Number of bits      |  Description                                                                                   |
    +-------------------+----------------------+------------------------------------------------------------------------------------------------+
    | Sync state        |  2                   |  0 UTC direct                                                                                  |
    |                   |                      |  1 UTC indirect                                                                                |
    |                   |                      |  2 Station is synchronized to a base station                                                   |
    |                   |                      |  3 Station is synchronized to another station based on the highest number of received stations |
    | Slot time-out     |  3                   |  Specifies frames remaining until a new slot is selected                                       |
    |                   |                      |  0 means that this was the last transmission in this slot                                      |
    |                   |                      |  1-7 means that 1 to 7 frames respectively are left until slot change                          |
    | Sub message       |  14                  |  14 The sub message depends on the current value in slot time-out                              |
    +-------------------+----------------------+------------------------------------------------------------------------------------------------+

    The slot time-out defines how to interpret the sub message:
    +-----------------+---------------------------------------------------------------------------+
    | Slot time-out   |  Description                                                              |
    +-----------------+---------------------------------------------------------------------------+
    | 3, 5, 7         |  Number of receiving stations (not own station) (between 0 and 16 383)    |
    | 2, 4, 6         |  Slot number Slot number used for this transmission (between 0 and 2 249) |
    | 1               |  UTC hour (bits 13 to 9) and minute (bits 8 to 2)                         |
    | 0               |  Next frame                                                               |
    +-----------------+---------------------------------------------------------------------------+

    You may refer to:
    - https://github.com/M0r13n/pyais/issues/17
    - https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.1371-1-200108-S!!PDF-E.pdf
    - https://www.navcen.uscg.gov/?pageName=AISMessagesA#Sync
    """
    result = {
        'received_stations': None,
        'slot_number': None,
        'utc_hour': None,
        'utc_minute': None,
        'slot_offset': None,
        'slot_timeout': 0,
        'sync_state': 0,
    }

    sync_state = (radio >> 17) & SYNC_MASK  # First two (2) bits
    slot_timeout = (radio >> 14) & TIMEOUT_MASK  # Next three (3) bits
    sub_msg = radio & MSG_MASK  # Last 14 bits

    if slot_timeout == 0:
        result['slot_offset'] = sub_msg
    elif slot_timeout == 1:
        result['utc_hour'] = (sub_msg >> 9) & 0x1f
        result['utc_minute'] = (sub_msg >> 2) & 0x3f
    elif slot_timeout in (2, 4, 6):
        result['slot_number'] = sub_msg
    elif slot_timeout in (3, 5, 7):
        result['received_stations'] = sub_msg
    else:
        raise ValueError("Slot timeout can only be an integer between 0 and 7")

    result['sync_state'] = SyncState(sync_state)
    result['slot_timeout'] = slot_timeout
    return result


def get_itdma_comm_state(radio: int) -> Dict[str, typing.Optional[int]]:
    """
    +-----------------+------+--------------------------------------------------------------------------------+
    |    Parameter    | Bits |                                  Description                                   |
    +-----------------+------+--------------------------------------------------------------------------------+
    | Sync state      |   2  | 0 UTC direct                                                                   |
    |                 |      | 1 UTC indirec                                                                  |
    |                 |      | 2 Station is synchronized to a base station                                    |
    |                 |      | 3 Station is synchronized to another station                                   |
    | Slot increment  |  13  | Offset to next slot to be used, or zero (0) if no more transmissions           |
    | Number of slots |   3  | Number of consecutive slots to allocate. (0 = 1 slot, 1 = 2 slots,2 = 3 slots, |
    |                 |      | 3 = 4 slots, 4 = 5 slots)                                                      |
    | Keep flag       |   1  | Set to TRUE = 1 if the slot remains allocated for one additional frame         |
    +-----------------+------+--------------------------------------------------------------------------------+

    You may refer to:
    - https://github.com/M0r13n/pyais/issues/17
    - https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.1371-1-200108-S!!PDF-E.pdf
    - https://www.navcen.uscg.gov/?pageName=AISMessagesA#Sync
    """

    sync_state = (radio >> 17) & SYNC_MASK  # First two (2) bits
    slot_increment = (radio >> 4) & SLOT_INCREMENT_MASK  # Next 13 bits
    num_slots = (radio >> 1) & TIMEOUT_MASK  # Next three (3) bits
    keep_flag = radio & 0x01  # Last bit

    return {
        'keep_flag': keep_flag,
        'sync_state': sync_state,
        'slot_increment': slot_increment,
        'num_slots': num_slots,
        'keep_flag': keep_flag,
    }


def get_first_three_digits(num: int) -> int:
    if num < 1000:
        return num
    digits = int(math.log10(num)) + 1
    return int(num // (10**(digits - 3)))


def get_country(mmsi: int) -> typing.Tuple[str, str]:
    return COUNTRY_MAPPING.get(get_first_three_digits(mmsi), ('NA', 'Unknown'))

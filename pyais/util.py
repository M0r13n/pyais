import base64
import math
import typing
from collections import OrderedDict
from functools import reduce
from operator import xor
from typing import Any, Generator, Hashable, TYPE_CHECKING, Union, Dict

from pyais.constants import COUNTRY_MAPPING, SyncState
from pyais.exceptions import NonPrintableCharacterException

if TYPE_CHECKING:
    BaseDict = OrderedDict[Hashable, Any]
else:
    BaseDict = OrderedDict

T = typing.TypeVar('T')


class SixBitNibleDecoder:
    """
    6-bit nible decoder.

    This class decodes AIS message payloads that use 6-bit ASCII encoding.
    AIS messages pack 6-bit values into ASCII characters for transmission,
    and this decoder converts them back to binary data.

    The decoder handles:
    - 6-bit to 8-bit conversion
    - Fill bits in the last character
    - Efficient bit packing into bytes

    Example:
        decoder = SixBitNibleDecoder()
        binary_data, bit_count = decoder.decode_fast(b"15M5N7001H")
    """

    def __init__(self) -> None:
        self._buffer = bytearray(256)

    def decode(self, payload: bytes, fill_bits: int = 0) -> tuple[bytes, int]:
        """
        Convert 6-bit AIS payload to binary data.

        Args:
            payload: 6-bit encoded AIS payload as bytes
            fill_bits: Number of padding bits in the last character (0-5)

        Returns:
            Tuple of (binary_data, total_bit_count)

        Raises:
            NonPrintableCharacterException: If payload contains invalid characters
        """
        payload_len = len(payload)
        if payload_len == 0:
            return b'', 0

        # Calculate total bits and required bytes
        total_bits = payload_len * 6 - fill_bits
        required_bytes = math.ceil(total_bits / 8)

        # Ensure buffer capacity
        if required_bytes > len(self._buffer):
            self._buffer = bytearray(required_bytes + 64)

        # Initialize output buffer
        for i in range(required_bytes):
            self._buffer[i] = 0

        current_bit_position = 0
        for char_index, char_byte in enumerate(payload):
            # Validate character is printable
            if not 0x20 <= char_byte <= 0x7e:
                raise NonPrintableCharacterException(f"Non printable character: '{hex(char_byte)}'")

            # Skip out-of-range characters
            if char_byte >= 120:
                continue

            # Convert ASCII to 6-bit value
            six_bit_value = self._ascii_to_six_bit(char_byte)

            # Handle fill bits in last character
            if char_index == payload_len - 1 and fill_bits > 0:
                six_bit_value = six_bit_value >> fill_bits
                bits_to_pack = 6 - fill_bits
            else:
                bits_to_pack = 6

            # Pack bits into buffer
            self._pack_bits_into_buffer(six_bit_value, bits_to_pack, current_bit_position, required_bytes)
            current_bit_position += bits_to_pack

        return bytes(self._buffer[:required_bytes]), total_bits

    def _ascii_to_six_bit(self, char_byte: int) -> int:
        """Convert ASCII character to 6-bit value."""
        if char_byte < 0x60:
            char_byte -= 0x30
        else:
            char_byte -= 0x38
        return char_byte & 0x3F

    def _pack_bits_into_buffer(self, value: int, bits_to_pack: int, bit_position: int, buffer_size: int) -> None:
        """Pack bits into the internal buffer at specified position."""
        byte_index = bit_position // 8
        bit_offset = bit_position % 8

        if bit_offset + bits_to_pack <= 8:
            # Fits entirely in current byte
            shift_amount = 8 - bit_offset - bits_to_pack
            self._buffer[byte_index] |= value << shift_amount
        else:
            # Spans across two bytes
            bits_in_first_byte = 8 - bit_offset
            bits_in_second_byte = bits_to_pack - bits_in_first_byte

            # Pack into first byte
            self._buffer[byte_index] |= value >> bits_in_second_byte

            # Pack into second byte if within bounds
            if byte_index + 1 < buffer_size:
                remaining_value = value << (8 - bits_in_second_byte)
                self._buffer[byte_index + 1] |= remaining_value & 0xFF


class SixBitNibleEncoder:
    """
    6-bit AIS (Automatic Identification System) encoder.

    Converts binary data into 6-bit AIS payload format using ASCII character encoding.
    The AIS standard uses a specific 6-bit encoding scheme where values 0-39 are encoded
    as ASCII characters 48-87 (0x30-0x57) and values 40-63 are encoded as ASCII
    characters 96-119 (0x60-0x77).

    The encoder handles bit padding automatically to ensure the output aligns to
    6-bit boundaries.
    """

    def __init__(self) -> None:
        self._buffer = bytearray(256)  # Pre-allocated buffer

    def encode(self, data: bytes, total_bits: int) -> tuple[str, int]:
        """
        Convert binary data to 6-bit AIS payload format.

        Args:
            data: Binary data to encode
            total_bits: Number of bits to process from the data

        Returns:
            Tuple of (encoded_string, fill_bits_count)
        """
        if len(data) == 0:
            return '', 0

        fill_bits = self._calculate_fill_bits(total_bits)
        char_count = math.ceil(total_bits / 6)
        self._ensure_buffer_size(char_count)

        bit_pos = 0
        char_idx = 0

        while bit_pos < total_bits and char_idx < char_count:
            six_bit_val = self._extract_six_bits(data, bit_pos, total_bits, char_idx, char_count, fill_bits)
            ascii_char = self._six_bit_to_ascii(six_bit_val)

            self._buffer[char_idx] = ascii_char
            char_idx += 1
            bit_pos += self._get_bits_extracted(bit_pos, total_bits, char_idx, char_count, fill_bits)

        return bytes(self._buffer[:char_count]).decode('ascii'), fill_bits

    def _calculate_fill_bits(self, total_bits: int) -> int:
        """Calculate number of fill bits needed for 6-bit alignment."""
        return (6 - (total_bits % 6)) % 6

    def _ensure_buffer_size(self, char_count: int) -> None:
        """Ensure buffer is large enough for the encoded output."""
        if char_count > len(self._buffer):
            self._buffer = bytearray(char_count + 64)

    def _extract_six_bits(self, data: bytes, bit_pos: int, total_bits: int,
                          char_idx: int, char_count: int, fill_bits: int) -> int:
        """Extract up to 6 bits from the data at the given bit position."""
        byte_idx = bit_pos // 8
        bit_offset = bit_pos % 8
        bits_to_extract = min(6, total_bits - bit_pos)

        # Handle last character fill bits
        if char_idx == char_count - 1 and fill_bits > 0:
            bits_to_extract = 6 - fill_bits

        six_bit_val = self._get_bits_from_data(data, byte_idx, bit_offset, bits_to_extract)

        # Handle fill bits in last character
        if char_idx == char_count - 1 and fill_bits > 0:
            six_bit_val = six_bit_val << fill_bits

        return six_bit_val & 0x3F

    def _get_bits_from_data(self, data: bytes, byte_idx: int, bit_offset: int, bits_to_extract: int) -> int:
        """Extract bits from data, handling byte boundaries."""
        if bit_offset + bits_to_extract <= 8:
            # All bits in current byte
            if byte_idx < len(data):
                return (data[byte_idx] >> (8 - bit_offset - bits_to_extract)) & ((1 << bits_to_extract) - 1)
            return 0
        else:
            # Bits span two bytes
            if byte_idx < len(data):
                six_bit_val = (data[byte_idx] << (bits_to_extract - (8 - bit_offset))) & ((1 << bits_to_extract) - 1)
                if byte_idx + 1 < len(data):
                    remaining_bits = bits_to_extract - (8 - bit_offset)
                    six_bit_val |= data[byte_idx + 1] >> (8 - remaining_bits)
                return six_bit_val
            return 0

    def _six_bit_to_ascii(self, six_bit_val: int) -> int:
        """Convert 6-bit value to AIS ASCII character."""
        if six_bit_val < 40:  # 0x28
            return six_bit_val + 0x30  # Add 48
        else:
            return six_bit_val + 0x38  # Add 56

    def _get_bits_extracted(self, bit_pos: int, total_bits: int, char_idx: int, char_count: int, fill_bits: int) -> int:
        """Calculate how many bits were extracted in this iteration."""
        bits_to_extract = min(6, total_bits - bit_pos)
        if char_idx == char_count and fill_bits > 0:
            bits_to_extract = 6 - fill_bits
        return bits_to_extract


def get_num(num: int, start_bit: int, num_bits: int, total_bits: int, signed: bool = False) -> int:
    # Handle edge cases
    if num_bits == 0 or start_bit >= total_bits:
        return 0

    # Calculate actual bits to read
    available_bits = total_bits - start_bit
    bits_to_read = min(num_bits, available_bits)
    shift = total_bits - start_bit - bits_to_read

    if bits_to_read == 0:
        return 0

    # Create mask and extract value
    mask = ((1 << bits_to_read) - 1) << shift
    val = (num & mask) >> shift

    # Handle signed interpretation
    if signed:
        sign_bit_mask = 1 << (num_bits - 1)
        if val & sign_bit_mask:
            val = val - (1 << num_bits)

    return val


def extract_bits(data: bytes, start_bit: int, num_bits: int, total_bit_length: int = -1, signed: bool = False) -> int:
    """bit extraction from bytes"""
    if total_bit_length == -1:
        total_bit_length = len(data) * 8

    if num_bits == 0:
        return 0

    if start_bit >= total_bit_length:
        return 0

    # Limit extraction to available bits
    available_bits = total_bit_length - start_bit
    bits_to_read = min(num_bits, available_bits)

    if bits_to_read == 0:
        return 0

    result = 0
    bits_read = 0

    while bits_read < bits_to_read:
        byte_idx = (start_bit + bits_read) // 8
        if byte_idx >= len(data):
            break

        bit_offset = (start_bit + bits_read) % 8
        bits_in_byte = min(8 - bit_offset, bits_to_read - bits_read)

        # Extract bits from current byte
        mask = (1 << bits_in_byte) - 1
        byte_value = (data[byte_idx] >> (8 - bit_offset - bits_in_byte)) & mask

        result = (result << bits_in_byte) | byte_value
        bits_read += bits_in_byte

    # Handle signed interpretation
    if signed and num_bits > 0:
        sign_bit_mask = 1 << (num_bits - 1)
        if result & sign_bit_mask:
            result = result - (1 << num_bits)

    return result


def chunks(sequence: typing.Sequence[T], n: int) -> Generator[typing.Sequence[T], None, None]:
    """Yield successive n-sized chunks from sequence."""
    return (sequence[i:i + n] for i in range(0, len(sequence), n))


def decode_bytes_as_ascii6(data: bytes, start_bit: int = 0, total_bits: int = -1) -> str:
    """
    Decode binary data as 6-bit ASCII.

    Args:
        data: Binary data to decode
        start_bit: Starting bit position (default: 0)
        total_bits: Total number of bits to process (default: all available)

    Returns:
        ASCII String
    """
    if total_bits == -1:
        total_bits = len(data) * 8 - start_bit

    string = ""
    bit_pos = start_bit

    while bit_pos < start_bit + total_bits:
        # Calculate how many bits are available for this chunk
        remaining_bits = (start_bit + total_bits) - bit_pos
        chunk_bits = min(6, remaining_bits)

        if chunk_bits == 0:
            break

        # Extract the 6-bit chunk (or less if at the end)
        n = extract_bits(data, bit_pos, chunk_bits, signed=False)

        # Handle incomplete chunks (less than 6 bits)
        if chunk_bits < 6:
            n <<= (6 - chunk_bits)  # Left-shift to align to 6-bit boundary

        # Convert to ASCII character
        if n < 0x20:
            n += 0x40

        # Break if there is an @ (ASCII 64)
        if n == 64:
            break

        string += chr(n)
        bit_pos += chunk_bits

    return string.strip()


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


def int_to_bytes(val: typing.Union[int, bytes]) -> int:
    """
    Convert a bytes object to an integer. Byteorder is big.

    @param val: A bytes object to convert to an int. If the value is already an int, this is a NO-OP.
    @return: Integer representation of `val`
    """
    if isinstance(val, int):
        return val
    return int.from_bytes(val, 'big')


def b64encode_str(val: bytes, encoding: str = 'utf-8') -> str:
    """BASE64 encoded a bytes string and returns the result as UTF-8 string"""
    return base64.b64encode(val).decode(encoding)


def coerce_val(val: typing.Any, d_type: typing.Type[T]) -> T:
    """Forces a given value in a given datatype"""
    if d_type == bytes and not isinstance(val, bytes):
        raise ValueError(f"Expected bytes, but got: {type(val)}")

    return d_type(val)  # type: ignore


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


def get_bytes(data: bytes, start_bit: int, length_bits: int) -> bytes:
    """
    Extract raw bytes from binary data starting at a specific bit position.

    Args:
        data: Source binary data
        start_bit: Starting bit position (0-indexed)
        length_bits: Number of bits to extract

    Returns:
        bytes object containing the extracted bits, padded to byte boundaries

    Examples:
        >>> decoder.get_bytes(b'\xFF\x00\xAA', 4, 8)  # Extract 8 bits starting at bit 4
        b'\xF0'
        >>> decoder.get_bytes(b'\xFF\x00\xAA', 0, 12)  # Extract 12 bits starting at bit 0
        b'\xFF\x00'
    """
    if length_bits <= 0:
        return b''

    # Check boundaries
    data_bit_length = len(data) * 8
    if start_bit >= data_bit_length:
        return b''

    # Limit to available bits
    available_bits = data_bit_length - start_bit
    actual_bits = min(length_bits, available_bits)

    if actual_bits <= 0:
        return b''

    # Calculate output byte count
    output_bytes = (actual_bits + 7) // 8

    result_buffer = bytearray(output_bytes)

    # Extract bits and pack into bytes
    bits_copied = 0

    while bits_copied < actual_bits:
        # Source position
        src_byte_idx = (start_bit + bits_copied) // 8
        src_bit_offset = (start_bit + bits_copied) % 8

        # Destination position
        dst_byte_idx = bits_copied // 8
        dst_bit_offset = bits_copied % 8

        # How many bits can we copy from current source byte?
        src_bits_available = 8 - src_bit_offset
        dst_bits_available = 8 - dst_bit_offset
        remaining_bits = actual_bits - bits_copied

        bits_to_copy = min(src_bits_available, dst_bits_available, remaining_bits)

        if src_byte_idx < len(data) and dst_byte_idx < output_bytes:
            # Extract bits from source
            src_mask = ((1 << bits_to_copy) - 1) << (src_bits_available - bits_to_copy)
            src_bits = (data[src_byte_idx] & src_mask) >> (src_bits_available - bits_to_copy)

            # Place bits in destination
            dst_shift = dst_bits_available - bits_to_copy
            result_buffer[dst_byte_idx] |= src_bits << dst_shift

        bits_copied += bits_to_copy

    return bytes(result_buffer[:output_bytes])

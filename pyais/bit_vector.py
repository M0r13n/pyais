"""
This bit vector uses pre-computed lookup tables and stores the entire payload as a single
arbitrary-precision int so that every field extraction is a constant-time shift-and-mask operation.
"""
import typing as t
from base64 import b64decode

# ASCII ordinal 6-bit AIS payload value
# Valid input range: ordinals 48 ('0') through 119 ('w').
# Everything outside that range maps to 0; upstream validation is expected.
_PAYLOAD_ARMOR: t.Final[tuple[int, ...]] = tuple(
    (c - 48 - 8 if c - 48 > 40 else c - 48) if 48 <= c <= 119 else 0 for c in range(256)
)

# AIS six-bit armoring is base64 with a different alphabet. Re-mapping the payload
# onto the standard base64 alphabet lets `base64.b64decode` do the 6-to-8 bit
# repacking in C, which is several times faster than a Python-level loop.
# Every one of the 256 input bytes maps onto a valid base64 character, so the
# decoder never sees (and never silently discards) an out-of-alphabet byte.
_B64_ALPHABET: t.Final[bytes] = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
_ARMOR_TO_B64: t.Final[bytes] = bytes(_B64_ALPHABET[v] for v in _PAYLOAD_ARMOR)

# base64 works on groups of four characters. Pad the payload up to the next
# multiple of four with 'A' (== six zero bits) and shift the surplus back out.
_B64_PAD: t.Final[tuple[bytes, ...]] = (b'', b'AAA', b'AA', b'A')

# 6-bit value decoded AIS character (for text fields)
_SIXBIT_CHAR: t.Final[tuple[str, ...]] = tuple(
    chr(v + 64) if v < 32 else chr(v) for v in range(64)
)

# Bitmasks: _MASK[n] = (1 << n) - 1
# 257 entries covers every realistic AIS field width.
_MASK: t.Final[tuple[int, ...]] = tuple((1 << n) - 1 for n in range(257))


class bit_vector:

    __slots__ = ("_value", "_length")

    def __init__(self, data: bytes, pad: int = 0) -> None:
        # Convert bytes into single large integer.
        # The payload is re-armored onto the base64 alphabet so that the actual
        # 6-to-8 bit repacking happens inside `b64decode` rather than in Python.
        length = len(data) * 6
        remainder = len(data) & 3
        if remainder:
            value = int.from_bytes(
                b64decode(data.translate(_ARMOR_TO_B64) + _B64_PAD[remainder]), 'big'
            ) >> (6 * (4 - remainder))
        else:
            value = int.from_bytes(b64decode(data.translate(_ARMOR_TO_B64)), 'big')

        if pad:
            value >>= pad
            length -= pad

        self._value: int = value
        self._length: int = length

    @classmethod
    def from_bytes(cls, data: bytes) -> 'bit_vector':
        """Create a bit vector from raw bytes without AIS six-bit dearmoring."""
        bv = cls(b"", 0)
        bv._value = int.from_bytes(data, 'big')
        bv._length = len(data) * 8
        return bv

    def get_num(self, start: int, width: int, signed: bool = False) -> int:
        """Return an unsigned integer of *width* bits at bit position *start*.
        Takes an additional argument *signed* if the number is signed.
        Returns an unsigned integer by default.
        """
        if signed:
            return self.get_signed(start, width)
        return self.get(start, width)

    def get(self, start: int, width: int) -> int:
        """Return an unsigned integer of *width* bits at bit position *start*."""
        # If the requested range extends beyond the end of the vector,
        # only the available bits are returned
        if width <= 0 or start >= self._length:
            return 0
        available = min(width, self._length - start)
        shift = self._length - start - available
        return (self._value >> shift) & _MASK[available]

    def get_signed(self, start: int, width: int) -> int:
        """Return a signed (two's-complement) integer."""
        if width <= 0 or start >= self._length:
            return 0
        available = min(width, self._length - start)
        shift = self._length - start - available
        val = (self._value >> shift) & _MASK[available]
        if val & (1 << (available - 1)):
            val -= 1 << available
        return val

    def get_bool(self, start: int) -> bool:
        """Return a single bit as a boolean."""
        if start >= self._length:
            return False
        shift = self._length - start - 1
        return bool((self._value >> shift) & 1)

    def get_str(self, start: int, width: int) -> str:
        """Return a 6-bit-encoded AIS text string."""
        if width <= 0 or start >= self._length:
            return ""
        chars = _SIXBIT_CHAR
        get = self.get
        parts: list[str] = [chars[get(i, 6)] for i in range(start, start + width, 6)]
        return "".join(parts).rstrip("@").strip()

    def get_bytes(self, start: int, width: int) -> bytes:
        """Return the value of *width* bits at bit position *start* as bytes."""
        if width <= 0 or start >= self._length:
            return b""

        available = min(width, self._length - start)
        shift = self._length - start - available
        # Not using _MASK because the width might be larger than 257 bits
        val = (self._value >> shift) & ((1 << available) - 1)

        # Pad to byte boundary on the right
        num_bytes = (available + 7) // 8
        pad_bits = num_bytes * 8 - available
        val <<= pad_bits

        return val.to_bytes(num_bytes, "big")

    def __len__(self) -> int:
        return self._length

    def __repr__(self) -> str:
        return f"bit_vector(length={self._length})"

    def __eq__(self, value: object) -> bool:
        try:
            if not isinstance(value, bit_vector):
                return False
            return self._length == value._length and self._value == value._value
        except ValueError:
            return False

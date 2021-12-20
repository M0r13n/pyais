import typing
import warnings
from collections import OrderedDict
from functools import partial, reduce
from operator import xor
from typing import Any, Generator, Hashable, TYPE_CHECKING, Callable, Union

from bitarray import bitarray

if TYPE_CHECKING:
    BaseDict = OrderedDict[Hashable, Any]
else:
    BaseDict = OrderedDict

from_bytes = partial(int.from_bytes, byteorder="big")
from_bytes_signed = partial(int.from_bytes, byteorder="big", signed=True)

T = typing.TypeVar('T')


def deprecated(f: Callable[[Any], Any]) -> Callable[[Any], Any]:
    @property  # type: ignore
    def wrapper(self: Any) -> Any:
        warnings.simplefilter('always', DeprecationWarning)  # turn off filter
        warnings.warn(f"{f.__name__} is deprecated and will be removed soon.",
                      category=DeprecationWarning)
        warnings.simplefilter('default', DeprecationWarning)  # reset filter

        return f(self)

    return wrapper


def decode_into_bit_array(data: bytes) -> bitarray:
    """
    Decodes a raw AIS message into a bitarray.
    :param data: Raw AIS message in bytes
    :return:
    """
    bit_arr = bitarray()

    for _, c in enumerate(data):
        if c < 0x30 or c > 0x77 or 0x57 < c < 0x6:
            raise ValueError(f"Invalid character: {chr(c)}")

        # Convert 8 bit binary to 6 bit binary
        c -= 0x30 if (c < 0x60) else 0x38
        c &= 0x3F
        bit_arr += bitarray(f'{c:06b}')

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
            n >> (6 - len(c))

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


def get_mmsi(data: bitarray, ix_low: int, ix_high: int) -> str:
    """
    A Maritime Mobile Service Identity (MMSI) is a series of nine digits.
    Every digit is required and therefore we can NOT use a int.
    See: issue #6
    """
    mmsi_int: int = get_int(data, ix_low, ix_high)
    return str(mmsi_int).zfill(9)


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


class FixedSizeDict(BaseDict):
    """
    Fixed sized dictionary that only contains up to N keys.
    """

    def __init__(self, maxlen: int) -> None:
        super().__init__()
        self.maxlen: int = maxlen

    def __setitem__(self, k: Hashable, v: Any) -> None:
        super().__setitem__(k, v)
        # if the maximum number is reach delete the oldest n keys
        if len(self) >= self.maxlen:
            self._pop_oldest()

    def _pop_oldest(self) -> Any:
        # instead of calling this method often, we delete a whole bunch of keys in one run
        for _ in range(self._items_to_pop):
            self.popitem(last=False)

    @property
    def _items_to_pop(self) -> int:
        # delete 1/5th of keys
        return self.maxlen // 5

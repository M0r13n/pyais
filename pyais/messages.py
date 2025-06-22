import abc
import datetime
import functools
import json
import math
import typing
from typing import Any, Dict, Optional, Sequence, Union

import attr
from bitarray import bitarray

from pyais.constants import TalkerID, NavigationStatus, ManeuverIndicator, EpfdType, ShipType, NavAid, StationType, \
    TransmitMode, StationIntervals, TurnRate, InlandLoadedType
from pyais.exceptions import InvalidNMEAMessageException, TagBlockNotInitializedException, UnknownMessageException, UnknownPartNoException, \
    InvalidDataTypeException, MissingPayloadException
from pyais.util import checksum, decode_into_bit_array, compute_checksum, get_itdma_comm_state, get_sotdma_comm_state, int_to_bin, str_to_bin, \
    encode_ascii_6, from_bytes, from_bytes_signed, decode_bin_as_ascii6, get_int, chk_to_int, coerce_val, \
    bits2bytes, bytes2bits, b64encode_str

NMEA_VALUE = typing.Union[str, float, int, bool, bytes]

B_EXCLAMATION_MARK = b"!"
B_DOLLAR_SIGN = b"$"
ASTERISK = b"*"
COMMA = b","
B_VDM = b"VDM"
B_VDO = b"VDO"
B_GH = b"HP"
TAG_BLOCK_START = b'\\'
MAX_FRAG_CNT = 100
MAX_PAYLOAD_LEN = 200


def bit_field(width: int, d_type: typing.Type[typing.Any],
              from_converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
              to_converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
              default: typing.Optional[typing.Any] = None,
              signed: bool = False,
              variable_length: bool = False,
              **kwargs: typing.Any) -> typing.Any:
    """
    Simple wrapper around the attr.ib interface to be used in conjunction with the Payload class.

    @param width:               The bit-width of the field.
    @param d_type:              The datatype of the field used while decoding
    @param from_converter:      Optional converter function called **before** encoding
    @param to_converter:        Optional converter function called **after** decoding
    @param default:             Optional default value to be used when no value is explicitly passed.
    @param signed:              Set to true if the value is a signed integer
    @param variable_length:     Set to true, if the field can be shorter than width (e.g. for binary data/text)
    @return:                    An attr.ib field instance.
    """
    return attr.ib(
        metadata={
            'width': width,
            'd_type': d_type,
            'from_converter': from_converter,
            'to_converter': to_converter,
            'signed': signed,
            'default': default,
            'variable_length': variable_length,
        },
        **kwargs
    )


ENUM_FIELDS = {'status', 'maneuver', 'epfd', 'ship_type', 'aid_type', 'station_type', 'txrx', 'interval'}


class AISJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle bytes objects"""

    def default(self, o: typing.Any) -> typing.Any:
        if isinstance(o, bytes):
            return b64encode_str(o)
        return json.JSONEncoder.default(self, o)


class NMEASentenceFactory:
    """
    NMEA sentence factory.
    There are tons of different NMEA sentences.
    In order to correctly parse each sentence, this factory looks at the structure of the sentence.
    The first comma-separated fields defines the type of NMEA sentence.

    NOTE: Only a very small subset of all NMEA sentences is currently supported!
    """

    @classmethod
    def _pre_process(
        cls, raw: bytes
    ) -> typing.Tuple[bytes, typing.Optional[bytes]]:
        """
        Preprocess the sentence.
        If the sentence has no tag block it is returned as is.
        Otherwise the tag block and NMEA sentence are separated
        Example with tag block:
        >>> NMEASentenceFactory._pre_process(b'\\s:2573535,c:1671533231*08\\!BSVDM,2,2,8,B,00000000000,2*36')
        (b'!BSVDM,2,2,8,B,00000000000,2*36', b's:2573535,c:1671533231*08')

        """
        raw = raw.strip()

        if raw[0] == ord(TAG_BLOCK_START):
            ix_start = 0
            ix_end = raw[1:].find(TAG_BLOCK_START) + 1
            tag_block = raw[ix_start + 1:ix_end]

            return raw[ix_end + 1:], tag_block

        return raw, None

    @classmethod
    def _produce(cls, raw: bytes) -> "NMEASentence":
        # Parse the first comma separated field
        fields = raw.split(COMMA)
        first_field = fields[0]
        delimiter = first_field[:1]
        type_code = first_field[3:]
        type_code = type_code.upper()

        if type_code == B_VDM or type_code == B_VDO:
            return AISSentence(raw)
        if delimiter == B_DOLLAR_SIGN:
            if type_code == B_GH:
                return GatehouseSentence(raw)

        raise UnknownMessageException(raw)

    @classmethod
    def produce(cls, raw: bytes) -> "NMEASentence":
        """Parse a single bytes string into an NMEA sentence."""
        if not isinstance(raw, bytes):
            raise TypeError("message must be bytes")

        if len(raw) == 0:
            raise InvalidNMEAMessageException("empty bytes")

        raw_sentence, tb = cls._pre_process(raw)
        sentence = cls._produce(raw_sentence)
        if tb:

            sentence.tag_block = TagBlock(tb)
        return sentence


def error_if_uninitialized(func: typing.Callable[['TagBlock'], typing.Any]) -> typing.Callable[['TagBlock'], typing.Any]:
    @functools.wraps(func)
    def wrapper(tb: 'TagBlock') -> typing.Any:
        if not tb.initialized:
            raise TagBlockNotInitializedException(
                'tag block not initialized. you need to call .init() first'
            )
        return func(tb)
    return wrapper


class TagBlockGroup:
    """Tag Block Group represents the 3-int group sequence
    optionally included as part of the NMEA Tag Block

    it consists of 3, comma-seperated integers X-Y-Z where:
    - X = Message ID in sequence
    - Y = Total parts in group
    - Z = Unique GroupID for this group of messages."""

    __slots__ = (
        'sentence_num',
        'sentence_tot',
        'group_id'
    )

    def __init__(self, msg_id: int, total: int, group_id: int):
        self.sentence_num = msg_id
        self.sentence_tot = total
        self.group_id = group_id

    @staticmethod
    def from_str(raw: str) -> 'TagBlockGroup':
        """Constructs a new NMEAGroup from it's string representation"""
        [msg_id, msg_total, group_id] = raw.split("-", 3)

        return TagBlockGroup(
            int(msg_id),
            int(msg_total),
            int(group_id)
        )

    @property
    def is_fragmented(self) -> bool:
        """Returns whether or not this group expects several parts."""
        return self.sentence_tot > 1

    def __str__(self) -> str:
        """Returns this NMEA group instance in it's string representation."""
        return f"{self.sentence_num}-{self.sentence_tot}-{self.group_id}"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TagBlockGroup):
            return self.sentence_num == other.sentence_num and self.sentence_tot == other.sentence_tot and self.group_id == other.group_id
        return False


class TagBlock:
    # Field code mapping for encoding/decoding
    FIELD_CODES = {
        'receiver_timestamp': 'c',
        'destination_station': 'd',
        'line_count': 'n',
        'relative_time': 'r',
        'source_station': 's',
        'text': 't',
        'group': 'g',
    }

    # Reverse mapping for decoding
    FIELD_NAMES = {code: name for name, code in FIELD_CODES.items()}

    __slots__ = (
        'raw',
        'initialized',
        '_is_valid',
        '_actual_checksum',
        '_expected_checksum',
        '_receiver_timestamp',
        '_source_station',
        '_destination_station',
        '_line_count',
        '_relative_time',
        '_text',
        '_group'
    )

    def __init__(self, raw: bytes) -> None:
        self.raw = raw
        self.initialized = False
        self._is_valid = False
        self._actual_checksum = -1
        self._expected_checksum = -1
        self._receiver_timestamp = None
        self._destination_station = None
        self._line_count = None
        self._source_station = None
        self._relative_time = None
        self._text = None
        self._group: Optional[TagBlockGroup] = None

    @property
    @error_if_uninitialized
    def receiver_timestamp(self) -> typing.Optional[str]:
        return self._receiver_timestamp

    @property
    @error_if_uninitialized
    def destination_station(self) -> typing.Optional[str]:
        return self._destination_station

    @property
    @error_if_uninitialized
    def line_count(self) -> typing.Optional[str]:
        return self._line_count

    @property
    @error_if_uninitialized
    def source_station(self) -> typing.Optional[str]:
        return self._source_station

    @property
    @error_if_uninitialized
    def relative_time(self) -> typing.Optional[str]:
        return self._relative_time

    @property
    @error_if_uninitialized
    def text(self) -> typing.Optional[str]:
        return self._text

    @property
    @error_if_uninitialized
    def is_valid(self) -> bool:
        return self._is_valid

    @property
    @error_if_uninitialized
    def actual_checksum(self) -> int:
        return self._actual_checksum

    @property
    @error_if_uninitialized
    def expected_checksum(self) -> int:
        return self._expected_checksum

    @property
    @error_if_uninitialized
    def group(self) -> typing.Optional[TagBlockGroup]:
        return self._group

    def init(self) -> None:
        """Initialize the TagBlock by parsing the raw data."""
        payload, check = self.raw.split(ASTERISK)

        self._actual_checksum = checksum(payload)
        self._expected_checksum = int(check.decode(), 16)
        self._is_valid = self._actual_checksum == self._expected_checksum

        self._parse_payload(payload)
        self.initialized = True

    def _parse_payload(self, payload: bytes) -> None:
        """Parse the payload bytes into fields."""
        fields = payload.split(COMMA)
        for field in fields:
            try:
                field_str = field.decode()
                spec, val = field_str.split(':', 1)

                if spec == 'g':
                    self._group = TagBlockGroup.from_str(val)
                elif spec in self.FIELD_NAMES:
                    # Set attribute directly using field name
                    attr_name = f"_{self.FIELD_NAMES[spec]}"
                    setattr(self, attr_name, val)
            except (ValueError, UnicodeDecodeError):
                # Skip malformed fields
                continue

    @classmethod
    def create(cls, **fields: Dict[str, object]) -> bytes:
        """Create a TagBlock from field values.
        Unknown fields are ignored. Refer to TagBlock.FIELD_NAMES for supported fields.

        >>> TagBlock.create(source_station="STATION1", text="Hello")
        b's:STATION1,t:Hello*2'
        """
        pairs = []
        for key, val in fields.items():
            if val is not None and key in cls.FIELD_CODES:
                field_code = cls.FIELD_CODES[key]
                pairs.append(f"{field_code}:{val}".encode())

        payload = COMMA.join(pairs)

        # compute checksum as hex, e.g. *7E
        csum = hex(checksum(payload))[2:].upper().encode()
        return payload + ASTERISK + csum

    @classmethod
    def create_str(cls, **fields: Dict[str, object]) -> str:
        """The same as .create() but returns a string"""
        return cls.create(**fields).decode()

    def __repr__(self) -> str:
        if not self.initialized:
            return "TagBlock<uninitialized>"
        return f"TagBlock<{self.raw.decode()}>"

    @error_if_uninitialized
    def asdict(self) -> typing.Dict[str, typing.Any]:
        """Return a dictionary representation of the TagBlock."""
        return {
            'raw': self.raw,
            'receiver_timestamp': self.receiver_timestamp,
            'source_station': self.source_station,
            'destination_station': self.destination_station,
            'line_count': self.line_count,
            'relative_time': self.relative_time,
            'text': self.text,
        }


class NMEASentence(object):
    """
    Single NMEA Sentence.
    An NMEA sentence consists of a start delimiter, followed by a comma-separated
    sequence of fields, followed by the character '*', the checksum and
    an end-of-line marker.
    """
    __slots__ = (
        'raw',
        'delimiter',
        'data_fields',
        'talker_id',
        'type',
        'checksum',
        'fill_bits',
        'is_valid',
        'wrapper_msg',
        'tag_block',
    )

    TYPE = "UNDEFINED"

    def __init__(self, raw: bytes) -> None:
        if not isinstance(raw, bytes):
            raise ValueError(f"'NMEAMessage' only accepts bytes, but got '{type(raw)}'")

        # Initial values
        self.checksum: int = -1

        # Store raw data
        self.raw: bytes = raw

        # A NMEA message consists of comma separated parts
        fields = raw.split(b",")

        # The first field of a sentence is called the "tag" and normally consists
        # of a two-letter talker ID followed by a three-letter type code.
        first_field = fields[0]
        self.delimiter = first_field[:1]
        self.talker_id = first_field[1:3].decode('ascii')
        self.type = first_field[3:].decode('ascii')

        checksum = fields[-1]
        fill, check = chk_to_int(checksum)
        # Fill bits (0 to 5)
        self.fill_bits: int = fill
        # Message Checksum (hex value)
        self.checksum = check
        # Set the checksum valid field
        self.is_valid = self.checksum == compute_checksum(self.raw)

        self.data_fields = fields[1:-1]

        # Some NMEA messages contain meta data for other messages
        # E.G PGHP messages (Gatehousing)
        self.wrapper_msg: typing.Optional['GatehouseSentence'] = None

        # Some NMEA messages may contain a leading tag block
        # NOTE:     I couldn't find any good documentation for these fields.
        #           Therefore, TagBlocks are lazily evaluated (need to call tag_block.init() first)
        self.tag_block: typing.Optional['TagBlock'] = None

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}<{self.raw.decode('ascii')}>"

    def __getitem__(self, item: str) -> Union[int, str, bytes, bitarray]:
        if isinstance(item, str):
            try:
                return getattr(self, item)  # type: ignore
            except AttributeError:
                raise KeyError(item)
        else:
            raise TypeError(f"Index must be str, not {type(item).__name__}")

    def __eq__(self, other: object) -> bool:
        return all([getattr(self, attr) == getattr(other, attr) for attr in self.__slots__])

    def __hash__(self) -> int:
        return hash(self.raw)

    @property
    def talker(self) -> TalkerID:
        return TalkerID(self.talker_id)


class GatehouseSentence(NMEASentence):
    TYPE = 'HP'

    _slots__ = (
        'country',
        'region',
        'pss',
        'online_data',
        'timestamp',
    )

    def __init__(self, raw: bytes) -> None:
        super().__init__(raw)

        fields = self.data_fields
        try:
            [year, month, day, hour, minute, second, millisecond] = fields[1:8]
            t = datetime.datetime(
                year=int(year),
                month=int(month),
                day=int(day),
                hour=int(hour),
                minute=int(minute),
                second=int(second),
                microsecond=int(millisecond) * 1000
            )
            # MMSI country code where the message originates from
            self.country = fields[8].decode('ascii')
            # The MMSI number of the region
            self.region = fields[9].decode('ascii')
            # MMSI number of the site transponder
            self.pss = fields[10].decode('ascii')
            # buffered data from a BSC will be designated with 0, online data with 1
            self.online_data = int(fields[11])
        except Exception as err:
            raise InvalidNMEAMessageException(raw) from err

        self.timestamp = t


class AISSentence(NMEASentence):
    TYPE = 'AIS'

    __slots__ = (
        'ais_id',
        'frag_cnt',
        'frag_num',
        'seq_id',
        'payload',
        'bit_array',
        'ais_id',
        'channel',
    )

    def __init__(self, raw: bytes) -> None:
        super().__init__(raw)

        try:
            # Unpack NMEA message parts
            (
                message_fragments,
                fragment_number,
                message_id,
                channel,
                payload,
            ) = self.data_fields[:5]

            # Total number of fragments
            self.frag_cnt: int = int(message_fragments)
            # Current fragment index
            self.frag_num: int = int(fragment_number)
            # Optional message index for multiline messages
            self.seq_id: Optional[int] = int(message_id) if message_id else None
            # Channel (A or B)
            self.channel: str = channel.decode('ascii')
            # Decoded message payload as byte string
            self.payload: bytes = payload

        except Exception as err:
            raise InvalidNMEAMessageException(raw) from err

        if len(payload) > MAX_PAYLOAD_LEN:
            raise InvalidNMEAMessageException("AIS payload too large")

        if self.frag_cnt > MAX_FRAG_CNT or self.frag_num > MAX_FRAG_CNT:
            raise InvalidNMEAMessageException("Too many fragments")

        # Finally decode bytes into bits
        self.bit_array: bitarray = decode_into_bit_array(self.payload, self.fill_bits)
        self.ais_id: int = get_int(self.bit_array, 0, 6)

    def asdict(self) -> Dict[str, Any]:
        """
        Convert the class to dict.
        @return: A dictionary that holds all fields, defined in __slots__
        """
        return {
            'ais_id': self.ais_id,  # int
            'raw': self.raw.decode('ascii'),  # str
            'talker': self.talker.value,  # str
            'type': self.type,  # str
            'frag_cnt': self.frag_cnt,  # int
            'frag_num': self.frag_num,  # int
            'seq_id': self.seq_id,  # None or int
            'channel': self.channel,  # str
            'payload': self.payload.decode('ascii'),  # str
            'fill_bits': self.fill_bits,  # int
            'checksum': self.checksum,  # int
            'bit_array': self.bit_array.to01(),  # str
            'is_valid': self.is_valid,  # bool
        }

    def decode_and_merge(self, enum_as_int: bool = False) -> Dict[str, Any]:
        """
        Decodes the message and returns the result as a dict together with all attributes of
        the original NMEA message.
        @param enum_as_int: Set to True to treat IntEnums as pure integers
        @return: A dictionary that holds all fields, defined in __slots__ + the decoded msg
        """
        rlt = self.asdict()
        del rlt['bit_array']
        decoded = self.decode()
        rlt.update(decoded.asdict(enum_as_int))
        return rlt

    @classmethod
    def from_string(cls, nmea_str: str) -> "NMEAMessage":
        return cls(nmea_str.encode('utf-8'))

    @classmethod
    def from_bytes(cls, nmea_byte_str: bytes) -> "NMEAMessage":
        return cls(nmea_byte_str)

    @classmethod
    def assemble_from_iterable(cls, messages: Sequence["AISSentence"]) -> "AISSentence":
        """
        Assemble a multiline message from a sequence of NMEA messages.
        :param messages: Sequence of NMEA messages
        :return: Single message
        """
        raw = b''
        data = b''
        bit_array = bitarray()
        is_valid = True

        for i, msg in enumerate(sorted(messages, key=lambda m: m.frag_num)):
            if i > 0:
                raw += b'\n'
            raw += msg.raw
            data += msg.payload
            bit_array += msg.bit_array
            is_valid &= msg.is_valid

        messages[0].raw = raw
        messages[0].payload = data
        messages[0].bit_array = bit_array
        messages[0].is_valid = is_valid
        return messages[0]

    @property
    def is_single(self) -> bool:
        return not self.seq_id and self.frag_num == self.frag_cnt == 1

    @property
    def is_multi(self) -> bool:
        return not self.is_single

    @property
    def fragment_count(self) -> int:
        return self.frag_cnt

    def decode(self) -> "ANY_MESSAGE":
        """
        Decode the AIS message.
        @return: The decoded message class as a superclass of `Payload`.

        >>> nmea = NMEAMessage(b"!AIVDO,1,1,,,B>qc:003wk?8mP=18D3Q3wgTiT;T,0*13").decode()
        MessageType18(msg_type=18, ...)
        """
        if not self.payload:
            raise MissingPayloadException(self.raw.decode())
        try:
            return MSG_CLASS[self.ais_id].from_bitarray(self.bit_array)
        except KeyError as e:
            raise UnknownMessageException(f"The message {self} is not supported!") from e


@attr.s(slots=True)
class Payload(abc.ABC):
    """
    Payload class
    --------------
    This class serves as an abstract base class for all messages.
    Each message shall inherit from Payload and define it's set of field using the `bit_field` method.
    """

    @staticmethod
    def __force_type(field: typing.Any, val: typing.Any) -> typing.Any:
        """
        Force a value into a specific type for a given bitfield.

        Note:   This method is meant to be used with `bit_fields` only.
        """
        if val is None:
            return val

        d_type = field.metadata['d_type']

        if isinstance(val, d_type):
            # The value is already of the correct type -> nothing to do
            return val

        try:
            coerced_val = coerce_val(val, d_type)
        except ValueError as err:
            raise ValueError(f"Could not coerce value for field '{field.name}'") from err

        return coerced_val

    @classmethod
    def fields(cls) -> typing.Tuple[typing.Any]:
        """
        A list of all fields that were added to this class using attrs.
        """
        return attr.fields(cls)  # type:ignore

    def to_bitarray(self) -> bitarray:
        """
        Convert all attributes of a given Payload/Message to binary.
        """
        out = bitarray()
        for field in self.fields():
            width = field.metadata['width']
            d_type = field.metadata['d_type']
            converter = field.metadata['from_converter']
            signed = field.metadata['signed']
            variable_length = field.metadata['variable_length']

            val = getattr(self, field.name)
            if val is None:
                continue

            val = converter(val) if converter is not None else val

            if d_type in (bool, int):
                bits = int_to_bin(val, width, signed=signed)
            elif d_type == float:
                val = int(val)
                bits = int_to_bin(val, width, signed=signed)
            elif d_type == str:
                trailing_spaces = not variable_length
                bits = str_to_bin(val, width, trailing_spaces=trailing_spaces)
            elif d_type == bytes:
                bits = bytes2bits(val, default=bitarray('0' * width))
            else:
                raise InvalidDataTypeException(d_type)

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
    def create(cls, **kwargs: NMEA_VALUE) -> "ANY_MESSAGE":
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
                val = cls.__force_type(field, kwargs[key])
                args[key] = val
            except KeyError:
                # Check if a default value was provided
                default = field.metadata['default']
                if default is not None:
                    args[key] = default
        return cls(**args)  # type:ignore

    @classmethod
    def from_bitarray(cls, bit_arr: bitarray) -> "ANY_MESSAGE":
        cur: int = 0
        end: int = 0
        length: int = len(bit_arr)
        kwargs: typing.Dict[str, typing.Any] = {}

        # Iterate over the bits until the last bit of the bitarray or all fields are fully decoded
        for field in cls.fields():

            if end >= length:
                # All fields that did not fit into the bit array are None
                kwargs[field.name] = None
                continue

            width = field.metadata['width']
            d_type = field.metadata['d_type']
            converter = field.metadata['to_converter']

            end = min(length, cur + width)
            bits = bit_arr[cur: end]

            val: typing.Any
            # Get the correct data type and decoding function
            if d_type == int or d_type == bool or d_type == float:
                shift = (8 - ((end - cur) % 8)) % 8
                if field.metadata['signed']:
                    val = from_bytes_signed(bits) >> shift
                else:
                    val = from_bytes(bits) >> shift

                if d_type == float:
                    val = float(val)
                elif d_type == bool:
                    val = bool(val)

            elif d_type == str:
                val = decode_bin_as_ascii6(bits)
            elif d_type == bytes:
                val = bits2bytes(bits)
            else:
                raise InvalidDataTypeException(d_type)

            val = converter(val) if converter is not None else val
            kwargs[field.name] = val
            cur = end

        return cls(**kwargs)  # type:ignore

    def asdict(self, enum_as_int: bool = False) -> typing.Dict[str, typing.Optional[NMEA_VALUE]]:
        """
        Convert the message to a dictionary.
        @param enum_as_int: If set to True all Enum values will be returned as raw ints.
        @return: The message as a dictionary.
        """
        if enum_as_int:
            d: typing.Dict[str, typing.Optional[NMEA_VALUE]] = {}
            for slt in self.__slots__:  # type: ignore
                val = getattr(self, slt)
                if val is not None and slt in ENUM_FIELDS:
                    val = int(getattr(self, slt))
                d[slt] = val
            return d
        else:
            return {slt: getattr(self, slt) for slt in self.__slots__}  # type: ignore

    def to_json(self) -> str:
        return AISJSONEncoder(indent=4).encode(self.asdict())


#
# Conversion functions
#

def from_speed(v: typing.Union[int, float]) -> float:
    return v * 10.0


def to_speed(v: typing.Union[int, float]) -> float:
    return v / 10.0


def from_lat_lon(v: typing.Union[int, float]) -> float:
    return round(float(v) * 600000.0)


def to_lat_lon(v: typing.Union[int, float]) -> float:
    return round(float(v) / 600000.0, 6)


def from_lat_lon_600(v: typing.Union[int, float]) -> float:
    return round(float(v) * 600.0)


def to_lat_lon_600(v: typing.Union[int, float]) -> float:
    return round(float(v) / 600.0, 6)


def from_10th(v: typing.Union[int, float]) -> float:
    return float(v) * 10.0


def to_10th(v: typing.Union[int, float]) -> float:
    return v / 10.0


def from_100th(v: typing.Union[int, float]) -> float:
    return float(v) * 100.0


def to_100th(v: typing.Union[int, float]) -> float:
    return v / 100.0


def from_mmsi(v: typing.Union[str, int]) -> int:
    return int(v)


def to_turn(turn: typing.Union[int, float]) -> typing.Union[float, TurnRate]:
    if not turn:
        return 0.0
    elif abs(turn) == 127:
        return TurnRate(turn)
    elif abs(turn) == 128:
        return TurnRate.NO_TI_DEFAULT

    return math.copysign(round((turn / 4.733) ** 2), turn)


def from_turn(turn: typing.Optional[typing.Union[int, float, TurnRate]]) -> int:
    if not turn:
        return 0
    elif abs(turn) == 127 or abs(turn) == 128:
        return int(turn)

    return int(math.copysign(round(4.733 * math.sqrt(abs(turn))), turn))


class CommunicationStateMixin:
    """
    Mixin class to access Communication State values by applicable messages.

    You may refer to 3.3.7.2.1 of:
    https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.1371-1-200108-S!!PDF-E.pdf
    """

    msg_type: int  # Type hint to make mypy happy
    radio: int  # Type hint to make mypy happy

    MAX_COMM_STATE_VALUE = 0x7ffff

    SOTDMA_TYPES = (1, 2, 4, 11)
    SOTDMA_ITDMA_TYPES = (9, 18, 26)

    def get_communication_state(self) -> Dict[str, typing.Optional[int]]:
        """Returns information used by the slot allocation algorithm as a dict."""
        result: Dict[str, typing.Optional[int]] = {
            'received_stations': None,
            'slot_number': None,
            'utc_hour': None,
            'utc_minute': None,
            'slot_offset': None,
            'slot_timeout': None,
            'sync_state': None,
            'keep_flag': None,
            'slot_increment': None,
            'num_slots': None,
        }

        if self.is_sotdma:
            result.update(get_sotdma_comm_state(self.communication_state_raw))
        else:
            result.update(get_itdma_comm_state(self.communication_state_raw))

        return result

    @property
    def is_sotdma(self) -> bool:
        """Messages of type 1, 2, 4, 11 use SOTDMA or 9, 18, 26 if 20th bit is set."""
        if self.msg_type in self.SOTDMA_TYPES:
            return True
        if self.msg_type in self.SOTDMA_ITDMA_TYPES:
            return self.radio <= self.MAX_COMM_STATE_VALUE
        return False

    @property
    def is_itdma(self) -> bool:
        """Messages of type 3 use ITDMA or 9, 18, 26 if 20th bit is set."""
        if self.msg_type == 3:
            return True
        if self.msg_type in self.SOTDMA_ITDMA_TYPES:
            return self.radio > self.MAX_COMM_STATE_VALUE
        return False

    @property
    def communication_state_raw(self) -> int:
        """Get the raw radio status except 20th bit - if present"""
        try:
            return self.radio & self.MAX_COMM_STATE_VALUE
        except AttributeError as err:
            raise ValueError(
                'Communication State is only available for messages with radio field'
            ) from err


@attr.s(slots=True)
class MessageType1(Payload, CommunicationStateMixin):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    msg_type = bit_field(6, int, default=1, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    status = bit_field(4, int, default=NavigationStatus.Undefined, converter=NavigationStatus.from_value, signed=False)
    turn = bit_field(8, float, default=TurnRate.NO_TI_DEFAULT, signed=True, to_converter=to_turn, from_converter=from_turn)
    speed = bit_field(10, float, from_converter=from_speed, to_converter=to_speed, default=0, signed=False)
    accuracy = bit_field(1, bool, default=0, signed=False)
    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, default=0, signed=True)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, default=0, signed=True)
    course = bit_field(12, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    heading = bit_field(9, int, default=0, signed=False)
    second = bit_field(6, int, default=0, signed=False)
    maneuver = bit_field(2, int, default=ManeuverIndicator.UNDEFINED, from_converter=ManeuverIndicator.from_value,
                         to_converter=ManeuverIndicator.from_value, signed=False)
    spare_1 = bit_field(3, bytes, default=b'')
    raim = bit_field(1, bool, default=0)
    radio = bit_field(19, int, default=0, signed=False)


class MessageType2(MessageType1):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    msg_type = bit_field(6, int, default=2)


class MessageType3(MessageType1):
    """
    AIS Vessel position report using ITDMA (Incremental Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    msg_type = bit_field(6, int, default=3)


@attr.s(slots=True)
class MessageType4(Payload, CommunicationStateMixin):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_4_base_station_report
    """
    msg_type = bit_field(6, int, default=4, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    year = bit_field(14, int, default=1970, signed=False)
    month = bit_field(4, int, default=1, signed=False)
    day = bit_field(5, int, default=1, signed=False)
    hour = bit_field(5, int, default=0, signed=False)
    minute = bit_field(6, int, default=0, signed=False)
    second = bit_field(6, int, default=0, signed=False)
    accuracy = bit_field(1, bool, default=0, signed=False)
    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    epfd = bit_field(4, int, default=EpfdType.Undefined, from_converter=EpfdType.from_value, to_converter=EpfdType.from_value,
                     signed=False)
    spare_1 = bit_field(10, bytes, default=b'')
    raim = bit_field(1, bool, default=0)
    radio = bit_field(19, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType5(Payload):
    """
    Static and Voyage Related Data
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_5_static_and_voyage_related_data
    """
    msg_type = bit_field(6, int, default=5, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    ais_version = bit_field(2, int, default=0, signed=False)
    imo = bit_field(30, int, default=0, signed=False)
    callsign = bit_field(42, str, default='')
    shipname = bit_field(120, str, default='')
    ship_type = bit_field(8, int, default=0, from_converter=ShipType.from_value, to_converter=ShipType.from_value)
    to_bow = bit_field(9, int, default=0, signed=False)
    to_stern = bit_field(9, int, default=0, signed=False)
    to_port = bit_field(6, int, default=0, signed=False)
    to_starboard = bit_field(6, int, default=0, signed=False)
    epfd = bit_field(4, int, default=EpfdType.Undefined, from_converter=EpfdType.from_value, to_converter=EpfdType.from_value)
    month = bit_field(4, int, default=0, signed=False)
    day = bit_field(5, int, default=0, signed=False)
    hour = bit_field(5, int, default=0, signed=False)
    minute = bit_field(6, int, default=0, signed=False)
    draught = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    destination = bit_field(120, str, default='')
    dte = bit_field(1, bool, default=0, signed=False)
    spare_1 = bit_field(1, bytes, default=b'')


@attr.s(slots=True)
class MessageType6(Payload):
    """
    Binary Addresses Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_6_binary_addressed_message
    """
    msg_type = bit_field(6, int, default=6)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    seqno = bit_field(2, int, default=0, signed=False)
    dest_mmsi = bit_field(30, int, from_converter=from_mmsi)
    retransmit = bit_field(1, bool, default=False, signed=False)
    spare_1 = bit_field(1, bytes, default=b'')
    dac = bit_field(10, int, default=0, signed=False)
    fid = bit_field(6, int, default=0, signed=False)
    data = bit_field(920, bytes, default=b'', variable_length=True)


@attr.s(slots=True)
class MessageType7(Payload):
    """
    Binary Acknowledge
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_7_binary_acknowledge
    """
    msg_type = bit_field(6, int, default=7, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'')
    mmsi1 = bit_field(30, int, default=0, from_converter=from_mmsi)
    mmsiseq1 = bit_field(2, int, default=0, signed=False)
    mmsi2 = bit_field(30, int, default=0, from_converter=from_mmsi)
    mmsiseq2 = bit_field(2, int, default=0, signed=False)
    mmsi3 = bit_field(30, int, default=0, from_converter=from_mmsi)
    mmsiseq3 = bit_field(2, int, default=0, signed=False)
    mmsi4 = bit_field(30, int, default=0, from_converter=from_mmsi)
    mmsiseq4 = bit_field(2, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType8(Payload):
    @classmethod
    def create(cls, **kwargs: typing.Union[str, float, int, bool, bytes]) -> "ANY_MESSAGE":
        dac: int = int(kwargs.get("dac", 0))
        fid: int = int(kwargs.get("fid", 0))
        if dac == 200 and fid == 10:
            return MessageType8Dac200Fid10.create(**kwargs)
        else:
            return MessageType8Default.create(**kwargs)

    @classmethod
    def from_bitarray(cls, bit_arr: bitarray) -> "ANY_MESSAGE":
        dac: int = get_int(bit_arr, 40, 50)
        fid: int = get_int(bit_arr, 50, 56)
        if dac == 200 and fid == 10:
            return MessageType8Dac200Fid10.from_bitarray(bit_arr)
        else:
            return MessageType8Default.from_bitarray(bit_arr)


@attr.s(slots=True)
class MessageType8Default(Payload):
    """
    Binary Acknowledge
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_8_binary_broadcast_message
    """

    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b"")
    dac = bit_field(10, int, default=0, signed=False)
    fid = bit_field(6, int, default=0, signed=False)
    data = bit_field(952, bytes, default=b"", variable_length=True)


@attr.s(slots=True)
class MessageType8Dac200Fid10(Payload):
    """
    Binary Acknowledge
    Inland variant with dac=200, fid=10

    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_8_binary_broadcast_message
    Msg variant: ECE/TRANS/SC.3/176 page 37
    https://unece.org/fileadmin/DAM/trans/doc/finaldocs/sc3/ECE-TRANS-SC3-176e.pdf
    """

    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b"")
    dac = bit_field(10, int, default=0, signed=False)
    fid = bit_field(6, int, default=0, signed=False)
    # Unique European Vessel Identification Number / ERI number
    vin = bit_field(48, str, default="")
    # 1 - 8000 (rest not to be used) length of ship in 1/10m 0 = default
    length = bit_field(13, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    # 1 - 1000 (rest not to be used) beam of ship in 1/10m; 0 = default
    beam = bit_field(10, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    # Numeric ERI Classification (CODES):
    # 1 Vessel and Convoy Type as described in ANNEX
    # E ERI ship types
    shiptype = bit_field(14, int, default=0, signed=False)
    # Number of blue cones/lights 0 - 3;
    # 4 = B-Flag, 5 = default = unknown
    hazard = bit_field(3, int, default=5, signed=False)
    # 1 - 2000 (rest not used) draught in 1/100m, 0 = default = unknown
    draught = bit_field(
        11,
        float,
        from_converter=from_100th,
        to_converter=to_100th,
        default=0,
        signed=False,
    )
    # 1 = loaded, 2 = unloaded, 0 = not available/default,, 3 should not be used
    # InlandLoadedType
    loaded = bit_field(
        2,
        int,
        default=InlandLoadedType.NotAvailable,
        from_converter=InlandLoadedType.from_value,
        to_converter=InlandLoadedType.from_value,
        signed=False,
    )
    speed_q = bit_field(1, bool, default=False)
    course_q = bit_field(1, bool, default=False)
    heading_q = bit_field(1, bool, default=False)
    spare = bit_field(8, bytes, default=0)


@attr.s(slots=True)
class MessageType9(Payload, CommunicationStateMixin):
    """
    Standard SAR Aircraft Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_9_standard_sar_aircraft_position_report
    """
    msg_type = bit_field(6, int, default=9, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    alt = bit_field(12, int, default=0, signed=False)
    # speed over ground is in knots, not deciknots
    speed = bit_field(10, float, default=0, signed=False)
    accuracy = bit_field(1, bool, default=0, signed=False)
    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    course = bit_field(12, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    second = bit_field(6, int, default=0, signed=False)

    reserved_1 = bit_field(8, int, default=0)
    dte = bit_field(1, bool, default=0)
    spare_1 = bit_field(3, bytes, default=b'')
    assigned = bit_field(1, bool, default=0)
    raim = bit_field(1, bool, default=0)
    radio = bit_field(20, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType10(Payload):
    """
    UTC/Date Inquiry
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_10_utc_date_inquiry
    """
    msg_type = bit_field(6, int, default=10, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'')
    dest_mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_2 = bit_field(2, bytes, default=b'')


class MessageType11(MessageType4):
    """
    UTC/Date Response
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_11_utc_date_response
    """
    msg_type = bit_field(6, int, default=11, signed=False)


@attr.s(slots=True)
class MessageType12(Payload):
    """
    Addressed Safety-Related Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_12_addressed_safety_related_message
    """
    msg_type = bit_field(6, int, default=12, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    seqno = bit_field(2, int, default=0, signed=False)
    dest_mmsi = bit_field(30, int, from_converter=from_mmsi)
    retransmit = bit_field(1, bool, default=False, signed=False)
    spare_1 = bit_field(1, bytes, default=b'')
    text = bit_field(936, str, default='', variable_length=True)


class MessageType13(MessageType7):
    """
    Identical to type 7
    """
    msg_type = bit_field(6, int, default=13, signed=False)


@attr.s(slots=True)
class MessageType14(Payload):
    """
    Safety-Related Broadcast Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_14_safety_related_broadcast_message
    """
    msg_type = bit_field(6, int, default=14, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'')
    text = bit_field(968, str, default='', variable_length=True)


@attr.s(slots=True)
class MessageType15(Payload):
    """
    Interrogation
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_15_interrogation
    """
    msg_type = bit_field(6, int, default=15, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'')
    mmsi1 = bit_field(30, int, default=0, from_converter=from_mmsi)
    type1_1 = bit_field(6, int, default=0, signed=False)
    offset1_1 = bit_field(12, int, default=0, signed=False)
    spare_2 = bit_field(2, bytes, default=b'')
    type1_2 = bit_field(6, int, default=0, signed=False)
    offset1_2 = bit_field(12, int, default=0, signed=False)
    spare_3 = bit_field(2, bytes, default=b'')
    mmsi2 = bit_field(30, int, default=0, from_converter=from_mmsi)
    type2_1 = bit_field(6, int, default=0, signed=False)
    offset2_1 = bit_field(12, int, default=0, signed=False)
    spare_4 = bit_field(2, bytes, default=b'')


@attr.s(slots=True)
class MessageType16(Payload):
    """
    Assignment Mode Command
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_16_assignment_mode_command
    """
    msg_type = bit_field(6, int, default=16, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'')

    mmsi1 = bit_field(30, int, default=0, from_converter=from_mmsi)
    offset1 = bit_field(12, int, default=0, signed=False)
    increment1 = bit_field(10, int, default=0, signed=False)

    mmsi2 = bit_field(30, int, default=0, from_converter=from_mmsi)
    offset2 = bit_field(12, int, default=0, signed=False)
    increment2 = bit_field(10, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType17(Payload):
    """
    DGNSS Broadcast Binary Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_17_dgnss_broadcast_binary_message
    """
    msg_type = bit_field(6, int, default=17, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'')
    # Note that latitude and longitude are in units of a tenth of a minute
    lon = bit_field(18, float, from_converter=from_10th, to_converter=to_10th, default=0)
    lat = bit_field(17, float, from_converter=from_10th, to_converter=to_10th, default=0)
    spare_2 = bit_field(5, bytes, default=b'')
    data = bit_field(736, bytes, default=b'', variable_length=True)


@attr.s(slots=True)
class MessageType18(Payload, CommunicationStateMixin):
    """
    Standard Class B CS Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_18_standard_class_b_cs_position_report
    """
    msg_type = bit_field(6, int, default=18, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    reserved_1 = bit_field(8, int, default=0, signed=False)
    speed = bit_field(10, float, from_converter=from_speed, to_converter=to_speed, default=0, signed=False)
    accuracy = bit_field(1, bool, default=0, signed=False)
    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    course = bit_field(12, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    heading = bit_field(9, int, default=0, signed=False)
    second = bit_field(6, int, default=0, signed=False)
    reserved_2 = bit_field(2, int, default=0, signed=False)
    cs = bit_field(1, bool, default=0, signed=False)
    display = bit_field(1, bool, default=0)
    dsc = bit_field(1, bool, default=0)
    band = bit_field(1, bool, default=0)
    msg22 = bit_field(1, bool, default=0)
    assigned = bit_field(1, bool, default=0)
    raim = bit_field(1, bool, default=0)
    radio = bit_field(20, int, default=0)


@attr.s(slots=True)
class MessageType19(Payload):
    """
    Extended Class B CS Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_19_extended_class_b_cs_position_report
    """
    msg_type = bit_field(6, int, default=19, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    reserved_1 = bit_field(8, int, default=0)

    speed = bit_field(10, float, from_converter=from_speed, to_converter=to_speed, default=0, signed=False)
    accuracy = bit_field(1, bool, default=0, signed=False)
    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    course = bit_field(12, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    heading = bit_field(9, int, default=0, signed=False)
    second = bit_field(6, int, default=0, signed=False)
    reserved_2 = bit_field(4, int, default=0, signed=False)
    shipname = bit_field(120, str, default='')
    ship_type = bit_field(8, int, default=0, from_converter=ShipType.from_value, to_converter=ShipType.from_value,
                          signed=False)
    to_bow = bit_field(9, int, default=0, signed=False)
    to_stern = bit_field(9, int, default=0, signed=False)
    to_port = bit_field(6, int, default=0, signed=False)
    to_starboard = bit_field(6, int, default=0, signed=False)
    epfd = bit_field(4, int, default=EpfdType.Undefined, from_converter=EpfdType.from_value, to_converter=EpfdType.from_value)
    raim = bit_field(1, bool, default=0)
    dte = bit_field(1, bool, default=0)
    assigned = bit_field(1, bool, default=0, signed=False)
    spare_1 = bit_field(4, bytes, default=b'')


@attr.s(slots=True)
class MessageType20(Payload):
    """
    Data Link Management Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_20_data_link_management_message
    """
    msg_type = bit_field(6, int, default=20, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'')

    offset1 = bit_field(12, int, default=0, signed=False)
    number1 = bit_field(4, int, default=0, signed=False)
    timeout1 = bit_field(3, int, default=0, signed=False)
    increment1 = bit_field(11, int, default=0, signed=False)

    offset2 = bit_field(12, int, default=0, signed=False)
    number2 = bit_field(4, int, default=0, signed=False)
    timeout2 = bit_field(3, int, default=0, signed=False)
    increment2 = bit_field(11, int, default=0, signed=False)

    offset3 = bit_field(12, int, default=0, signed=False)
    number3 = bit_field(4, int, default=0, signed=False)
    timeout3 = bit_field(3, int, default=0, signed=False)
    increment3 = bit_field(11, int, default=0, signed=False)

    offset4 = bit_field(12, int, default=0, signed=False)
    number4 = bit_field(4, int, default=0, signed=False)
    timeout4 = bit_field(3, int, default=0, signed=False)
    increment4 = bit_field(11, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType21(Payload):
    """
    Aid-to-Navigation Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_21_aid_to_navigation_report
    """
    msg_type = bit_field(6, int, default=21, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    aid_type = bit_field(5, int, default=0, from_converter=NavAid.from_value, to_converter=NavAid.from_value,
                         signed=False)
    name = bit_field(120, str, default='')

    accuracy = bit_field(1, bool, default=0, signed=False)
    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    to_bow = bit_field(9, int, default=0, signed=False)
    to_stern = bit_field(9, int, default=0, signed=False)
    to_port = bit_field(6, int, default=0, signed=False)
    to_starboard = bit_field(6, int, default=0, signed=False)

    epfd = bit_field(4, int, default=EpfdType.Undefined, from_converter=EpfdType.from_value, to_converter=EpfdType.from_value)
    second = bit_field(6, int, default=0, signed=False)
    off_position = bit_field(1, bool, default=0)
    reserved_1 = bit_field(8, int, default=0, signed=False)
    raim = bit_field(1, bool, default=0)
    virtual_aid = bit_field(1, bool, default=0)
    assigned = bit_field(1, bool, default=0)
    spare_1 = bit_field(1, bytes, default=b'')
    name_ext = bit_field(88, str, default='')

    @functools.cached_property
    def full_name(self) -> str:
        """The name field is up to 20 characters of 6-bit ASCII. If this field
        is full (has no trailing @ characters) the decoder should interpret
        the Name Extension field later in the message (no more than 14 6-bit
        characters) and concatenate it to this one to obtain the full name."""
        if self.name:
            if self.name_ext:
                return f"{self.name}{self.name_ext}"
            return str(self.name)
        return ""


@attr.s(slots=True)
class MessageType22Addressed(Payload):
    """
    Channel Management
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_22_channel_management
    """
    msg_type = bit_field(6, int, default=22, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'')

    channel_a = bit_field(12, int, default=0, signed=False)
    channel_b = bit_field(12, int, default=0, signed=False)
    txrx = bit_field(4, int, default=0, signed=False)
    power = bit_field(1, bool, default=0)  # 69 bits

    # If it is addressed (addressed field is 1),
    # the same span of data is interpreted as two 30-bit MMSIs
    # beginning at bit offsets 69 and 104 respectively.
    dest1 = bit_field(30, int, default=0, from_converter=from_mmsi)
    empty_1 = bit_field(5, int, default=0)
    dest2 = bit_field(30, int, default=0, from_converter=from_mmsi)
    empty_2 = bit_field(5, int, default=0)

    addressed = bit_field(1, bool, default=0)
    band_a = bit_field(1, bool, default=0)
    band_b = bit_field(1, bool, default=0)
    zonesize = bit_field(3, int, default=0)
    spare_2 = bit_field(23, bytes, default=b'')


@attr.s(slots=True)
class MessageType22Broadcast(Payload):
    """
    Channel Management
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_22_channel_management
    """
    msg_type = bit_field(6, int, default=22, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'')

    channel_a = bit_field(12, int, default=0, signed=False)
    channel_b = bit_field(12, int, default=0, signed=False)
    txrx = bit_field(4, int, default=0, signed=False)
    power = bit_field(1, bool, default=0)

    # If the message is broadcast (addressed field is 0),
    # the ne_lon, ne_lat, sw_lon, and sw_lat fields are the
    # corners of a rectangular jurisdiction area over which control parameter
    # ne_lon, ne_lat, sw_lon, and sw_lat fields are in 0.1 minutes
    ne_lon = bit_field(18, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    ne_lat = bit_field(17, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    sw_lon = bit_field(18, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    sw_lat = bit_field(17, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)

    addressed = bit_field(1, bool, default=0)
    band_a = bit_field(1, bool, default=0)
    band_b = bit_field(1, bool, default=0)
    zonesize = bit_field(3, int, default=0, signed=False)
    spare_2 = bit_field(23, bytes, default=b'')


class MessageType22(Payload):
    """
    Type 22 messages are different from other messages:
        The encoding differs depending on the `addressed` field. If the message is broadcast
        (addressed field is 0), the ne_lon, ne_lat, sw_lon, and sw_lat fields are the
        corners of a rectangular jurisdiction area over which control parameters are to
        be set. If it is addressed (addressed field is 1),
        the same span of data is interpreted as two 30-bit MMSIs beginning
        at bit offsets 69 and 104 respectively.
    """

    @classmethod
    def create(cls, **kwargs: typing.Union[str, float, int, bool, bytes]) -> "ANY_MESSAGE":
        if kwargs.get('addressed', False):
            return MessageType22Addressed.create(**kwargs)
        else:
            return MessageType22Broadcast.create(**kwargs)

    @classmethod
    def from_bitarray(cls, bit_arr: bitarray) -> "ANY_MESSAGE":
        if get_int(bit_arr, 139, 140):
            return MessageType22Addressed.from_bitarray(bit_arr)
        else:
            return MessageType22Broadcast.from_bitarray(bit_arr)


@attr.s(slots=True)
class MessageType23(Payload):
    """
    Group Assignment Command
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_23_group_assignment_command
    """
    msg_type = bit_field(6, int, default=23, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'')

    ne_lon = bit_field(18, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    ne_lat = bit_field(17, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    sw_lon = bit_field(18, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    sw_lat = bit_field(17, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)

    station_type = bit_field(4, int, default=0, from_converter=StationType.from_value,
                             to_converter=StationType.from_value)
    ship_type = bit_field(8, int, default=0, from_converter=ShipType.from_value, to_converter=ShipType.from_value)
    spare_2 = bit_field(22, bytes, default=b'')

    txrx = bit_field(2, int, default=0, from_converter=TransmitMode.from_value, to_converter=TransmitMode.from_value,
                     signed=False)
    interval = bit_field(4, int, default=0, from_converter=StationIntervals.from_value,
                         to_converter=StationIntervals.from_value)
    quiet = bit_field(4, int, default=0, signed=False)
    spare_3 = bit_field(6, bytes, default=b'')


@attr.s(slots=True)
class MessageType24PartA(Payload):
    msg_type = bit_field(6, int, default=24, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    partno = bit_field(2, int, default=0, signed=False)
    shipname = bit_field(120, str, default='')
    spare_1 = bit_field(8, bytes, default=b'')


@attr.s(slots=True)
class MessageType24PartB(Payload):
    msg_type = bit_field(6, int, default=24, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    partno = bit_field(2, int, default=0, signed=False)
    ship_type = bit_field(8, int, default=0, signed=False)
    vendorid = bit_field(18, str, default='', signed=False)
    model = bit_field(4, int, default=0, signed=False)
    serial = bit_field(20, int, default=0, signed=False)
    callsign = bit_field(42, str, default='')

    to_bow = bit_field(9, int, default=0, signed=False)
    to_stern = bit_field(9, int, default=0, signed=False)
    to_port = bit_field(6, int, default=0, signed=False)
    to_starboard = bit_field(6, int, default=0, signed=False)

    spare_1 = bit_field(6, bytes, default=b'')


class MessageType24(Payload):
    """
    Static Data Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_24_static_data_report

    Just like message type 22, this message encodes different fields depending
    on the `partno` field.
    If the Part Number field is 0, the rest of the message is interpreted as a Part A; if it is 1,
    the rest of the message is interpreted as a Part B;
    """

    @classmethod
    def create(cls, **kwargs: typing.Union[str, float, int, bool, bytes]) -> "ANY_MESSAGE":
        partno: int = int(kwargs.get('partno', 0))
        if partno == 0:
            return MessageType24PartA.create(**kwargs)
        elif partno == 1:
            return MessageType24PartB.create(**kwargs)
        else:
            raise UnknownPartNoException(f"Partno {partno} is not allowed!")

    @classmethod
    def from_bitarray(cls, bit_arr: bitarray) -> "ANY_MESSAGE":
        partno: int = get_int(bit_arr, 38, 40)
        if partno == 0:
            return MessageType24PartA.from_bitarray(bit_arr)
        elif partno == 1:
            return MessageType24PartB.from_bitarray(bit_arr)
        else:
            raise UnknownPartNoException(f"Partno {partno} is not allowed!")


@attr.s(slots=True)
class MessageType25AddressedStructured(Payload):
    msg_type = bit_field(6, int, default=25, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    dest_mmsi = bit_field(30, int, default=0, from_converter=from_mmsi, signed=False)
    app_id = bit_field(16, int, default=0, signed=False)
    data = bit_field(82, bytes, default=b'')


@attr.s(slots=True)
class MessageType25BroadcastStructured(Payload):
    msg_type = bit_field(6, int, default=25, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    app_id = bit_field(16, int, default=0, signed=False)
    data = bit_field(112, bytes, default=b'', )


@attr.s(slots=True)
class MessageType25AddressedUnstructured(Payload):
    msg_type = bit_field(6, int, default=25, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    dest_mmsi = bit_field(30, int, default=0, from_converter=from_mmsi)
    data = bit_field(98, bytes, default=b'')


@attr.s(slots=True)
class MessageType25BroadcastUnstructured(Payload):
    msg_type = bit_field(6, int, default=25, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    data = bit_field(128, bytes, default=b'')


class MessageType25(Payload):
    """
    Single Slot Binary Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_25_single_slot_binary_message

    NOTE: This message type is quite uncommon and
    I was not able find any real world occurrence of the type.
    Also documentation seems to vary. Use with caution.
    """

    @classmethod
    def create(cls, **kwargs: typing.Union[str, float, int, bool, bytes]) -> "ANY_MESSAGE":
        addressed = kwargs.get('addressed', False)
        structured = kwargs.get('structured', False)

        if addressed:
            if structured:
                return MessageType25AddressedStructured.create(**kwargs)
            else:
                return MessageType25AddressedUnstructured.create(**kwargs)
        else:
            if structured:
                return MessageType25BroadcastStructured.create(**kwargs)
            else:
                return MessageType25BroadcastUnstructured.create(**kwargs)

    @classmethod
    def from_bitarray(cls, bit_arr: bitarray) -> "ANY_MESSAGE":
        addressed: int = get_int(bit_arr, 38, 39)
        structured: int = get_int(bit_arr, 39, 40)

        if addressed:
            if structured:
                return MessageType25AddressedStructured.from_bitarray(bit_arr)
            else:
                return MessageType25AddressedUnstructured.from_bitarray(bit_arr)
        else:
            if structured:
                return MessageType25BroadcastStructured.from_bitarray(bit_arr)
            else:
                return MessageType25BroadcastUnstructured.from_bitarray(bit_arr)


@attr.s(slots=True)
class MessageType26AddressedStructured(Payload, CommunicationStateMixin):
    msg_type = bit_field(6, int, default=26, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    dest_mmsi = bit_field(30, int, default=0, from_converter=from_mmsi)
    app_id = bit_field(16, int, default=0, signed=False)
    data = bit_field(958, bytes, default=b'')
    radio = bit_field(20, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType26BroadcastStructured(Payload, CommunicationStateMixin):
    msg_type = bit_field(6, int, default=26, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    app_id = bit_field(16, int, default=0, signed=False)
    data = bit_field(988, bytes, default=b'')
    radio = bit_field(20, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType26AddressedUnstructured(Payload, CommunicationStateMixin):
    msg_type = bit_field(6, int, default=26, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    dest_mmsi = bit_field(30, int, default=0, from_converter=from_mmsi)
    app_id = bit_field(16, int, default=0, signed=False)
    data = bit_field(958, bytes, default=b'')
    radio = bit_field(20, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType26BroadcastUnstructured(Payload, CommunicationStateMixin):
    msg_type = bit_field(6, int, default=26, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    data = bit_field(1004, bytes, default=b'')
    radio = bit_field(20, int, default=0, signed=False)


class MessageType26(Payload):
    """
    Multiple Slot Binary Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_26_multiple_slot_binary_message

    NOTE: This message type is quite uncommon and
    I was not able find any real world occurrence of the type.
    Also documentation seems to vary. Use with caution.
    """

    @classmethod
    def create(cls, **kwargs: typing.Union[str, float, int, bool, bytes]) -> "ANY_MESSAGE":
        addressed = kwargs.get('addressed', False)
        structured = kwargs.get('structured', False)

        if addressed:
            if structured:
                return MessageType26AddressedStructured.create(**kwargs)
            else:
                return MessageType26AddressedUnstructured.create(**kwargs)
        else:
            if structured:
                return MessageType26AddressedStructured.create(**kwargs)
            else:
                return MessageType26BroadcastUnstructured.create(**kwargs)

    @classmethod
    def from_bitarray(cls, bit_arr: bitarray) -> "ANY_MESSAGE":
        addressed: int = get_int(bit_arr, 38, 39)
        structured: int = get_int(bit_arr, 39, 40)

        if addressed:
            if structured:
                return MessageType26AddressedStructured.from_bitarray(bit_arr)
            else:
                return MessageType26BroadcastStructured.from_bitarray(bit_arr)
        else:
            if structured:
                return MessageType26AddressedUnstructured.from_bitarray(bit_arr)
            else:
                return MessageType26BroadcastUnstructured.from_bitarray(bit_arr)


@attr.s(slots=True)
class MessageType27(Payload):
    """
    Long Range AIS Broadcast message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_27_long_range_ais_broadcast_message
    """
    msg_type = bit_field(6, int, default=27, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    accuracy = bit_field(1, bool, default=0, signed=False)
    raim = bit_field(1, bool, default=0, signed=False)
    status = bit_field(4, int, default=NavigationStatus.Undefined, from_converter=NavigationStatus, to_converter=NavigationStatus, signed=False)
    lon = bit_field(18, float, from_converter=from_lat_lon_600, to_converter=to_lat_lon_600, default=0, signed=True)
    lat = bit_field(17, float, from_converter=from_lat_lon_600, to_converter=to_lat_lon_600, default=0, signed=True)
    speed = bit_field(6, float, default=0, signed=False)
    course = bit_field(9, float, default=0, signed=False)
    gnss = bit_field(1, bool, default=0, signed=False)
    spare_1 = bit_field(1, bytes, default=b'')


MSG_CLASS = {
    0: MessageType1,  # there are messages with a zero (0) as an id. these seem to be the same as type 1 messages
    1: MessageType1,
    2: MessageType2,
    3: MessageType3,
    4: MessageType4,
    5: MessageType5,
    6: MessageType6,
    7: MessageType7,
    8: MessageType8,
    9: MessageType9,
    10: MessageType10,
    11: MessageType11,
    12: MessageType12,
    13: MessageType13,
    14: MessageType14,
    15: MessageType15,
    16: MessageType16,
    17: MessageType17,
    18: MessageType18,
    19: MessageType19,
    20: MessageType20,
    21: MessageType21,
    22: MessageType22,
    23: MessageType23,
    24: MessageType24,
    25: MessageType25,
    26: MessageType26,
    27: MessageType27,
}

# This is type hint for all messages
ANY_MESSAGE = typing.Union[
    MessageType1,
    MessageType2,
    MessageType3,
    MessageType4,
    MessageType5,
    MessageType6,
    MessageType7,
    MessageType8Default,
    MessageType8Dac200Fid10,
    MessageType9,
    MessageType10,
    MessageType11,
    MessageType12,
    MessageType13,
    MessageType14,
    MessageType15,
    MessageType16,
    MessageType17,
    MessageType18,
    MessageType19,
    MessageType20,
    MessageType21,
    MessageType22Addressed,
    MessageType22Broadcast,
    MessageType23,
    MessageType24PartA,
    MessageType24PartB,
    MessageType25AddressedStructured,
    MessageType25AddressedUnstructured,
    MessageType25BroadcastStructured,
    MessageType25BroadcastUnstructured,
    MessageType26AddressedStructured,
    MessageType26AddressedUnstructured,
    MessageType26BroadcastStructured,
    MessageType26BroadcastUnstructured,
    MessageType27,
]

# This is only there for backwards compatibility
NMEAMessage = AISSentence

import abc
import datetime
import functools
import json
import math
import typing
from typing import Any, Dict, Optional, Sequence, Union

import attr

from pyais.bit_vector import bit_vector
from pyais.constants import (
    AtoNDimensionType,
    AtoNRestrictedUseInidicator,
    AtoNSationType,
    EMMATypeCodes,
    EMMAWinds,
    IceClass,
    SOLASStatus,
    SignalImpact,
    SignalStatus,
    TalkerID,
    NavigationStatus,
    ManeuverIndicator,
    EpfdType,
    ShipType,
    NavAid,
    StationType,
    TransmitMode,
    StationIntervals,
    TurnRate,
    InlandLoadedType
)
from pyais.exceptions import InvalidNMEAMessageException, TagBlockNotInitializedException, UnknownMessageException, UnknownPartNoException, \
    InvalidDataTypeException, MissingPayloadException
from pyais.util import SIX_BIT_ENCODING, ParsedDimensions, SixBitNibleEncoder, checksum, compute_checksum, decode_bytes_as_ascii6, get_itdma_comm_state, get_sotdma_comm_state, chk_to_int, coerce_val, b64encode_str, is_auxiliary_craft, parse_dimensions

NMEA_VALUE = typing.Union[str, float, int, bool, bytes]
_ConverterFunc = typing.Callable[[NMEA_VALUE,], NMEA_VALUE]
_DecoderPlan = list[tuple[str, int, int, bool, int, _ConverterFunc]]
INT, BOOL, FLOAT, STR, BYTES = 0, 1, 2, 3, 4

B_EXCLAMATION_MARK = b"!"
B_DOLLAR_SIGN = b"$"
ASTERISK = b"*"
COMMA = b","
B_VDM = b"VDM"
B_VDO = b"VDO"
B_GH = b"HP"
TAG_BLOCK_START = b'\\'
TAG_BLOCK_START_ORD = TAG_BLOCK_START[0]
MAX_FRAG_CNT = 100
MAX_PAYLOAD_LEN = 200

# A stream carries only a handful of distinct sentence tags (b'!AIVDM',
# b'!BSVDM', ...) and channels, repeated for every single line. Splitting and
# decoding them once and caching the result turns a few slices plus two ASCII
# decodes into a single dict lookup. The caches are capped so that a malformed
# or hostile feed cannot grow them without bound.
_MAX_PARSE_CACHE = 512
_TAG_CACHE: typing.Dict[bytes, typing.Tuple[bytes, str, str]] = {}
_ASCII_CACHE: typing.Dict[bytes, str] = {}
# Fragment counts and sequence ids are small decimal numbers written the same
# way every time; int() is comparatively expensive for such short inputs.
_SMALL_INTS: typing.Dict[bytes, int] = {str(i).encode(): i for i in range(256)}
# The trailing '<fill>*<checksum>' field has only a few thousand possible
# values, so it repeats constantly across a stream. Caching the parse avoids a
# split plus two int() conversions per sentence.
_MAX_CHK_CACHE = 4096
_CHK_CACHE: typing.Dict[bytes, typing.Tuple[int, int]] = {}


def _split_tag(first_field: bytes) -> typing.Tuple[bytes, str, str]:
    """Split a sentence tag into (delimiter, talker id, type code) and cache it."""
    tag = (
        first_field[:1],
        first_field[1:3].decode('ascii'),
        first_field[3:].decode('ascii'),
    )
    if len(_TAG_CACHE) >= _MAX_PARSE_CACHE:
        _TAG_CACHE.clear()
    _TAG_CACHE[first_field] = tag
    return tag


def _ascii(raw: bytes) -> str:
    """Decode a short, frequently repeated ASCII field, with caching."""
    val = raw.decode('ascii')
    if len(_ASCII_CACHE) >= _MAX_PARSE_CACHE:
        _ASCII_CACHE.clear()
    _ASCII_CACHE[raw] = val
    return val


def bit_field(
    width: int,
    d_type: typing.Type[typing.Any],
    from_converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
    to_converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
    default: typing.Optional[typing.Any] = None,
    signed: bool = False,
    variable_length: bool = False,
    is_spare: bool = False,
    **kwargs: typing.Any
) -> typing.Any:
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
            'is_spare': is_spare,
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
    def _pre_process(cls, raw: bytes) -> typing.Tuple[bytes, typing.Optional[bytes]]:
        """
        Preprocess the sentence.
        If the sentence has no tag block it is returned as is.
        Otherwise the tag block and NMEA sentence are separated
        Example with tag block:
        >>> NMEASentenceFactory._pre_process(b'\\s:2573535,c:1671533231*08\\!BSVDM,2,2,8,B,00000000000,2*36')
        (b'!BSVDM,2,2,8,B,00000000000,2*36', b's:2573535,c:1671533231*08')
        """
        raw = raw.strip()

        if raw[0] == TAG_BLOCK_START_ORD:
            ix_start = 0
            ix_end = raw[1:].find(TAG_BLOCK_START) + 1
            tag_block = raw[ix_start + 1:ix_end]

            return raw[ix_end + 1:], tag_block

        return raw, None

    @classmethod
    def produce(cls, raw: bytes) -> "NMEASentence":
        """Parse a single bytes string into an NMEA sentence."""
        if not isinstance(raw, bytes):
            raise TypeError("message must be bytes")

        if len(raw) == 0:
            raise InvalidNMEAMessageException("empty bytes")

        # The common case, a plain sentence with no tag block, is handled inline
        raw_sentence = raw.strip()
        tb = None
        if raw_sentence[0] == TAG_BLOCK_START_ORD:
            raw_sentence, tb = cls._pre_process(raw_sentence)

        # [b'!AIVDM', b'1', b'1', b'', b'B', b'133S0:0P00PCsJ:MECBR0gv:0D8N', b'0*7F']
        fields = raw_sentence.split(COMMA)

        # b'!AIVDM'
        first_field = fields[0]

        # Almost every sentence is already upper case; only pay for .upper()
        # when the tag does not match as-is.
        type_code = first_field[3:]
        if type_code != B_VDM and type_code != B_VDO:
            type_code = type_code.upper()

        if type_code == B_VDM or type_code == B_VDO:
            sentence: NMEASentence = AISSentence(raw_sentence, fields)
        elif first_field[:1] == B_DOLLAR_SIGN and type_code == B_GH:
            sentence = GatehouseSentence(raw_sentence, fields)
        else:
            raise UnknownMessageException(raw_sentence)

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
        msg_id, msg_total, group_id = raw.split("-", 3)

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

    def to_raw(self) -> bytes:
        """Convert a tag block to raw bytes"""
        fields = []
        if self._group is not None:
            fields.append(f"g:{self._group}")
        if self._source_station is not None:
            fields.append(f"s:{self._source_station}")
        if self._receiver_timestamp is not None:
            fields.append(f"c:{self._receiver_timestamp}")
        if self._destination_station is not None:
            fields.append(f"d:{self._destination_station}")
        if self._line_count is not None:
            fields.append(f"n:{self._line_count}")
        if self._relative_time is not None:
            fields.append(f"r:{self._relative_time}")
        if self._text is not None:
            fields.append(f"t:{self._text}")

        if not fields:
            raise ValueError('can not convert empty tag block to bytes (forgot to call .init()?)')

        payload_str = ','.join(fields)
        payload = payload_str.encode()

        chk_int = checksum(payload)
        chk = f"{chk_int:02X}".encode()

        return payload + ASTERISK + chk


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
        '_is_valid',
        'wrapper_msg',
        'tag_block',
    )

    TYPE = "UNDEFINED"

    def __init__(self, raw: bytes, fields: typing.Optional[typing.List[bytes]] = None) -> None:
        if not isinstance(raw, bytes):
            raise ValueError(f"'NMEAMessage' only accepts bytes, but got '{type(raw)}'")

        # Store raw data
        self.raw: bytes = raw

        # A NMEA message consists of comma separated parts. The factory has
        # usually split them already - only split again when called directly.
        if fields is None:
            fields = raw.split(COMMA)

        # The first field of a sentence is called the "tag" and normally consists
        # of a two-letter talker ID followed by a three-letter type code.
        first_field = fields[0]  # b'!AIVDM'
        tag = _TAG_CACHE.get(first_field)
        if tag is None:
            tag = _split_tag(first_field)  # (b'!', 'AI', 'VDM')}
        self.delimiter, self.talker_id, self.type = tag

        checksum_field = fields[-1]  # b'0*45'
        parsed = _CHK_CACHE.get(checksum_field)
        if parsed is None:
            parsed = chk_to_int(checksum_field)
            if len(_CHK_CACHE) >= _MAX_CHK_CACHE:
                _CHK_CACHE.clear()
            _CHK_CACHE[checksum_field] = parsed
        # Fill bits (0 to 5) and message checksum (hex value)
        self.fill_bits: int = parsed[0]
        self.checksum = parsed[1]

        # Set the checksum valid field
        self._is_valid: bool | None = None

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

    def __getitem__(self, item: str) -> Union[int, str, bytes]:
        if isinstance(item, str):
            try:
                return getattr(self, item)  # type: ignore
            except AttributeError:
                raise KeyError(item)
        else:
            raise TypeError(f"Index must be str, not {type(item).__name__}")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NMEASentence) and self.raw == other.raw

    def __hash__(self) -> int:
        return hash(self.raw)

    @property
    def talker(self) -> TalkerID:
        return TalkerID(self.talker_id)

    @property
    def is_valid(self) -> bool:
        if self._is_valid is None:
            self._is_valid = self.checksum == compute_checksum(self.raw)
        return self._is_valid

    @is_valid.setter
    def is_valid(self, val: bool) -> None:
        self._is_valid = val


class GatehouseSentence(NMEASentence):
    TYPE = 'HP'

    __slots__ = (
        'country',
        'region',
        'pss',
        'online_data',
        'timestamp',
    )

    def __init__(self, raw: bytes, fields: typing.Optional[typing.List[bytes]] = None) -> None:
        super().__init__(raw, fields)

        data_fields = self.data_fields
        try:
            [year, month, day, hour, minute, second, millisecond] = data_fields[1:8]
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
            self.country = data_fields[8].decode('ascii')
            # The MMSI number of the region
            self.region = data_fields[9].decode('ascii')
            # MMSI number of the site transponder
            self.pss = data_fields[10].decode('ascii')
            # buffered data from a BSC will be designated with 0, online data with 1
            self.online_data = int(data_fields[11])
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
        'bv',
        'ais_id',
        'channel',
    )

    def __init__(self, raw: bytes, fields: typing.Optional[typing.List[bytes]] = None) -> None:
        super().__init__(raw, fields)

        try:
            # Unpack NMEA message parts
            (
                message_fragments,
                fragment_number,
                message_id,
                channel,
                payload,
            ) = self.data_fields[:5]

            # These are all short decimal numbers and single letters that repeat
            # on every line, so the cached lookups below hit almost every time.
            # Total number of fragments
            frag_cnt = _SMALL_INTS.get(message_fragments)
            self.frag_cnt: int = int(message_fragments) if frag_cnt is None else frag_cnt

            # Current fragment index
            frag_num = _SMALL_INTS.get(fragment_number)
            self.frag_num: int = int(fragment_number) if frag_num is None else frag_num

            # Optional message index for multiline messages
            if message_id:
                seq_id = _SMALL_INTS.get(message_id)
                self.seq_id: Optional[int] = int(message_id) if seq_id is None else seq_id
            else:
                self.seq_id = None

            # Channel (A or B)
            chan = _ASCII_CACHE.get(channel)
            self.channel: str = _ascii(channel) if chan is None else chan
            # Decoded message payload as byte string
            self.payload: bytes = payload

        except Exception as err:
            raise InvalidNMEAMessageException(raw) from err

        if len(payload) > MAX_PAYLOAD_LEN:
            raise InvalidNMEAMessageException("AIS payload too large")

        if self.frag_cnt > MAX_FRAG_CNT or self.frag_num > MAX_FRAG_CNT:
            raise InvalidNMEAMessageException("Too many fragments")

        # Finally decode bytes into bits
        self.bv = bit_vector(payload, self.fill_bits)
        self.ais_id = self.bv.get(0, 6)

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
        if len(messages) == 1:
            return messages[0]

        raw = b''
        payload = b''
        is_valid = True

        for i, msg in enumerate(sorted(messages, key=lambda m: m.frag_num)):
            if i > 0:
                raw += b'\n'
            raw += msg.raw
            payload += msg.payload
            is_valid &= msg.is_valid

        messages[0].raw = raw
        messages[0].payload = payload
        messages[0].bv = bit_vector(payload, messages[-1].fill_bits)
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
            return MSG_CLASS[self.ais_id].from_vector(self.bv)
        except KeyError as e:
            raise UnknownMessageException(f"The message {self} is not supported!") from e


@attr.s(slots=True)
class Payload(abc.ABC):
    """
    Payload class
    --------------
    This class serves as an abstract base class for all messages.
    Each message shall inherit from Payload and define it's set of field using the `bit_field` method.

    A pre-computed decoder plan is built once per class to remove redundant work during decoding.
    Such a decoder plan is nothing more than a simple list of decoding-instructions for each field.
    Because message classes differ structurally each class requires its individual plan - but it
    suffices to compute this plan once.
    """

    _decoder_plan: _DecoderPlan  # just a type hint

    # Fast paths are used to speed up decoding for certain fixed-width message types.
    # Assume a fast path may be available until proven otherwise.
    # Set to False if a message class raises a NotImplementedError during runtime.
    FAST_PATH_AVAILABLE: list[bool] = [True] * 64

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

    @classmethod
    @functools.lru_cache(maxsize=64)
    def field_dict(cls) -> typing.Dict[str, typing.Any]:
        """
        A dictionary of <field.name: field> key value pairs.
        LRU cached for fast repeated access.
        """
        return {field.name: field for field in cls.fields()}

    def to_bytes(self) -> tuple[bytes, int]:
        output = bytearray()
        bit_buffer = 0
        bits_in_buffer = 0
        total_bits = 0

        for field in self.fields():
            width = field.metadata['width']
            d_type = field.metadata['d_type']
            converter = field.metadata['from_converter']
            variable_length = field.metadata['variable_length']

            val = getattr(self, field.name)
            if val is None:
                continue

            val = converter(val) if converter is not None else val

            if d_type in (bool, int, float):
                # Convert number to bits
                val = int(val)
                bit_buffer = (bit_buffer << width) | (val & ((1 << width) - 1))
                bits_in_buffer += width
            elif d_type == str:
                trailing_spaces = not variable_length
                num_chars = int(width / 6)
                if trailing_spaces:
                    # Add trailing '@' if the string is shorter than `width`
                    for _ in range(num_chars - len(val)):
                        val += "@"
                for char in val[:num_chars]:
                    # Convert each char to six-bit ASCII vector
                    txt = SIX_BIT_ENCODING[char.upper()]
                    bit_buffer = (bit_buffer << 6) | (txt & ((1 << width) - 1))
                    bits_in_buffer += 6
            elif d_type == bytes:
                # Convert bytes to bits
                if not val:
                    bit_buffer = (bit_buffer << width)
                    bits_in_buffer += width
                else:
                    required_bits = min(width, len(val) * 8)
                    int_value = int.from_bytes(val, 'big') >> (len(val) * 8 - required_bits)  # undo left-alignment
                    bit_buffer = (bit_buffer << required_bits) | int_value
                    bits_in_buffer += required_bits
            else:
                raise InvalidDataTypeException(d_type)

            # Flush out bytes
            while bits_in_buffer >= 8:
                bits_in_buffer -= 8
                byte = (bit_buffer >> bits_in_buffer) & 0xFF
                output.append(byte)
                total_bits += 8

        # Handle remaining bits (if any)
        if bits_in_buffer > 0:
            byte = (bit_buffer << (8 - bits_in_buffer)) & 0xFF
            output.append(byte)
            total_bits += bits_in_buffer

        return bytes(output), total_bits

    def encode(self) -> typing.Tuple[str, int]:
        """
        Encode a payload as an ASCII encoded bit vector. The second returned value is the number of fill bits.
        """
        return SixBitNibleEncoder().encode(*self.to_bytes())

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
    def _build_plan(cls) -> _DecoderPlan:
        """Build the decoding plan for a given message class.
        This is done by iterating over each field of the message.
        Then, for each field name, offset, width, signed, data type, and conversion function are determined.
        """
        plan: _DecoderPlan = []
        offset = 0
        for field in cls.fields():
            md = field.metadata
            width = md['width']
            d_type = md['d_type']
            if d_type is int:
                kind = INT
            elif d_type is float:
                kind = FLOAT
            elif d_type is bool:
                kind = BOOL
            elif d_type is str:
                kind = STR
            elif d_type is bytes:
                kind = BYTES
            else:
                raise InvalidDataTypeException(d_type)
            signed = md['signed']
            converter = md['to_converter']
            plan.append((field.name, offset, width, signed, kind, converter))
            offset += width
        return plan

    @classmethod
    def _fast_path(cls, bv: bit_vector) -> 'ANY_MESSAGE':
        """Use a flat extraction plan instead of iterating over each message class's
        fields. Convert the whole payload into an int once and extract every field
        with (value >> shift) & mask. These shifts run in C and are faster than
        repeated bit-field extraction."""
        raise NotImplementedError

    @classmethod
    def decoder_plan(cls) -> _DecoderPlan:
        """Get the decoder plan (cached) for a given message class.
        This is stored as a class attribute for future use."""
        plan = cls.__dict__.get('_decoder_plan')
        if plan is None:
            plan = cls._build_plan()
            cls._decoder_plan = plan
        return plan

    @classmethod
    def from_vector(cls, bv: bit_vector) -> "ANY_MESSAGE":
        plan = cls.decoder_plan()
        bv_len = len(bv)
        # Is a fast path available?
        if bv_len == 168:
            mid = bv._value >> 162
            if cls.FAST_PATH_AVAILABLE[mid]:
                try:
                    return cls._fast_path(bv)
                except NotImplementedError:
                    # Fast path is not implemented for this message type.
                    # Do not try this again.
                    cls.FAST_PATH_AVAILABLE[mid] = False
        kwargs: dict[str, NMEA_VALUE | None] = {}
        val: NMEA_VALUE
        get_num = bv.get_num
        get_str = bv.get_str
        get_bytes = bv.get_bytes

        for name, offset, width, signed, kind, converter in plan:
            if offset >= bv_len:
                kwargs[name] = None
                continue
            if kind == INT:
                val = get_num(offset, width, signed)
            elif kind == FLOAT:
                val = float(get_num(offset, width, signed))
            elif kind == BOOL:
                val = bool(get_num(offset, width, signed))
            elif kind == STR:
                val = get_str(offset, width)
            else:
                val = get_bytes(offset, width)

            if converter is not None:
                val = converter(val)
            kwargs[name] = val
        return cls(**kwargs)  # type:ignore

    def asdict(self, enum_as_int: bool = False, ignore_spare: bool = True) -> typing.Dict[str, typing.Optional[NMEA_VALUE]]:
        """
        Convert the message to a dictionary.
        @param enum_as_int:     If set to True all Enum values will be returned as raw ints.
        @param ignore_spare:    Ignore spare fields (default is True)
        @return:                The message as a dictionary.
        """
        data: typing.Dict[str, typing.Optional[NMEA_VALUE]] = {}
        fields = self.field_dict()
        slt: str
        for slt in self.__slots__:
            # ignore spare fields
            if ignore_spare and slt in fields:
                field = fields[slt]
                if 'is_spare' in field.metadata and field.metadata['is_spare']:
                    continue

            val = getattr(self, slt)

            # convert enums to int
            if enum_as_int:
                if val is not None and slt in ENUM_FIELDS:
                    val = int(getattr(self, slt))

            data[slt] = val
        return data

    def to_json(self, ignore_spare: bool = True) -> str:
        return AISJSONEncoder(indent=4).encode(self.asdict(ignore_spare=ignore_spare))


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


def from_lat_lon_60000(v: typing.Union[int, float]) -> float:
    # coordinates expressed in 1/1000 minutes (scale 1/60000 of a degree)
    return round(float(v) * 60000.0)


def to_lat_lon_60000(v: typing.Union[int, float]) -> float:
    return round(float(v) / 60000.0, 6)


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


def from_airtemp_leg(v: typing.Union[int, float]) -> float:
    # legacy FID=11 air temperature: value = raw * 0.1 - 60
    return round((float(v) + 60.0) / 0.1)


def to_airtemp_leg(v: typing.Union[int, float]) -> float:
    return round(float(v) * 0.1 - 60.0, 1)


def from_dewpt_leg(v: typing.Union[int, float]) -> float:
    return round((float(v) + 20.0) / 0.1)


def to_dewpt_leg(v: typing.Union[int, float]) -> float:
    return round(float(v) * 0.1 - 20.0, 1)


def from_press800(v: typing.Union[int, float]) -> int:
    return int(round(v)) - 800


def to_press800(v: typing.Union[int, float]) -> int:
    return int(v) + 800


def from_wl_leg(v: typing.Union[int, float]) -> float:
    return round((float(v) + 10.0) / 0.1)


def to_wl_leg(v: typing.Union[int, float]) -> float:
    return round(float(v) * 0.1 - 10.0, 1)


def from_press799(v: typing.Union[int, float]) -> int:
    # pressure in hPa, transmitted as (value - 799)
    return int(round(v)) - 799


def to_press799(v: typing.Union[int, float]) -> int:
    return int(v) + 799


def from_wl31(v: typing.Union[int, float]) -> float:
    # FID=31 water level: value = raw * 0.01 - 10
    return round((float(v) + 10.0) / 0.01)


def to_wl31(v: typing.Union[int, float]) -> float:
    return round(float(v) * 0.01 - 10.0, 2)


def _asm_bits(data: bytes, offset: int, length: int, signed: bool = False) -> int:
    """Read `length` bits at bit `offset` (MSB-first) from an ASM data region."""
    if not data:
        return 0
    total = len(data) * 8
    if offset + length > total:
        return 0
    acc = int.from_bytes(data, 'big')
    val = (acc >> (total - offset - length)) & ((1 << length) - 1)
    if signed and (val & (1 << (length - 1))):
        val -= (1 << length)
    return val


# Bit offsets inside a single 120-bit VTS target record.
# IALA IFM 16, Table 44 (identical to the IFM 17 target record).
_VTS_TARGET_BITS = 120
_VTS_MAX_TARGETS = 7


def _decode_vts_targets(data: bytes,
                        max_targets: int = _VTS_MAX_TARGETS) -> typing.List[typing.Dict[str, typing.Any]]:
    """Decode up to `max_targets` VTS target records from a data region.

    Each record is 120 bits (IALA IFM 16, Table 44):
    id_type(2), target_id(42), spare(4), lat(24), lon(25), course(9), second(6), speed(8)

    `target_id` is decoded as six-bit ASCII when `id_type` is 2 (call sign),
    otherwise it is returned as an unsigned integer (MMSI or IMO number).
    """
    out: typing.List[typing.Dict[str, typing.Any]] = []
    if not data:
        return out
    n = min((len(data) * 8) // _VTS_TARGET_BITS, max_targets)
    for i in range(n):
        base = i * _VTS_TARGET_BITS
        id_type = _asm_bits(data, base, 2)
        target_id: typing.Union[int, str]
        if id_type == 2:
            target_id = decode_bytes_as_ascii6(data, base + 2, 42)
        else:
            target_id = _asm_bits(data, base + 2, 42)
        out.append({
            'id_type': id_type,
            'target_id': target_id,
            'lat': round(_asm_bits(data, base + 48, 24, signed=True) / 60000.0, 6),
            'lon': round(_asm_bits(data, base + 72, 25, signed=True) / 60000.0, 6),
            'course': _asm_bits(data, base + 97, 9),
            'second': _asm_bits(data, base + 106, 6),
            'speed': _asm_bits(data, base + 112, 8),
        })
    return out


def _decode_synthetic_targets(data: bytes) -> typing.List[typing.Dict[str, typing.Any]]:
    """Decode 1-4 synthetic targets (120 bits each) from a FID=17 region."""
    out: typing.List[typing.Dict[str, typing.Any]] = []
    if not data:
        return out
    n = min((len(data) * 8) // 120, 4)
    for i in range(n):
        base = i * 120
        chars = []
        for k in range(7):
            c = _asm_bits(data, base + 2 + k * 6, 6)
            chars.append(chr(c + 64) if c < 32 else chr(c))
        ident = ''.join(chars).rstrip('@ ')
        out.append({
            'id': ident,
            'lat': round(_asm_bits(data, base + 48, 24, signed=True) / 60000.0, 5),
            'lon': round(_asm_bits(data, base + 72, 25, signed=True) / 60000.0, 5),
            'course': _asm_bits(data, base + 97, 9),
            'speed': _asm_bits(data, base + 112, 8),
        })
    return out


# A single Area Notice sub-area indication: a 3-bit shape selector followed by
# an 84-bit shape-specific payload (IMO289, DAC=1/FID=22 and DAC=1/FID=23).
_AREA_NOTICE_SUBAREA_BITS = 87
_AREA_NOTICE_MAX_SUBAREAS = 10

# Sub-area shape selectors.
AREA_NOTICE_SHAPE_CIRCLE = 0
AREA_NOTICE_SHAPE_RECTANGLE = 1
AREA_NOTICE_SHAPE_SECTOR = 2
AREA_NOTICE_SHAPE_POLYLINE = 3
AREA_NOTICE_SHAPE_POLYGON = 4
AREA_NOTICE_SHAPE_TEXT = 5

# Sub Area Types
_AREA_TYPE_STR = {0: 'circle', 1: 'rectangle', 2: 'sector', 3: 'polyline', 4: 'polygon', 5: 'text'}


def _decode_area_notice_subareas(data: bytes) -> typing.List[typing.Dict[str, typing.Any]]:
    """Decode 1-10 Area Notice sub-area indications (87 bits each).

    Each record starts with a 3-bit shape selector that determines how the
    remaining 84 bits are laid out. Shapes 0-2 carry an absolute position,
    shapes 3-4 carry offsets from the preceding shape, and shape 5 carries
    free text.

    `scale` is a power-of-ten multiplier for the linear dimensions of the
    record. It is reported as-is, and the dimensions it applies to (radius,
    east, north, distance) are returned already multiplied out, in metres.
    """
    out: typing.List[typing.Dict[str, typing.Any]] = []
    if not data:
        return out

    n = min((len(data) * 8) // _AREA_NOTICE_SUBAREA_BITS, _AREA_NOTICE_MAX_SUBAREAS)
    for i in range(n):

        # 3-bit shape selector. Same for every shape.
        base = i * _AREA_NOTICE_SUBAREA_BITS
        shape = _asm_bits(data, base, 3)
        area: typing.Dict[str, typing.Any] = {
            'shape': shape,
            'shape_str': _AREA_TYPE_STR.get(shape, 'reserved')
        }

        if shape == AREA_NOTICE_SHAPE_TEXT:
            # 14 six-bit characters filling the whole 84-bit payload.
            area['text'] = decode_bytes_as_ascii6(data, base + 3, 84).rstrip('@ ')
            out.append(area)
            continue

        if shape > AREA_NOTICE_SHAPE_TEXT:
            # 6-7 are reserved: keep the raw payload rather than guess a layout.
            area['data'] = _asm_bits(data, base + 3, 84)
            out.append(area)
            continue

        scale = _asm_bits(data, base + 3, 2)
        factor = 10 ** scale
        area['scale'] = scale

        if shape in (AREA_NOTICE_SHAPE_POLYLINE, AREA_NOTICE_SHAPE_POLYGON):
            # Four (bearing, distance) pairs of 20 bits; the last 2 bits spare.
            points = []
            for k in range(4):
                off = base + 5 + k * 20
                points.append({
                    # True bearing in half-degree steps; 720 (= 360.0) is N/A.
                    'bearing': _asm_bits(data, off, 10) * 0.5,
                    # 0 = no point / no vertex.
                    'distance': _asm_bits(data, off + 10, 10) * factor,
                })
            area['points'] = points
            out.append(area)
            continue

        # Shapes 0-2 share a common position block.
        area['lon'] = round(_asm_bits(data, base + 5, 25, signed=True) / 60000.0, 5)
        area['lat'] = round(_asm_bits(data, base + 30, 24, signed=True) / 60000.0, 5)
        area['precision'] = _asm_bits(data, base + 54, 3)

        if shape == AREA_NOTICE_SHAPE_CIRCLE:
            # 0 = the shape is a point rather than a circle.
            area['radius'] = _asm_bits(data, base + 57, 12) * factor
        elif shape == AREA_NOTICE_SHAPE_RECTANGLE:
            # 0 = degenerate box, i.e. a N/S line (east) or an E/W line (north).
            area['east'] = _asm_bits(data, base + 57, 8) * factor
            area['north'] = _asm_bits(data, base + 65, 8) * factor
            # Degrees clockwise from true north; 0 = no rotation.
            area['orientation'] = _asm_bits(data, base + 73, 9)
        else:  # AREA_NOTICE_SHAPE_SECTOR
            area['radius'] = _asm_bits(data, base + 57, 12) * factor
            # Sector boundaries, degrees clockwise from true north.
            area['left'] = _asm_bits(data, base + 69, 9)
            area['right'] = _asm_bits(data, base + 78, 9)

        out.append(area)

    return out


# A single Environmental sensor record: a 4-bit report type, a 20-bit
# timestamp+site header, and an 85-bit type-specific payload (IMO289,
# DAC=1/FID=26). 27 + 85 = 112 bits per record.
_ENV_REPORT_BITS = 112
_ENV_MAX_REPORTS = 5

# Sensor Report Type selectors (Table 38).
ENV_REPORT_SITE_LOCATION = 0
ENV_REPORT_STATION_ID = 1
ENV_REPORT_WIND = 2
ENV_REPORT_WATER_LEVEL = 3
ENV_REPORT_CURRENT_2D = 4
ENV_REPORT_CURRENT_3D = 5
ENV_REPORT_CURRENT_HORIZONTAL = 6
ENV_REPORT_SEA_STATE = 7
ENV_REPORT_SALINITY = 8
ENV_REPORT_WEATHER = 9
ENV_REPORT_AIRGAP = 10

_ENV_REPORT_TYPE_STR = {
    0: 'site_location', 1: 'station_id', 2: 'wind', 3: 'water_level',
    4: 'current_2d', 5: 'current_3d', 6: 'current_horizontal',
    7: 'sea_state', 8: 'salinity', 9: 'weather', 10: 'airgap',
}


def _decode_environmental_reports(data: bytes) -> typing.List[typing.Dict[str, typing.Any]]:
    """Decode 1-5 Environmental sensor records (112 bits each).

    Every record starts with a common 27-bit header (report type, UTC
    day/hour/minute, and a site ID), followed by an 85-bit payload whose
    layout depends on the report type. Report type 11 and any other
    unrecognized value are kept as a raw 85-bit integer rather than guessed
    at.

    Fields are returned already scaled to their documented units (knots,
    metres, degrees C, percent, etc.); sentinel/N/A/reserved codes are
    passed through as-is rather than converted to None, matching how
    `_decode_area_notice_subareas` handles its own sentinels.
    """
    out: typing.List[typing.Dict[str, typing.Any]] = []
    if not data:
        return out

    n = min((len(data) * 8) // _ENV_REPORT_BITS, _ENV_MAX_REPORTS)
    for i in range(n):
        base = i * _ENV_REPORT_BITS
        sensor = _asm_bits(data, base, 4)
        report: typing.Dict[str, typing.Any] = {
            'sensor': sensor,
            'sensor_str': _ENV_REPORT_TYPE_STR.get(sensor, 'reserved'),
            'day': _asm_bits(data, base + 4, 5),
            'hour': _asm_bits(data, base + 9, 5),
            'minute': _asm_bits(data, base + 14, 6),
            'site': _asm_bits(data, base + 20, 7),
        }
        p = base + 27  # start of the 85-bit payload

        if sensor == ENV_REPORT_SITE_LOCATION:
            report['lon'] = round(_asm_bits(data, p, 28, signed=True) / 600000.0, 5)
            report['lat'] = round(_asm_bits(data, p + 28, 27, signed=True) / 600000.0, 5)
            report['alt'] = round(_asm_bits(data, p + 55, 11) * 0.1, 1)
            report['owner'] = _asm_bits(data, p + 66, 4)
            report['timeout'] = _asm_bits(data, p + 70, 3)

        elif sensor == ENV_REPORT_STATION_ID:
            report['name'] = decode_bytes_as_ascii6(data, p, 84).rstrip('@ ')

        elif sensor == ENV_REPORT_WIND:
            report['wspeed'] = _asm_bits(data, p, 7)
            report['wgust'] = _asm_bits(data, p + 7, 7)
            report['wdir'] = _asm_bits(data, p + 14, 9)
            report['wgustdir'] = _asm_bits(data, p + 23, 9)
            report['sensortype'] = _asm_bits(data, p + 32, 3)
            report['fwspeed'] = _asm_bits(data, p + 35, 7)
            report['fwgust'] = _asm_bits(data, p + 42, 7)
            report['fwdir'] = _asm_bits(data, p + 49, 9)
            report['fday'] = _asm_bits(data, p + 58, 5)
            report['fhour'] = _asm_bits(data, p + 63, 5)
            report['fminute'] = _asm_bits(data, p + 68, 6)
            report['duration'] = _asm_bits(data, p + 74, 8)

        elif sensor == ENV_REPORT_WATER_LEVEL:
            report['absolute'] = bool(_asm_bits(data, p, 1))
            report['level'] = round(_asm_bits(data, p + 1, 16, signed=True) * 0.01, 2)
            report['leveltrend'] = _asm_bits(data, p + 17, 2)
            report['datum'] = _asm_bits(data, p + 19, 5)
            report['sensortype'] = _asm_bits(data, p + 24, 3)
            report['fabsolute'] = bool(_asm_bits(data, p + 27, 1))
            # IMO289 documents 16 bits of 2 decimal-place precision for the
            # forecast level too; the "0.001m" in its prose is inconsistent
            # with that range, so the 0.01m step from the current-level
            # field is used here as well.
            report['flevel'] = round(_asm_bits(data, p + 28, 16, signed=True) * 0.01, 2)
            report['fday'] = _asm_bits(data, p + 44, 5)
            report['fhour'] = _asm_bits(data, p + 49, 5)
            report['fminute'] = _asm_bits(data, p + 54, 6)
            report['duration'] = _asm_bits(data, p + 60, 8)

        elif sensor == ENV_REPORT_CURRENT_2D:
            for idx, off in enumerate((0, 26, 52), start=1):
                report[f'cspeed{idx}'] = round(_asm_bits(data, p + off, 8) * 0.1, 1)
                report[f'cdir{idx}'] = _asm_bits(data, p + off + 8, 9)
                report[f'cdepth{idx}'] = _asm_bits(data, p + off + 17, 9)
            report['sensortype'] = _asm_bits(data, p + 78, 3)

        elif sensor == ENV_REPORT_CURRENT_3D:
            report['cnorth1'] = round(_asm_bits(data, p, 8) * 0.1, 1)
            report['ceast1'] = round(_asm_bits(data, p + 8, 8) * 0.1, 1)
            report['cup1'] = round(_asm_bits(data, p + 16, 8) * 0.1, 1)
            report['cdepth1'] = _asm_bits(data, p + 24, 9)
            report['cnorth2'] = round(_asm_bits(data, p + 33, 8) * 0.1, 1)
            report['ceast2'] = round(_asm_bits(data, p + 41, 8) * 0.1, 1)
            report['cup2'] = round(_asm_bits(data, p + 49, 8) * 0.1, 1)
            report['cdepth2'] = _asm_bits(data, p + 57, 9)
            report['sensortype'] = _asm_bits(data, p + 66, 3)

        elif sensor == ENV_REPORT_CURRENT_HORIZONTAL:
            report['bearing1'] = _asm_bits(data, p, 9)
            report['distance1'] = _asm_bits(data, p + 9, 7)
            report['speed1'] = round(_asm_bits(data, p + 16, 8) * 0.1, 1)
            report['direction1'] = _asm_bits(data, p + 24, 9)
            report['depth1'] = _asm_bits(data, p + 33, 9)
            report['bearing2'] = _asm_bits(data, p + 42, 9)
            report['distance2'] = _asm_bits(data, p + 51, 7)
            report['speed2'] = round(_asm_bits(data, p + 58, 8) * 0.1, 1)
            report['direction2'] = _asm_bits(data, p + 66, 9)
            report['depth2'] = _asm_bits(data, p + 75, 9)

        elif sensor == ENV_REPORT_SEA_STATE:
            report['swheight'] = round(_asm_bits(data, p, 8) * 0.1, 1)
            report['swperiod'] = _asm_bits(data, p + 8, 6)
            report['swelldir'] = _asm_bits(data, p + 14, 9)
            report['seastate'] = _asm_bits(data, p + 23, 4)
            report['swelltype'] = _asm_bits(data, p + 27, 3)
            report['watertemp'] = round(_asm_bits(data, p + 30, 10, signed=True) * 0.1, 1)
            report['watertempdepth'] = round(_asm_bits(data, p + 40, 7) * 0.1, 1)
            report['depthtype'] = _asm_bits(data, p + 47, 3)
            report['waveheight'] = round(_asm_bits(data, p + 50, 8) * 0.1, 1)
            report['waveperiod'] = _asm_bits(data, p + 58, 6)
            report['wavedir'] = _asm_bits(data, p + 64, 9)
            report['wavetype'] = _asm_bits(data, p + 73, 3)
            report['salinity'] = round(_asm_bits(data, p + 76, 9) * 0.1, 1)

        elif sensor == ENV_REPORT_SALINITY:
            report['watertemp'] = round(_asm_bits(data, p, 10, signed=True) * 0.1, 1)
            report['conductivity'] = round(_asm_bits(data, p + 10, 10) * 0.1, 1)
            report['pressure'] = round(_asm_bits(data, p + 20, 16) * 0.1, 1)
            report['salinity'] = round(_asm_bits(data, p + 36, 9) * 0.1, 1)
            report['salinitytype'] = _asm_bits(data, p + 45, 2)
            report['sensortype'] = _asm_bits(data, p + 47, 3)

        elif sensor == ENV_REPORT_WEATHER:
            report['temperature'] = round(_asm_bits(data, p, 11, signed=True) * 0.1, 1)
            report['sensortype'] = _asm_bits(data, p + 11, 3)
            report['preciptype'] = _asm_bits(data, p + 14, 2)
            report['visibility'] = round(_asm_bits(data, p + 16, 8) * 0.1, 1)
            report['dewpoint'] = round(_asm_bits(data, p + 24, 10, signed=True) * 0.1, 1)
            report['dewtype'] = _asm_bits(data, p + 34, 3)
            # Raw code per spec: 0 = <=800hPa, 1-401 = 800-1200hPa (i.e. raw
            # + 799), 402 = >=1201hPa, 403 = N/A. Kept raw rather than
            # offset, since a sentinel-safe conversion would need the same
            # per-field care as the attrs-based pressure fields elsewhere.
            report['pressure'] = _asm_bits(data, p + 37, 9)
            report['pressuretend'] = _asm_bits(data, p + 46, 2)
            report['pressuretype'] = _asm_bits(data, p + 48, 3)
            report['salinity'] = round(_asm_bits(data, p + 51, 9) * 0.1, 1)

        elif sensor == ENV_REPORT_AIRGAP:
            report['airdraught'] = round(_asm_bits(data, p, 13) * 0.01, 2)
            report['airgap'] = round(_asm_bits(data, p + 13, 13) * 0.01, 2)
            report['gaptrend'] = _asm_bits(data, p + 26, 2)
            report['fairgap'] = round(_asm_bits(data, p + 28, 13) * 0.01, 2)
            report['fday'] = _asm_bits(data, p + 41, 5)
            report['fhour'] = _asm_bits(data, p + 46, 5)
            report['fminute'] = _asm_bits(data, p + 51, 6)

        else:
            # Report type 11 is reserved for future use; anything else is
            # unrecognized. Keep the raw payload rather than guess a layout.
            report['data'] = _asm_bits(data, p, 85)

        out.append(report)

    return out


# A single Route Information waypoint: signed longitude/latitude at the same
# 1/10000-minute resolution as the Common Navigation Block (IMO289,
# DAC=1/FID=27, and its addressed equivalent DAC=1/FID=28).
_ROUTE_WAYPOINT_BITS = 55
_ROUTE_MAX_WAYPOINTS = 16


def _decode_route_waypoints(data: bytes, waycount: int) -> typing.List[typing.Dict[str, float]]:
    """Decode up to 16 (lon, lat) waypoints, 55 bits each."""
    out: typing.List[typing.Dict[str, float]] = []
    if not data:
        return out

    available = (len(data) * 8) // _ROUTE_WAYPOINT_BITS
    n = max(0, min(waycount, _ROUTE_MAX_WAYPOINTS, available))
    for i in range(n):
        base = i * _ROUTE_WAYPOINT_BITS
        out.append({
            'lon': round(_asm_bits(data, base, 28, signed=True) / 600000.0, 5),
            'lat': round(_asm_bits(data, base + 28, 27, signed=True) / 600000.0, 5),
        })
    return out


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
    spare_1 = bit_field(3, bytes, default=b'', is_spare=True)
    raim = bit_field(1, bool, default=0)
    radio = bit_field(19, int, default=0, signed=False)

    @classmethod
    def _fast_path(cls, bv: bit_vector) -> 'MessageType1':
        v = bv._value
        # Rot
        r = (v >> 118) & 255
        if r > 127:
            r -= 256
        # Lon
        lx = (v >> 79) & 0xFFFFFFF
        if lx & 0x8000000:
            lx -= 0x10000000
        # Lat
        ly = (v >> 52) & 0x7FFFFFF
        if ly & 0x4000000:
            ly -= 0x8000000

        return cls(
            v >> 162,
            (v >> 160) & 3,
            (v >> 130) & 0x3FFFFFFF,  # type: ignore
            (v >> 126) & 15,
            to_turn(r),
            to_speed((v >> 108) & 1023),
            bool((v >> 107) & 1),
            to_lat_lon(lx),
            to_lat_lon(ly),
            to_10th((v >> 40) & 4095),
            (v >> 31) & 511,
            (v >> 25) & 63,
            ManeuverIndicator.from_value((v >> 23) & 3),
            (((v >> 20) & 7) << 5).to_bytes(1, "big"),
            bool((v >> 19) & 1),
            v & 0x7ffff,
        )


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
    spare_1 = bit_field(10, bytes, default=b'', is_spare=True)
    raim = bit_field(1, bool, default=0)
    radio = bit_field(19, int, default=0, signed=False)

    @classmethod
    def _fast_path(cls, bv: bit_vector) -> 'MessageType4':
        v = bv._value
        # Lon
        lx = (v >> 61) & 0xFFFFFFF
        if lx & 0x8000000:
            lx -= 0x10000000
        # Lat
        ly = (v >> 34) & 0x7FFFFFF
        if ly & 0x4000000:
            ly -= 0x8000000

        return cls(
            v >> 162,
            (v >> 160) & 0x3,
            (v >> 130) & 0x3fffffff,  # type: ignore
            (v >> 116) & 0x3fff,
            (v >> 112) & 0xf,
            (v >> 107) & 0x1f,
            (v >> 102) & 0x1f,
            (v >> 96) & 0x3f,
            (v >> 90) & 0x3f,
            bool((v >> 89) & 0x1),
            to_lat_lon(lx),
            to_lat_lon(ly),
            EpfdType.from_value((v >> 30) & 0xf),
            (((v >> 20) & 0x3ff) << 6).to_bytes(2, "big"),
            bool((v >> 19) & 0x1),
            v & 0x7ffff,
        )


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
    spare_1 = bit_field(1, bytes, default=b'', is_spare=True)


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
    spare_1 = bit_field(1, bytes, default=b'', is_spare=True)
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
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
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
        variant = _msg8_variant(dac, fid)
        if variant is not None:
            return variant.create(**kwargs)
        return MessageType8Default.create(**kwargs)

    @classmethod
    def from_vector(cls, bv: bit_vector) -> "ANY_MESSAGE":
        dac: int = bv.get(40, 10)
        fid: int = bv.get(50, 6)
        variant = _msg8_variant(dac, fid)
        if variant is not None:
            return variant.from_vector(bv)
        return MessageType8Default.from_vector(bv)


@attr.s(slots=True)
class MessageType8Default(Payload):
    """
    Binary Acknowledge
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_8_binary_broadcast_message
    """

    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b"", is_spare=True)
    dac = bit_field(10, int, default=0, signed=False)
    fid = bit_field(6, int, default=0, signed=False)
    data = bit_field(952, bytes, default=b"", variable_length=True)


@attr.s(slots=True)
class MessageType8Dac1Fid0(Payload):
    """ITU-R M.1371 broadcast text using 6-bit ASCII (DAC=1, FID=0)."""
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=0, signed=False)
    ack_required = bit_field(1, bool, default=False, signed=False)
    text_sequence = bit_field(11, int, default=0, signed=False)
    text = bit_field(906, str, default='', variable_length=True)


@attr.s(slots=True)
class MessageType8Dac1Fid11(Payload):
    """Meteorological and Hydrological Data (IMO236). Superseded by FID=31."""
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=11, signed=False)
    lat = bit_field(24, float, from_converter=from_lat_lon_60000, to_converter=to_lat_lon_60000, signed=True, default=0)
    lon = bit_field(25, float, from_converter=from_lat_lon_60000, to_converter=to_lat_lon_60000, signed=True, default=0)
    day = bit_field(5, int, default=0, signed=False)
    hour = bit_field(5, int, default=24, signed=False)
    minute = bit_field(6, int, default=60, signed=False)
    wspeed = bit_field(7, int, default=127, signed=False)
    wgust = bit_field(7, int, default=127, signed=False)
    wdir = bit_field(9, int, default=511, signed=False)
    wgustdir = bit_field(9, int, default=511, signed=False)
    airtemp = bit_field(11, float, from_converter=from_airtemp_leg, to_converter=to_airtemp_leg, default=0, signed=False)
    humidity = bit_field(7, int, default=127, signed=False)
    dewpoint = bit_field(10, float, from_converter=from_dewpt_leg, to_converter=to_dewpt_leg, default=0, signed=False)
    pressure = bit_field(9, int, from_converter=from_press800, to_converter=to_press800, default=0, signed=False)
    pressuretend = bit_field(2, int, default=3, signed=False)
    visibility = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    waterlevel = bit_field(9, float, from_converter=from_wl_leg, to_converter=to_wl_leg, default=0, signed=False)
    leveltrend = bit_field(2, int, default=3, signed=False)
    cspeed = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    cdir = bit_field(9, int, default=511, signed=False)
    cspeed2 = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    cdir2 = bit_field(9, int, default=511, signed=False)
    cdepth2 = bit_field(5, int, default=31, signed=False)
    cspeed3 = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    cdir3 = bit_field(9, int, default=511, signed=False)
    cdepth3 = bit_field(5, int, default=31, signed=False)
    waveheight = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    waveperiod = bit_field(6, int, default=63, signed=False)
    wavedir = bit_field(9, int, default=511, signed=False)
    swellheight = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    swellperiod = bit_field(6, int, default=63, signed=False)
    swelldir = bit_field(9, int, default=511, signed=False)
    seastate = bit_field(4, int, default=13, signed=False)
    watertemp = bit_field(10, float, from_converter=from_wl_leg, to_converter=to_wl_leg, default=0, signed=False)
    preciptype = bit_field(3, int, default=7, signed=False)
    salinity = bit_field(9, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    ice = bit_field(2, int, default=3, signed=False)


@attr.s(slots=True)
class MessageType8Dac1Fid16(Payload):
    """IALA VTS targets (targets derived by means other than AIS). DAC=1, FID=16.

    Variable length: 1 to 7 target records of 120 bits each, so 176 to 896 bits
    in total. The records live in a raw region; use .targets to decode them.

    Src: https://www.iala.int/asm/vts-targets-targets-derived-means-ais/
    """
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=16, signed=False)
    target_data = bit_field(840, bytes, default=b'', variable_length=True)

    @property
    def targets(self) -> typing.List[typing.Dict[str, typing.Any]]:
        """Decode the 1-7 VTS targets (id_type, target_id, lat, lon, course, second, speed)."""
        return _decode_vts_targets(self.target_data)


@attr.s(slots=True)
class MessageType8Dac1Fid17(Payload):
    """VTS-Generated/Synthetic targets (IMO236).
    1-4 targets of 120 bits each in a raw region (see .targets)."""
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=17, signed=False)
    target_data = bit_field(480, bytes, default=b'', variable_length=True)

    @property
    def targets(self) -> typing.List[typing.Dict[str, typing.Any]]:
        """Decode the 1-4 synthetic targets (id, lat, lon, course, speed)."""
        return _decode_synthetic_targets(self.target_data)


@attr.s(slots=True)
class MessageType8Dac1Fid19(Payload):
    """Marine Traffic Signal (IMO289). DAC=1, FID=19.

    Fixed length: 360 bits (occupies 2 slots).

    status (Status of Signal): 0 = not available (default), 1 = in regular
    service, 2 = irregular service, 3 = reserved.

    signal / nextsignal (Signal in Service, Table 8.2): 0 = not available
    (default), 1-7 = IALA port traffic signals 1, 2, 3, 4, 5, 2a, 5a,
    8-13 = Japan traffic signals I, O, F, XI, XO, X, 14-31 = reserved.

    Src: https://www.iala.int/asm/marine-traffic-signal/
    """
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=19, signed=False)
    linkage = bit_field(10, int, default=0, signed=False)
    station = bit_field(120, str, default='')
    lon = bit_field(25, float, from_converter=from_lat_lon_60000, to_converter=to_lat_lon_60000, signed=True, default=0)
    lat = bit_field(24, float, from_converter=from_lat_lon_60000, to_converter=to_lat_lon_60000, signed=True, default=0)
    status = bit_field(2, int, default=0, signed=False)
    signal = bit_field(5, int, default=0, signed=False)
    hour = bit_field(5, int, default=24, signed=False)
    minute = bit_field(6, int, default=60, signed=False)
    nextsignal = bit_field(5, int, default=0, signed=False)
    spare_2 = bit_field(102, bytes, default=b'', is_spare=True)


@attr.s(slots=True)
class MessageType8Dac1Fid20(Payload):
    """Berthing data (IMO289). DAC=1, FID=20.

    Broadcast counterpart of the addressed Message 6 berthing data: the same
    272-bit application block, carried behind the 56-bit Message 8 header,
    for a fixed total of 328 bits.

    Provides information on a ship's berth. Sent by a ship it is a berthing
    request; sent by a competent authority it is a berthing assignment. The
    UTC timestamp is the time requested or granted for berthing, and
    berth_lon/berth_lat refer to the centre of the berth.

    berth_length: 1-510 m in 1 m steps, 511 = >= 511 m, 0 = N/A (default).
    berth_depth: 0.1-25.4 m in 0.1 m steps, 25.5 = >= 25.5 m, 0 = N/A (default).

    position (Mooring Position): 0 = not available (default), 1 = port-side to,
    2 = starboard-side to, 3 = Mediterranean (end-on) mooring, 4 = mooring
    buoy, 5 = anchorage, 6-7 = reserved.

    availability is the master flag for the service fields that follow it: the
    2-bit service values are only meaningful when it is set. Each service uses
    0 = not available or requested (default), 1 = service available,
    2 = no data or unknown, 3 = not to be used.

    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_imo289_berthing_data_addressed
    """
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=20, signed=False)
    linkage = bit_field(10, int, default=0, signed=False)
    berth_length = bit_field(9, int, default=0, signed=False)
    berth_depth = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    position = bit_field(3, int, default=0, signed=False)
    month = bit_field(4, int, default=0, signed=False)
    day = bit_field(5, int, default=0, signed=False)
    hour = bit_field(5, int, default=24, signed=False)
    minute = bit_field(6, int, default=60, signed=False)
    availability = bit_field(1, bool, default=False, signed=False)
    agent = bit_field(2, int, default=0, signed=False)
    fuel = bit_field(2, int, default=0, signed=False)
    chandler = bit_field(2, int, default=0, signed=False)
    stevedore = bit_field(2, int, default=0, signed=False)
    electrical = bit_field(2, int, default=0, signed=False)
    water = bit_field(2, int, default=0, signed=False)
    customs = bit_field(2, int, default=0, signed=False)
    cartage = bit_field(2, int, default=0, signed=False)
    crane = bit_field(2, int, default=0, signed=False)
    lift = bit_field(2, int, default=0, signed=False)
    medical = bit_field(2, int, default=0, signed=False)
    navrepair = bit_field(2, int, default=0, signed=False)
    provisions = bit_field(2, int, default=0, signed=False)
    shiprepair = bit_field(2, int, default=0, signed=False)
    surveyor = bit_field(2, int, default=0, signed=False)
    steam = bit_field(2, int, default=0, signed=False)
    tugs = bit_field(2, int, default=0, signed=False)
    solidwaste = bit_field(2, int, default=0, signed=False)
    liquidwaste = bit_field(2, int, default=0, signed=False)
    hazardouswaste = bit_field(2, int, default=0, signed=False)
    ballast = bit_field(2, int, default=0, signed=False)
    additional = bit_field(2, int, default=0, signed=False)
    regional1 = bit_field(2, int, default=0, signed=False)
    regional2 = bit_field(2, int, default=0, signed=False)
    future1 = bit_field(2, int, default=0, signed=False)
    future2 = bit_field(2, int, default=0, signed=False)
    berth_name = bit_field(120, str, default='')
    berth_lon = bit_field(25, float, from_converter=from_lat_lon_60000, to_converter=to_lat_lon_60000, signed=True, default=0)
    berth_lat = bit_field(24, float, from_converter=from_lat_lon_60000, to_converter=to_lat_lon_60000, signed=True, default=0)


@attr.s(slots=True)
class MessageType8Dac1Fid21(Payload):
    """Weather observation report from ship (IMO289). DAC=1, FID=21.

    Two variants share this (DAC, FID) pair and are distinguished by bit 56,
    the WMO bit; the field layouts diverge completely after it. Like
    MessageType16, this class only dispatches and is never instantiated
    itself.

    Only the non-WMO variant (bit 56 = 0) is decoded, as
    MessageType8Dac1Fid21NonWmo. The WMO BUFR variant (bit 56 = 1) falls back
    to MessageType8Default, so its payload stays available as raw bytes in
    `data` rather than being mis-read against the wrong layout.

    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_imo289_weather_observation_report_from_ship
    """

    @classmethod
    def create(cls, **kwargs: typing.Union[str, float, int, bool, bytes]) -> "ANY_MESSAGE":
        if int(kwargs.get('wmo', 0)):
            return MessageType8Default.create(**kwargs)
        return MessageType8Dac1Fid21NonWmo.create(**kwargs)

    @classmethod
    def from_vector(cls, bv: bit_vector) -> "ANY_MESSAGE":
        if bv.get(56, 1):
            return MessageType8Default.from_vector(bv)
        return MessageType8Dac1Fid21NonWmo.from_vector(bv)


@attr.s(slots=True)
class MessageType8Dac1Fid21NonWmo(Payload):
    """Weather observation report from ship, non-WMO variant (IMO289).

    DAC=1, FID=21, WMO bit clear. Fixed length: 360 bits.

    weather (Present Weather, WMO code 45501): 0 = clear (no clouds at any
    level), 1 = cloudy, 2 = rain, 3 = fog, 4 = snow, 5 = typhoon/hurricane,
    6 = monsoon, 7 = thunderstorm, 8 = not available (default),
    9-15 = reserved.

    vislimit, when set, means the maximum range of the visibility equipment
    was reached, so `visibility` should be read as "greater than" its value.

    pressuretend carries a WMO FM13 code; IMO289 does not enumerate it.
    """
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=21, signed=False)
    wmo = bit_field(1, bool, default=False, signed=False)
    location = bit_field(120, str, default='')
    lon = bit_field(25, float, from_converter=from_lat_lon_60000, to_converter=to_lat_lon_60000, signed=True, default=0)
    lat = bit_field(24, float, from_converter=from_lat_lon_60000, to_converter=to_lat_lon_60000, signed=True, default=0)
    day = bit_field(5, int, default=0, signed=False)
    hour = bit_field(5, int, default=24, signed=False)
    minute = bit_field(6, int, default=60, signed=False)
    weather = bit_field(4, int, default=8, signed=False)
    vislimit = bit_field(1, bool, default=False, signed=False)
    visibility = bit_field(7, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    humidity = bit_field(7, int, default=127, signed=False)
    wspeed = bit_field(7, int, default=127, signed=False)
    wdir = bit_field(9, int, default=360, signed=False)
    pressure = bit_field(9, int, from_converter=from_press799, to_converter=to_press799, default=0, signed=False)
    pressuretend = bit_field(4, int, default=15, signed=False)
    airtemp = bit_field(11, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    watertemp = bit_field(10, float, from_converter=from_10th, to_converter=to_10th, default=50.1, signed=True)
    waveperiod = bit_field(6, int, default=63, signed=False)
    waveheight = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    wavedir = bit_field(9, int, default=360, signed=False)
    swellheight = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    swelldir = bit_field(9, int, default=360, signed=False)
    swellperiod = bit_field(6, int, default=63, signed=False)
    spare_2 = bit_field(3, bytes, default=b'', is_spare=True)


@attr.s(slots=True)
class MessageType8Dac1Fid22(Payload):
    """Area Notice (broadcast) (IMO289). DAC=1, FID=22.

    Broadcasts time- and location-dependent information about hazards to
    navigation. There is a related addressed form as Message 6, DAC=1/FID=23,
    which uses the same sub-area records behind a different header.

    Variable length: a fixed 111-bit header followed by 1 to 10 sub-area
    indications of 87 bits each, so 198 to 981 bits in total. The sub-areas
    live in a raw region; use .sub_areas to decode them.

    notice (Notice Description) is a 7-bit code from the IMO289 table, grouped
    in blocks of 8: 0-21 caution areas, 23-30 environmental caution areas,
    32-38 restricted areas, 40-45 anchorage areas, 56-58 security alerts,
    64-76 distress areas, 80-85 instructions, 88-95 information, 96-108 chart
    features, 112-114 reports from ship, 120-122 routes, 125 = other (see the
    associated text), 126 = cancel the area identified by linkage,
    127 = undefined (default).

    duration is the notice lifetime in minutes measured from the UTC timestamp,
    with 0 = cancel this notice and 262143 = N/A (default).

    linkage ties the notice to a text message sent with the same linkage ID;
    in this context it also acts as the identifier of the area itself, which
    is what a notice of 126 cancels.

    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_imo289_area_notice_broadcast
    """
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=22, signed=False)
    linkage = bit_field(10, int, default=0, signed=False)
    notice = bit_field(7, int, default=127, signed=False)
    month = bit_field(4, int, default=0, signed=False)
    day = bit_field(5, int, default=0, signed=False)
    hour = bit_field(5, int, default=24, signed=False)
    minute = bit_field(6, int, default=60, signed=False)
    duration = bit_field(18, int, default=262143, signed=False)
    area_data = bit_field(870, bytes, default=b'', variable_length=True)

    @property
    def sub_areas(self) -> typing.List[typing.Dict[str, typing.Any]]:
        """Decode the 1-10 sub-area indications (shape and shape-specific fields)."""
        return _decode_area_notice_subareas(self.area_data)


@attr.s(slots=True)
class MessageType8Dac1Fid24(Payload):
    """Extended Ship Static and Voyage Related Data (IMO289). DAC=1, FID=24.

    Used by a ship to report height over keel (air draught), port-call
    history, the operational status of a long list of SOLAS-required
    navigational equipment, ice class, and other voyage-related data.
    Replaces a deprecated trial message from IMO236. Fixed length: 360 bits.

    airdraught is stored in 0.01 m units (1-8190 -> 0.01-81.90 m). IMO289
    documents the special value 81.91 m ("81.91 = >= 81.91 m") which is only
    representable if the true step size is 0.01 m rather than the 0.1 m the
    prose states elsewhere in the standard; gpsd's AIVDM reference notes this
    same inconsistency and uses the 0.01 m step, which is what is used here.

    Each `*_state` field reports the operational status of one piece of
    equipment using the "SOLAS Status" codes (0 = not available/requested,
    1 = operational, 2 = not operational, 3 = no data).

    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_imo289_extended_ship_static_and_voyage_related_data
    """
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=24, signed=False)
    linkage = bit_field(10, int, default=0, signed=False)
    airdraught = bit_field(13, float, from_converter=from_100th, to_converter=to_100th, default=0, signed=False)
    lastport = bit_field(30, str, default='')
    nextport = bit_field(30, str, default='')
    secondport = bit_field(30, str, default='')
    ais_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    ata_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    bnwas_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    ecdisb_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    chart_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    sounder_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    epaid_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    steer_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    gnss_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    gyro_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    lrit_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    magcomp_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    navtex_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    arpa_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    sband_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    xband_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    hfradio_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    inmarsat_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    mfradio_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    vhfradio_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    grndlog_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    waterlog_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    thd_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    tcs_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    vdr_state = bit_field(2, int, default=SOLASStatus.NotAvailable, signed=False, from_converter=SOLASStatus.from_value, to_converter=SOLASStatus.from_value)
    spare_2 = bit_field(2, bytes, default=b'', is_spare=True)
    iceclass = bit_field(4, int, default=IceClass.NotAvailable, signed=False, from_converter=IceClass.from_value, to_converter=IceClass.from_value)
    horsepower = bit_field(18, int, default=262143, signed=False)
    vhfchan = bit_field(12, int, default=0, signed=False)
    lshiptype = bit_field(42, str, default='')
    tonnage = bit_field(18, int, default=262143, signed=False)
    lading = bit_field(2, int, default=0, signed=False)
    heavyoil = bit_field(2, int, default=0, signed=False)
    lightoil = bit_field(2, int, default=0, signed=False)
    dieseloil = bit_field(2, int, default=0, signed=False)
    totaloil = bit_field(14, int, default=16382, signed=False)
    persons = bit_field(13, int, default=0, signed=False)
    spare_3 = bit_field(10, bytes, default=b'', is_spare=True)


@attr.s(slots=True)
class MessageType8Dac1Fid26(Payload):
    """Environmental (IMO289). DAC=1, FID=26.

    Broadcasts one or more sensor readings from a fixed shore-based or
    moored sensor site: location, wind, water level, currents, sea state,
    salinity, weather, or air gap/air draught, each with its own payload
    layout selected by the sensor report type.

    Variable length: a fixed 56-bit header followed by 1 to 5 sensor
    records of 112 bits each, so 168 to 616 bits in total. The records
    live in a raw region; use `.reports` to decode them.

    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_imo289_environmental
    """
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=26, signed=False)
    reports_data = bit_field(560, bytes, default=b'', variable_length=True)

    @property
    def reports(self) -> typing.List[typing.Dict[str, typing.Any]]:
        """Decode the 1-5 sensor records (report type and type-specific fields)."""
        return _decode_environmental_reports(self.reports_data)


@attr.s(slots=True)
class MessageType8Dac1Fid27(Payload):
    """Route Information (broadcast) (IMO289). DAC=1, FID=27.

    Conveys a start time and a list of waypoints describing a course. There
    is an addressed equivalent, Message 6, DAC=1/FID=28, using the same
    fields and waypoint records behind a different (addressed) header.

    Variable length: a fixed 117-bit header followed by 1 to 16 waypoints
    of 55 bits each, so 172 to 997 bits in total. The waypoints live in a
    raw region; use `.waypoints` to decode them, bounded by `waycount`.

    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_imo289_route_information_broadcast
    """
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=27, signed=False)
    linkage = bit_field(10, int, default=0, signed=False)
    sender = bit_field(3, int, default=0, signed=False)
    rtype = bit_field(5, int, default=0, signed=False)
    month = bit_field(4, int, default=0, signed=False)
    day = bit_field(5, int, default=0, signed=False)
    hour = bit_field(5, int, default=24, signed=False)
    minute = bit_field(6, int, default=60, signed=False)
    duration = bit_field(18, int, default=262143, signed=False)
    waycount = bit_field(5, int, default=0, signed=False)
    waypoints_data = bit_field(880, bytes, default=b'', variable_length=True)

    @property
    def waypoints(self) -> typing.List[typing.Dict[str, float]]:
        """Decode up to `waycount` (lon, lat) waypoints, 55 bits each."""
        return _decode_route_waypoints(self.waypoints_data, self.waycount)


@attr.s(slots=True)
class MessageType8Dac1Fid29(Payload):
    """IMO289 Text description (broadcast). DAC=1, FID=29.

    This message is intended to provide a text annotation to another message
    via the Message Linkage ID field.

    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_imo289_text_description_broadcast
    """

    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=29, signed=False)
    linkage = bit_field(10, int, default=0, signed=False)
    description = bit_field(966, str, default="", variable_length=True)


@attr.s(slots=True)
class MessageType8Dac1Fid31(Payload):
    """Meteorological and hydrological data (IMO289).
    DAC=1, FID=31."""
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dac = bit_field(10, int, default=1, signed=False)
    fid = bit_field(6, int, default=31, signed=False)
    lon = bit_field(25, float, from_converter=from_lat_lon_60000, to_converter=to_lat_lon_60000, signed=True, default=0)
    lat = bit_field(24, float, from_converter=from_lat_lon_60000, to_converter=to_lat_lon_60000, signed=True, default=0)
    accuracy = bit_field(1, bool, default=False, signed=False)
    day = bit_field(5, int, default=0, signed=False)
    hour = bit_field(5, int, default=24, signed=False)
    minute = bit_field(6, int, default=60, signed=False)
    wspeed = bit_field(7, int, default=127, signed=False)
    wgust = bit_field(7, int, default=127, signed=False)
    wdir = bit_field(9, int, default=360, signed=False)
    wgustdir = bit_field(9, int, default=360, signed=False)
    airtemp = bit_field(11, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    humidity = bit_field(7, int, default=101, signed=False)
    dewpoint = bit_field(10, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    pressure = bit_field(9, int, from_converter=from_press799, to_converter=to_press799, default=0, signed=False)
    pressuretend = bit_field(2, int, default=3, signed=False)
    visgreater = bit_field(1, bool, default=False, signed=False)
    visibility = bit_field(7, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    waterlevel = bit_field(12, float, from_converter=from_wl31, to_converter=to_wl31, default=0, signed=False)
    leveltrend = bit_field(2, int, default=3, signed=False)
    cspeed = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    cdir = bit_field(9, int, default=360, signed=False)
    cspeed2 = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    cdir2 = bit_field(9, int, default=360, signed=False)
    cdepth2 = bit_field(5, int, default=31, signed=False)
    cspeed3 = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    cdir3 = bit_field(9, int, default=360, signed=False)
    cdepth3 = bit_field(5, int, default=31, signed=False)
    waveheight = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    waveperiod = bit_field(6, int, default=63, signed=False)
    wavedir = bit_field(9, int, default=360, signed=False)
    swellheight = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    swellperiod = bit_field(6, int, default=63, signed=False)
    swelldir = bit_field(9, int, default=360, signed=False)
    seastate = bit_field(4, int, default=13, signed=False)
    watertemp = bit_field(10, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    preciptype = bit_field(3, int, default=7, signed=False)
    salinity = bit_field(9, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    ice = bit_field(2, int, default=3, signed=False)


@attr.s(slots=True)
class MessageType8Dac200Fid10(Payload):
    """
    Binary broadcast
    Inland variant with dac=200, fid=10

    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_8_binary_broadcast_message
    Msg variant: ECE/TRANS/SC.3/176 page 37
    https://unece.org/fileadmin/DAM/trans/doc/finaldocs/sc3/ECE-TRANS-SC3-176e.pdf
    """

    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b"", is_spare=True)
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
    spare = bit_field(8, bytes, default=b'', is_spare=True)


@attr.s(slots=True)
class MessageType8Dac200Fid23(Payload):
    """
    Binary broadcast
    Inland variant with DAC = 200 FID = 23

    EMMA warning

    https://gpsd.gitlab.io/gpsd/AIVDM.html#_emma_warning_report_inland_ais
    """

    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b"", is_spare=True)
    dac = bit_field(10, int, default=200, signed=False)
    fid = bit_field(6, int, default=23, signed=False)

    start_year = bit_field(8, int, default=0, signed=False)
    start_month = bit_field(4, int, default=0, signed=False)
    start_day = bit_field(5, int, default=0, signed=False)

    end_year = bit_field(8, int, default=0, signed=False)
    end_month = bit_field(4, int, default=0, signed=False)
    end_day = bit_field(5, int, default=0, signed=False)

    start_hour = bit_field(5, int, default=24, signed=False)
    start_minute = bit_field(6, int, default=60, signed=False)

    end_hour = bit_field(5, int, default=24, signed=False)
    end_minute = bit_field(6, int, default=60, signed=False)

    start_lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    start_lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)

    end_lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    end_lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)

    type = bit_field(4, int, default=EMMATypeCodes.NA, signed=False, from_converter=EMMATypeCodes.from_value, to_converter=EMMATypeCodes.from_value)
    min = bit_field(9, int, default=255, signed=True)
    max = bit_field(9, int, default=255, signed=True)
    intensity = bit_field(2, int, default=0, signed=False)
    wind = bit_field(4, int, default=EMMAWinds.NA, signed=False, from_converter=EMMAWinds.from_value, to_converter=EMMAWinds.from_value)
    spare_2 = bit_field(6, bytes, default=b'', is_spare=True)


@attr.s(slots=True)
class MessageType8Dac200Fid24(Payload):
    """
    Binary broadcast
    Inland variant with DAC = 200 FID = 24

    Water level

    https://gpsd.gitlab.io/gpsd/AIVDM.html#_water_levels_inland_ais
    """

    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b"", is_spare=True)
    dac = bit_field(10, int, default=200, signed=False)
    fid = bit_field(6, int, default=24, signed=False)

    country = bit_field(12, str, default='', variable_length=False)

    # 4 x 25 bits
    gauge_id_1 = bit_field(11, int, default=0, signed=False)
    water_level_1 = bit_field(14, int, default=0, signed=True)
    gauge_id_2 = bit_field(11, int, default=0, signed=False)
    water_level_2 = bit_field(14, int, default=0, signed=True)
    gauge_id_3 = bit_field(11, int, default=0, signed=False)
    water_level_3 = bit_field(14, int, default=0, signed=True)
    gauge_id_4 = bit_field(11, int, default=0, signed=False)
    water_level_4 = bit_field(14, int, default=0, signed=True)

    @property
    def gauges(self) -> list[tuple[int, int]]:
        """Returns an array of four tuples (gauge-id, water-level)"""
        return [
            (self.gauge_id_1, self.water_level_1),
            (self.gauge_id_2, self.water_level_2),
            (self.gauge_id_3, self.water_level_3),
            (self.gauge_id_4, self.water_level_4),
        ]


@attr.s(slots=True)
class MessageType8Dac200Fid40(Payload):
    """
    Binary broadcast
    Inland variant with DAC = 200 FID = 40

    Signal strength

    https://gpsd.gitlab.io/gpsd/AIVDM.html#_signal_strength_inland_ais
    """

    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b"", is_spare=True)
    dac = bit_field(10, int, default=200, signed=False)
    fid = bit_field(6, int, default=40, signed=False)

    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)

    form = bit_field(4, int, default=0, signed=False)
    facing = bit_field(9, int, default=0, signed=False)
    direction = bit_field(3, int, default=0, signed=False, from_converter=SignalImpact.from_value, to_converter=SignalImpact.from_value)

    # The spec encodes nine signal states as decimal digits inside a 30-bit integer field
    status_raw = bit_field(30, int, default=0, signed=False)

    spare_2 = bit_field(11, bytes, default=b"", signed=False, is_spare=True)

    @property
    def status(self) -> list[SignalStatus]:
        n = self.status_raw
        result = [SignalStatus.Unknown] * 9
        for i in range(8, -1, -1):
            result[i] = SignalStatus(n % 10)
            n //= 10

        return result

# ---------------------------------------------------------------------------
# DAC/FID dispatch tables
# ---------------------------------------------------------------------------


_MSG8_VARIANTS: typing.Dict[typing.Tuple[int, int], typing.Type[Payload]] = {
    (1, 0): MessageType8Dac1Fid0,
    (1, 11): MessageType8Dac1Fid11,
    (1, 16): MessageType8Dac1Fid16,
    (1, 17): MessageType8Dac1Fid17,
    (1, 19): MessageType8Dac1Fid19,
    (1, 20): MessageType8Dac1Fid20,
    (1, 21): MessageType8Dac1Fid21,
    (1, 22): MessageType8Dac1Fid22,
    (1, 24): MessageType8Dac1Fid24,
    (1, 26): MessageType8Dac1Fid26,
    (1, 27): MessageType8Dac1Fid27,
    (1, 29): MessageType8Dac1Fid29,
    (1, 31): MessageType8Dac1Fid31,
    (200, 10): MessageType8Dac200Fid10,
    (200, 23): MessageType8Dac200Fid23,
    (200, 24): MessageType8Dac200Fid24,
    (200, 40): MessageType8Dac200Fid40,
}


def _msg8_variant(dac: int, fid: int) -> typing.Optional[typing.Type[Payload]]:
    """Return the MessageType8 subclass for a (DAC, FID) pair, or None for the default."""
    return _MSG8_VARIANTS.get((dac, fid))


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
    spare_1 = bit_field(3, bytes, default=b'', is_spare=True)
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
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    dest_mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_2 = bit_field(2, bytes, default=b'', is_spare=True)


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
    spare_1 = bit_field(1, bytes, default=b'', is_spare=True)
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
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
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
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    mmsi1 = bit_field(30, int, default=0, from_converter=from_mmsi)
    type1_1 = bit_field(6, int, default=0, signed=False)
    offset1_1 = bit_field(12, int, default=0, signed=False)
    spare_2 = bit_field(2, bytes, default=b'', is_spare=True)
    type1_2 = bit_field(6, int, default=0, signed=False)
    offset1_2 = bit_field(12, int, default=0, signed=False)
    spare_3 = bit_field(2, bytes, default=b'', is_spare=True)
    mmsi2 = bit_field(30, int, default=0, from_converter=from_mmsi)
    type2_1 = bit_field(6, int, default=0, signed=False)
    offset2_1 = bit_field(12, int, default=0, signed=False)
    spare_4 = bit_field(2, bytes, default=b'', is_spare=True)


@attr.s(slots=True)
class MessageType16DestinationA(Payload):
    """
    Assignment Mode Command (short)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_16_assignment_mode_command
    """
    msg_type = bit_field(6, int, default=16, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)

    mmsi1 = bit_field(30, int, default=0, from_converter=from_mmsi)
    offset1 = bit_field(12, int, default=0, signed=False)
    increment1 = bit_field(10, int, default=0, signed=False)
    spare_2 = bit_field(4, bytes, default=b'', is_spare=True)


@attr.s(slots=True)
class MessageType16DestinationAB(Payload):
    """
    Assignment Mode Command (long)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_16_assignment_mode_command
    """
    msg_type = bit_field(6, int, default=16, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)

    mmsi1 = bit_field(30, int, default=0, from_converter=from_mmsi)
    offset1 = bit_field(12, int, default=0, signed=False)
    increment1 = bit_field(10, int, default=0, signed=False)

    mmsi2 = bit_field(30, int, default=0, from_converter=from_mmsi)
    offset2 = bit_field(12, int, default=0, signed=False)
    increment2 = bit_field(10, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType16(Payload):
    """If the message is 96 bits long, it should be interpreted as an assignment for a single station (92 bits)
    followed by 4 bits of padding reserved for future use. If the message is 144 bits long it should be
    interpreted as a channel assignment for two stations; no padding follows."""
    @classmethod
    def create(cls, **kwargs: typing.Union[str, float, int, bool, bytes]) -> "ANY_MESSAGE":
        if 'mmsi2' in kwargs:
            return MessageType16DestinationAB.create(**kwargs)
        return MessageType16DestinationA.create(**kwargs)

    @classmethod
    def from_vector(cls, bv: bit_vector) -> "ANY_MESSAGE":
        if len(bv) > 96:
            return MessageType16DestinationAB.from_vector(bv)
        return MessageType16DestinationA.from_vector(bv)


@attr.s(slots=True)
class MessageType17(Payload):
    """
    DGNSS Broadcast Binary Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_17_dgnss_broadcast_binary_message
    """
    msg_type = bit_field(6, int, default=17, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)
    # Note that latitude and longitude are in units of a tenth of a minute
    lon = bit_field(18, float, from_converter=from_10th, to_converter=to_10th, default=0)
    lat = bit_field(17, float, from_converter=from_10th, to_converter=to_10th, default=0)
    spare_2 = bit_field(5, bytes, default=b'', is_spare=True)
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

    @classmethod
    def _fast_path(cls, bv: bit_vector) -> 'MessageType18':
        v = bv._value
        # Lon
        lx = (v >> 83) & 0xFFFFFFF
        if lx & 0x8000000:
            lx -= 0x10000000
        # Lat
        ly = (v >> 56) & 0x7FFFFFF
        if ly & 0x4000000:
            ly -= 0x8000000

        return cls(
            v >> 162,
            (v >> 160) & 0x3,
            (v >> 130) & 0x3fffffff,  # type: ignore
            (v >> 122) & 0xff,
            to_speed((v >> 112) & 0x3ff),
            bool((v >> 111) & 0x1),
            to_lat_lon(lx),
            to_lat_lon(ly),
            to_10th((v >> 44) & 0xfff),
            (v >> 35) & 0x1ff,
            (v >> 29) & 0x3f,
            (v >> 27) & 0x3,
            bool((v >> 26) & 0x1),
            bool((v >> 25) & 0x1),
            bool((v >> 24) & 0x1),
            bool((v >> 23) & 0x1),
            bool((v >> 22) & 0x1),
            bool((v >> 21) & 0x1),
            bool((v >> 20) & 0x1),
            v & 0xfffff,
        )


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
    spare_1 = bit_field(4, bytes, default=b'', is_spare=True)


@attr.s(slots=True)
class MessageType20(Payload):
    """
    Data Link Management Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_20_data_link_management_message
    """
    msg_type = bit_field(6, int, default=20, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)

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
    spare_1 = bit_field(1, bytes, default=b'', is_spare=True)
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
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)

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
    spare_2 = bit_field(23, bytes, default=b'', is_spare=True)


@attr.s(slots=True)
class MessageType22Broadcast(Payload):
    """
    Channel Management
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_22_channel_management
    """
    msg_type = bit_field(6, int, default=22, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)

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
    spare_2 = bit_field(23, bytes, default=b'', is_spare=True)


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
    def from_vector(cls, bv: bit_vector) -> "ANY_MESSAGE":
        if bv.get(139, 1):
            return MessageType22Addressed.from_vector(bv)
        else:
            return MessageType22Broadcast.from_vector(bv)


@attr.s(slots=True)
class MessageType23(Payload):
    """
    Group Assignment Command
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_23_group_assignment_command
    """
    msg_type = bit_field(6, int, default=23, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)
    spare_1 = bit_field(2, bytes, default=b'', is_spare=True)

    ne_lon = bit_field(18, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    ne_lat = bit_field(17, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    sw_lon = bit_field(18, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    sw_lat = bit_field(17, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)

    station_type = bit_field(4, int, default=0, from_converter=StationType.from_value, to_converter=StationType.from_value)
    ship_type = bit_field(8, int, default=0, from_converter=ShipType.from_value, to_converter=ShipType.from_value)
    spare_2 = bit_field(22, bytes, default=b'', is_spare=True)

    txrx = bit_field(2, int, default=0, from_converter=TransmitMode.from_value, to_converter=TransmitMode.from_value, signed=False)
    interval = bit_field(4, int, default=0, from_converter=StationIntervals.from_value, to_converter=StationIntervals.from_value)
    quiet = bit_field(4, int, default=0, signed=False)
    spare_3 = bit_field(6, bytes, default=b'', is_spare=True)


@attr.s(slots=True)
class MessageType24PartA(Payload):
    msg_type = bit_field(6, int, default=24, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    partno = bit_field(2, int, default=0, signed=False)
    shipname = bit_field(120, str, default='')
    spare_1 = bit_field(8, bytes, default=b'', is_spare=True)


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

    spare_1 = bit_field(6, bytes, default=b'', is_spare=True)


@attr.s(slots=True)
class MessageType24PartBAuxiliaryCraft(Payload):
    """
    Static Data Report - Part B (Auxiliary Craft Variant)

    When the MMSI follows the pattern 98XXXYYYY (auxiliary craft),
    bits 132-161 contain the mothership MMSI instead of vessel dimensions.

    See ITU-R M.1371-5 for specification details.
    """
    msg_type = bit_field(6, int, default=24, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    partno = bit_field(2, int, default=0, signed=False)
    ship_type = bit_field(8, int, default=0, signed=False)
    vendorid = bit_field(18, str, default='', signed=False)
    model = bit_field(4, int, default=0, signed=False)
    serial = bit_field(20, int, default=0, signed=False)
    callsign = bit_field(42, str, default='')

    mothership_mmsi = bit_field(30, int, from_converter=from_mmsi)

    spare_1 = bit_field(6, bytes, default=b'', is_spare=True)


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
        mmsi: int = int(kwargs.get('mmsi', 0))
        partno: int = int(kwargs.get('partno', 0))
        if partno == 0:
            return MessageType24PartA.create(**kwargs)
        elif partno == 1:
            if is_auxiliary_craft(mmsi):
                return MessageType24PartBAuxiliaryCraft.create(**kwargs)
            return MessageType24PartB.create(**kwargs)
        else:
            raise UnknownPartNoException(f"Partno {partno} is not allowed!")

    @classmethod
    def from_vector(cls, bv: bit_vector) -> "ANY_MESSAGE":
        mmsi: int = bv.get(8, 30)
        partno: int = bv.get(38, 2)
        if partno == 0:
            return MessageType24PartA.from_vector(bv)
        elif partno == 1:
            if is_auxiliary_craft(mmsi):
                return MessageType24PartBAuxiliaryCraft.from_vector(bv)
            return MessageType24PartB.from_vector(bv)
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
    def from_vector(cls, bv: bit_vector) -> "ANY_MESSAGE":
        addressed: int = bv.get(38, 1)
        structured: int = bv.get(39, 1)

        if addressed:
            if structured:
                return MessageType25AddressedStructured.from_vector(bv)
            else:
                return MessageType25AddressedUnstructured.from_vector(bv)
        else:
            if structured:
                return MessageType25BroadcastStructured.from_vector(bv)
            else:
                return MessageType25BroadcastUnstructured.from_vector(bv)


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
                return MessageType26BroadcastStructured.create(**kwargs)
            else:
                return MessageType26BroadcastUnstructured.create(**kwargs)

    @classmethod
    def from_vector(cls, bv: bit_vector) -> "ANY_MESSAGE":
        addressed: int = bv.get(38, 1)
        structured: int = bv.get(39, 1)

        if addressed:
            if structured:
                return MessageType26AddressedStructured.from_vector(bv)
            else:
                return MessageType26AddressedUnstructured.from_vector(bv)
        else:
            if structured:
                return MessageType26BroadcastStructured.from_vector(bv)
            else:
                return MessageType26BroadcastUnstructured.from_vector(bv)


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
    status = bit_field(4, int, default=NavigationStatus.Undefined, from_converter=NavigationStatus.from_value, to_converter=NavigationStatus, signed=False)
    lon = bit_field(18, float, from_converter=from_lat_lon_600, to_converter=to_lat_lon_600, default=0, signed=True)
    lat = bit_field(17, float, from_converter=from_lat_lon_600, to_converter=to_lat_lon_600, default=0, signed=True)
    speed = bit_field(6, float, default=0, signed=False)
    course = bit_field(9, float, default=0, signed=False)
    gnss = bit_field(1, bool, default=0, signed=False)
    spare_1 = bit_field(1, bytes, default=b'', is_spare=True)


@attr.s(slots=True)
class MessageType28(Payload):
    """
    Aid-to-Navigation Report (Single-slot message)
    Defined in ITU-R M.1371-6

    NOTE: provides similar information as AIS Message 21, but in one slot versus two slot.
    """
    msg_type = bit_field(6, int, default=28, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi)

    second = bit_field(6, int, default=0, signed=False)
    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    restricted = bit_field(2, int, default=0, signed=False, from_converter=AtoNRestrictedUseInidicator, to_converter=AtoNRestrictedUseInidicator)
    station_type = bit_field(3, int, default=0, from_converter=AtoNSationType.from_value, to_converter=AtoNSationType.from_value)
    aid_type = bit_field(7, int, default=0, from_converter=NavAid.from_value, to_converter=NavAid.from_value, signed=False)
    iala_mrn = bit_field(17, int, default=0, signed=False)

    dimension = bit_field(4, int, default=0, signed=False, from_converter=AtoNDimensionType, to_converter=AtoNDimensionType)
    dimensions_a = bit_field(9, int, default=0, signed=False)
    dimensions_b = bit_field(11, int, default=0, signed=False)
    dimension_additional_data = bit_field(1, int, default=0, signed=False)
    charted_status = bit_field(1, int, default=0, signed=False)
    station_status = bit_field(4, int, default=0, signed=False)
    status_bits = bit_field(8, int, default=0, signed=False)
    spare_1 = bit_field(1, bytes, default=b'', signed=False, is_spare=True)
    auth = bit_field(1, int, default=0, signed=False)

    def parse_dimensions(self) -> ParsedDimensions:
        """Parse the dimensions according to ITU-R M.1371-6 table 84"""
        return parse_dimensions(self.dimension, self.dimensions_a, self.dimensions_b)

    @property
    def has_multiple_dimension_types(self) -> bool:
        """Whether this AtoN uses multiple dimension types for the same MMSI"""
        return bool(self.dimension_additional_data == 1)


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
    28: MessageType28,
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
    MessageType8Dac1Fid0,
    MessageType8Dac1Fid11,
    MessageType8Dac1Fid16,
    MessageType8Dac1Fid17,
    MessageType8Dac1Fid19,
    MessageType8Dac1Fid20,
    MessageType8Dac1Fid21NonWmo,
    MessageType8Dac1Fid22,
    MessageType8Dac1Fid24,
    MessageType8Dac1Fid26,
    MessageType8Dac1Fid27,
    MessageType8Dac1Fid29,
    MessageType8Dac1Fid31,
    MessageType8Dac200Fid10,
    MessageType8Dac200Fid23,
    MessageType8Dac200Fid24,
    MessageType8Dac200Fid40,
    MessageType9,
    MessageType10,
    MessageType11,
    MessageType12,
    MessageType13,
    MessageType14,
    MessageType15,
    MessageType16DestinationA,
    MessageType16DestinationAB,
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
    MessageType28,
]

# This is only there for backwards compatibility
NMEAMessage = AISSentence

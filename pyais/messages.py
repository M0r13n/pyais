import abc
import json
import typing
from typing import Any, Dict, Optional, Sequence, Union

import attr
from bitarray import bitarray

from pyais.constants import TalkerID, NavigationStatus, ManeuverIndicator, EpfdType, ShipType, NavAid, StationType, \
    TransmitMode, StationIntervals
from pyais.exceptions import InvalidNMEAMessageException, UnknownMessageException, UnknownPartNoException, \
    InvalidDataTypeException
from pyais.util import decode_into_bit_array, compute_checksum, int_to_bin, str_to_bin, \
    encode_ascii_6, from_bytes, int_to_bytes, from_bytes_signed, decode_bin_as_ascii6, get_int, chk_to_int

NMEA_VALUE = typing.Union[str, float, int, bool, bytes]


def validate_message(msg: bytes) -> None:
    """
    Validates a given message.
    It checks if the messages complies with the AIS standard.
    It is based on:
        1. https://en.wikipedia.org/wiki/Automatic_identification_system
        2. https://en.wikipedia.org/wiki/NMEA_0183

    If not errors are found, nothing is returned.
    Otherwise an InvalidNMEAMessageException is raised.
    """
    values = msg.split(b",")

    # A message has exactly 7 comma separated values
    if len(values) != 7:
        raise InvalidNMEAMessageException(
            "A NMEA message needs to have exactly 7 comma separated entries."
        )

    # The only allowed blank value may be the message ID
    if not values[0]:
        raise InvalidNMEAMessageException(
            "The NMEA message type is empty!"
        )

    if not values[1]:
        raise InvalidNMEAMessageException(
            "Number of sentences is empty!"
        )

    if not values[2]:
        raise InvalidNMEAMessageException(
            "Sentence number is empty!"
        )

    if not values[5]:
        raise InvalidNMEAMessageException(
            "The NMEA message body (payload) is empty."
        )

    if not values[6]:
        raise InvalidNMEAMessageException(
            "NMEA checksum (NMEA 0183 Standard CRC16) is empty."
        )

    try:
        sentence_num = int(values[1])
        if sentence_num > 0xff:
            raise InvalidNMEAMessageException(
                "Number of sentences exceeds limit of 9 total sentences."
            )
    except ValueError:
        raise InvalidNMEAMessageException(
            "Invalid sentence number. No Number."
        )

    if values[2]:
        try:
            sentence_num = int(values[2])
            if sentence_num > 0xff:
                raise InvalidNMEAMessageException(
                    " Sentence number exceeds limit of 9 total sentences."
                )
        except ValueError:
            raise InvalidNMEAMessageException(
                "Invalid Sentence number. No Number."
            )

    if values[3]:
        try:
            sentence_num = int(values[3])
            if sentence_num > 0xff:
                raise InvalidNMEAMessageException(
                    "Number of sequential message ID exceeds limit of 9 total sentences."
                )
        except ValueError:
            raise InvalidNMEAMessageException(
                "Invalid  sequential message ID. No Number."
            )

    # It should not have more than 82 chars of payload
    if len(values[5]) > 82:
        raise InvalidNMEAMessageException(
            f"{msg.decode('utf-8')} has more than 82 characters of payload."
        )


def bit_field(width: int, d_type: typing.Type[typing.Any],
              from_converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
              to_converter: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None,
              default: typing.Optional[typing.Any] = None,
              signed: bool = False,
              **kwargs: typing.Any) -> typing.Any:
    """
    Simple wrapper around the attr.ib interface to be used in conjunction with the Payload class.

    @param width:               The bit-width of the field.
    @param d_type:              The datatype of the fields value.
    @param from_converter:      Optional converter function called **before** encoding
    @param to_converter:        Optional converter function called **after** decoding
    @param default:             Optional default value to be used when no value is explicitly passed.
    @param signed:              Set to true if the value is a signed integer
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
        },
        **kwargs
    )


ENUM_FIELDS = {'status', 'maneuver', 'epfd', 'ship_type', 'aid_type', 'station_type', 'txrx', 'interval'}


class NMEAMessage(object):
    __slots__ = (
        'ais_id',
        'raw',
        'talker',
        'type',
        'frag_cnt',
        'frag_num',
        'seq_id',
        'channel',
        'payload',
        'fill_bits',
        'checksum',
        'bit_array'
    )

    def __init__(self, raw: bytes) -> None:
        if not isinstance(raw, bytes):
            raise ValueError(f"'NMEAMessage' only accepts bytes, but got '{type(raw)}'")

        validate_message(raw)

        # Initial values
        self.checksum: int = -1

        # Store raw data
        self.raw: bytes = raw

        # An AIS NMEA message consists of seven, comma separated parts
        values = raw.split(b",")

        # Unpack NMEA message parts
        (
            head,
            message_fragments,
            fragment_number,
            message_id,
            channel,
            payload,
            checksum
        ) = values

        # The talker is identified by the next 2 characters
        talker: str = head[1:3].decode('ascii')
        self.talker: TalkerID = TalkerID(talker)

        # The type of message is then identified by the next 3 characters
        self.type: str = head[3:].decode('ascii')

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

        fill, check = chk_to_int(checksum)
        # Fill bits (0 to 5)
        self.fill_bits: int = fill
        # Message Checksum (hex value)
        self.checksum = check

        # Finally decode bytes into bits
        self.bit_array: bitarray = decode_into_bit_array(self.payload, self.fill_bits)
        self.ais_id: int = get_int(self.bit_array, 0, 6)

    def __str__(self) -> str:
        return str(self.raw)

    def __getitem__(self, item: str) -> Union[int, str, bytes, bitarray]:
        if isinstance(item, str):
            try:
                return getattr(self, item)  # type: ignore
            except AttributeError:
                raise KeyError(item)
        else:
            raise TypeError(f"Index must be str, not {type(item).__name__}")

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

    def __eq__(self, other: object) -> bool:
        return all([getattr(self, attr) == getattr(other, attr) for attr in self.__slots__])

    @classmethod
    def from_string(cls, nmea_str: str) -> "NMEAMessage":
        return cls(nmea_str.encode('utf-8'))

    @classmethod
    def from_bytes(cls, nmea_byte_str: bytes) -> "NMEAMessage":
        return cls(nmea_byte_str)

    @classmethod
    def assemble_from_iterable(cls, messages: Sequence["NMEAMessage"]) -> "NMEAMessage":
        """
        Assemble a multiline message from a sequence of NMEA messages.
        :param messages: Sequence of NMEA messages
        :return: Single message
        """
        raw = b''
        data = b''
        bit_array = bitarray()

        for i, msg in enumerate(sorted(messages, key=lambda m: m.frag_num)):
            if i > 0:
                raw += b'\n'
            raw += msg.raw
            data += msg.payload
            bit_array += msg.bit_array

        messages[0].raw = raw
        messages[0].payload = data
        messages[0].bit_array = bit_array
        return messages[0]

    @property
    def is_valid(self) -> bool:
        return self.checksum == compute_checksum(self.raw)

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
        Decode the NMEA message.
        @return: The decoded message class as a superclass of `Payload`.

        >>> nmea = NMEAMessage(b"!AIVDO,1,1,,,B>qc:003wk?8mP=18D3Q3wgTiT;T,0*13").decode()
        MessageType18(msg_type=18, repeat=0, mmsi='1000000000', reserved=0, speed=1023,
         accuracy=0, lon=181.0, lat=91.0, course=360.0, heading=511, second=31,
         reserved_2=0, cs=True, display=False, dsc=False, band=True, msg22=True,
         assigned=False, raim=False, radio=410340)
        """
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

    @classmethod
    def fields(cls) -> typing.Tuple[typing.Any]:
        """
        A list of all fields that were added to this class using attrs.
        """
        return attr.fields(cls)  # type:ignore

    def to_bitarray(self) -> bitarray:
        """
        Convert a payload to binary.
        """
        out = bitarray()
        for field in self.fields():
            width = field.metadata['width']
            d_type = field.metadata['d_type']
            converter = field.metadata['from_converter']
            signed = field.metadata['signed']

            val = getattr(self, field.name)
            if val is None:
                continue

            val = converter(val) if converter is not None else val
            val = d_type(val)

            if d_type == int or d_type == bool:
                bits = int_to_bin(val, width, signed=signed)
            elif d_type == float:
                val = int(val)
                bits = int_to_bin(val, width, signed=signed)
            elif d_type == str:
                bits = str_to_bin(val, width)
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
                args[key] = kwargs[key]
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
        kwargs: typing.Dict[str, typing.Any] = {}

        # Iterate over the bits until the last bit of the bitarray or all fields are fully decoded
        for field in cls.fields():

            if end >= len(bit_arr):
                # All fields that did not fit into the bit array are None
                kwargs[field.name] = None
                continue

            width = field.metadata['width']
            d_type = field.metadata['d_type']
            converter = field.metadata['to_converter']

            end = min(len(bit_arr), cur + width)
            bits = bit_arr[cur: end]

            val: typing.Any
            # Get the correct data type and decoding function
            if d_type == int or d_type == bool or d_type == float:
                shift = (8 - ((end - cur) % 8)) % 8
                if field.metadata['signed']:
                    val = from_bytes_signed(bits) >> shift
                else:
                    val = from_bytes(bits) >> shift
                val = d_type(val)
            elif d_type == str:
                val = decode_bin_as_ascii6(bits)
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
            for slt in self.__slots__:
                val = getattr(self, slt)
                if val is not None and slt in ENUM_FIELDS:
                    val = int(getattr(self, slt))
                d[slt] = val
            return d
        else:
            return {slt: getattr(self, slt) for slt in self.__slots__}

    def to_json(self) -> str:
        return json.dumps(
            self.asdict(),
            indent=4
        )


#
# Conversion functions
#

def from_speed(v: typing.Union[int, float]) -> float:
    return v * 10.0


def to_speed(v: typing.Union[int, float]) -> float:
    return v / 10.0


def from_lat_lon(v: typing.Union[int, float]) -> float:
    return float(v) * 600000.0


def to_lat_lon(v: typing.Union[int, float]) -> float:
    return round(float(v) / 600000.0, 6)


def from_lat_lon_600(v: typing.Union[int, float]) -> float:
    return float(v) * 600.0


def to_lat_lon_600(v: typing.Union[int, float]) -> float:
    return round(float(v) / 600.0, 6)


def from_10th(v: typing.Union[int, float]) -> float:
    return float(v) * 10.0


def to_10th(v: typing.Union[int, float]) -> float:
    return v / 10.0


def from_mmsi(v: typing.Union[str, int]) -> int:
    return int(v)


def to_mmsi(v: typing.Union[str, int]) -> str:
    return str(v).zfill(9)


@attr.s(slots=True)
class MessageType1(Payload):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    """
    msg_type = bit_field(6, int, default=1, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    status = bit_field(4, int, default=0, converter=NavigationStatus.from_value, signed=False)
    turn = bit_field(8, int, default=0, signed=True)
    speed = bit_field(10, float, from_converter=from_speed, to_converter=to_speed, default=0, signed=False)
    accuracy = bit_field(1, int, default=0, signed=False)
    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, default=0, signed=True)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, default=0, signed=True)
    course = bit_field(12, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    heading = bit_field(9, int, default=0, signed=False)
    second = bit_field(6, int, default=0, signed=False)
    maneuver = bit_field(2, int, default=0, from_converter=ManeuverIndicator.from_value,
                         to_converter=ManeuverIndicator.from_value, signed=False)
    spare = bit_field(3, int, default=0)
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
class MessageType4(Payload):
    """
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_4_base_station_report
    """
    msg_type = bit_field(6, int, default=4, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    year = bit_field(14, int, default=1970, signed=False)
    month = bit_field(4, int, default=1, signed=False)
    day = bit_field(5, int, default=1, signed=False)
    hour = bit_field(5, int, default=0, signed=False)
    minute = bit_field(6, int, default=0, signed=False)
    second = bit_field(6, int, default=0, signed=False)
    accuracy = bit_field(1, int, default=0, signed=False)
    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    epfd = bit_field(4, int, default=0, from_converter=EpfdType.from_value, to_converter=EpfdType.from_value,
                     signed=False)
    spare = bit_field(10, int, default=0)
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
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    ais_version = bit_field(2, int, default=0, signed=False)
    imo = bit_field(30, int, default=0, signed=False)
    callsign = bit_field(42, str, default='')
    shipname = bit_field(120, str, default='')
    ship_type = bit_field(8, int, default=0, from_converter=ShipType.from_value, to_converter=ShipType.from_value)
    to_bow = bit_field(9, int, default=0, signed=False)
    to_stern = bit_field(9, int, default=0, signed=False)
    to_port = bit_field(6, int, default=0, signed=False)
    to_starboard = bit_field(6, int, default=0, signed=False)
    epfd = bit_field(4, int, default=0, from_converter=EpfdType.from_value, to_converter=EpfdType.from_value)
    month = bit_field(4, int, default=0, signed=False)
    day = bit_field(5, int, default=0, signed=False)
    hour = bit_field(5, int, default=0, signed=False)
    minute = bit_field(6, int, default=0, signed=False)
    draught = bit_field(8, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    destination = bit_field(120, str, default='')
    dte = bit_field(1, bool, default=0, signed=False)
    spare = bit_field(1, bool, default=0)


@attr.s(slots=True)
class MessageType6(Payload):
    """
    Binary Addresses Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_4_base_station_report
    """
    msg_type = bit_field(6, int, default=6)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    seqno = bit_field(2, int, default=0, signed=False)
    dest_mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    retransmit = bit_field(1, bool, default=False, signed=False)
    spare = bit_field(1, int, default=0)
    dac = bit_field(10, int, default=0, signed=False)
    fid = bit_field(6, int, default=0, signed=False)
    data = bit_field(920, int, default=0, from_converter=int_to_bytes, to_converter=int_to_bytes)


@attr.s(slots=True)
class MessageType7(Payload):
    """
    Binary Acknowledge
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_7_binary_acknowledge
    """
    msg_type = bit_field(6, int, default=7, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    spare = bit_field(2, int, default=0)
    mmsi1 = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
    mmsiseq1 = bit_field(2, int, default=0, signed=False)
    mmsi2 = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
    mmsiseq2 = bit_field(2, int, default=0, signed=False)
    mmsi3 = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
    mmsiseq3 = bit_field(2, int, default=0, signed=False)
    mmsi4 = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
    mmsiseq4 = bit_field(2, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType8(Payload):
    """
    Binary Acknowledge
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_8_binary_broadcast_message
    """
    msg_type = bit_field(6, int, default=8, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    spare = bit_field(2, int, default=0)
    dac = bit_field(10, int, default=0, signed=False)
    fid = bit_field(6, int, default=0, signed=False)
    data = bit_field(952, int, default=0, from_converter=int_to_bytes)


@attr.s(slots=True)
class MessageType9(Payload):
    """
    Standard SAR Aircraft Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_9_standard_sar_aircraft_position_report
    """
    msg_type = bit_field(6, int, default=9, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    alt = bit_field(12, int, default=0, signed=False)
    # speed over ground is in knots, not deciknots
    speed = bit_field(10, int, default=0, signed=False)
    accuracy = bit_field(1, int, default=0, signed=False)
    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    course = bit_field(12, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    second = bit_field(6, int, default=0, signed=False)

    reserved = bit_field(8, int, default=0)
    dte = bit_field(1, bool, default=0)
    spare = bit_field(3, int, default=0)
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
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    spare_1 = bit_field(2, int, default=0)
    dest_mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    spare_2 = bit_field(2, int, default=0)


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
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    seqno = bit_field(2, int, default=0, signed=False)
    dest_mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    retransmit = bit_field(1, bool, default=False, signed=False)
    spare = bit_field(1, int, default=0, signed=False)
    text = bit_field(936, str, default='')


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
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    spare = bit_field(2, int, default=0)
    text = bit_field(968, str, default='')


@attr.s(slots=True)
class MessageType15(Payload):
    """
    Interrogation
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_15_interrogation
    """
    msg_type = bit_field(6, int, default=15, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    spare_1 = bit_field(2, int, default=0, signed=False)
    mmsi1 = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
    type1_1 = bit_field(6, int, default=0, signed=False)
    offset1_1 = bit_field(12, int, default=0, signed=False)
    spare_2 = bit_field(2, int, default=0)
    type1_2 = bit_field(6, int, default=0, signed=False)
    offset1_2 = bit_field(12, int, default=0, signed=False)
    spare_3 = bit_field(2, int, default=0)
    mmsi2 = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
    type2_1 = bit_field(6, int, default=0, signed=False)
    offset2_1 = bit_field(12, int, default=0, signed=False)
    spare_4 = bit_field(2, int, default=0)


@attr.s(slots=True)
class MessageType16(Payload):
    """
    Assignment Mode Command
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_16_assignment_mode_command
    """
    msg_type = bit_field(6, int, default=16, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    spare = bit_field(2, int, default=0)

    mmsi1 = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
    offset1 = bit_field(12, int, default=0, signed=False)
    increment1 = bit_field(10, int, default=0, signed=False)

    mmsi2 = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
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
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    spare_1 = bit_field(2, int, default=0)
    # Note that latitude and longitude are in units of a tenth of a minute
    lon = bit_field(18, float, from_converter=from_10th, to_converter=to_10th, default=0)
    lat = bit_field(17, float, from_converter=from_10th, to_converter=to_10th, default=0)
    spare_2 = bit_field(5, int, default=0)
    data = bit_field(736, int, default=0, from_converter=int_to_bytes)


@attr.s(slots=True)
class MessageType18(Payload):
    """
    Standard Class B CS Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_18_standard_class_b_cs_position_report
    """
    msg_type = bit_field(6, int, default=18, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    reserved = bit_field(8, int, default=0, signed=False)
    speed = bit_field(10, float, from_converter=from_speed, to_converter=to_speed, default=0, signed=False)
    accuracy = bit_field(1, int, default=0, signed=False)
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
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    reserved = bit_field(8, int, default=0)

    speed = bit_field(10, float, from_converter=from_speed, to_converter=to_speed, default=0, signed=False)
    accuracy = bit_field(1, int, default=0, signed=False)
    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    course = bit_field(12, float, from_converter=from_10th, to_converter=to_10th, default=0, signed=False)
    heading = bit_field(9, int, default=0, signed=False)
    second = bit_field(6, int, default=0, signed=False)
    regional = bit_field(4, int, default=0, signed=False)
    shipname = bit_field(120, str, default='')
    ship_type = bit_field(8, int, default=0, from_converter=ShipType.from_value, to_converter=ShipType.from_value,
                          signed=False)
    to_bow = bit_field(9, int, default=0, signed=False)
    to_stern = bit_field(9, int, default=0, signed=False)
    to_port = bit_field(6, int, default=0, signed=False)
    to_starboard = bit_field(6, int, default=0, signed=False)
    epfd = bit_field(4, int, default=0, from_converter=EpfdType.from_value, to_converter=EpfdType.from_value)
    raim = bit_field(1, bool, default=0)
    dte = bit_field(1, bool, default=0)
    assigned = bit_field(1, bool, default=0, signed=False)
    spare = bit_field(4, int, default=0)


@attr.s(slots=True)
class MessageType20(Payload):
    """
    Data Link Management Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_20_data_link_management_message
    """
    msg_type = bit_field(6, int, default=20, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    spare = bit_field(2, int, default=0)

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
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    aid_type = bit_field(5, int, default=0, from_converter=NavAid.from_value, to_converter=NavAid.from_value,
                         signed=False)
    name = bit_field(120, str, default='')

    accuracy = bit_field(1, int, default=0, signed=False)
    lon = bit_field(28, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    lat = bit_field(27, float, from_converter=from_lat_lon, to_converter=to_lat_lon, signed=True, default=0)
    to_bow = bit_field(9, int, default=0, signed=False)
    to_stern = bit_field(9, int, default=0, signed=False)
    to_port = bit_field(6, int, default=0, signed=False)
    to_starboard = bit_field(6, int, default=0, signed=False)

    epfd = bit_field(4, int, default=0, from_converter=EpfdType.from_value, to_converter=EpfdType.from_value)
    second = bit_field(6, int, default=0, signed=False)
    off_position = bit_field(1, bool, default=0)
    regional = bit_field(8, int, default=0, signed=False)
    raim = bit_field(1, bool, default=0)
    virtual_aid = bit_field(1, bool, default=0)
    assigned = bit_field(1, bool, default=0)
    spare = bit_field(1, int, default=0)
    name_ext = bit_field(88, str, default='')


@attr.s(slots=True)
class MessageType22Addressed(Payload):
    """
    Channel Management
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_22_channel_management
    """
    msg_type = bit_field(6, int, default=22, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    spare_1 = bit_field(2, int, default=0)  # 40 bits

    channel_a = bit_field(12, int, default=0, signed=False)
    channel_b = bit_field(12, int, default=0, signed=False)
    txrx = bit_field(4, int, default=0, signed=False)
    power = bit_field(1, bool, default=0)  # 69 bits

    # If it is addressed (addressed field is 1),
    # the same span of data is interpreted as two 30-bit MMSIs
    # beginning at bit offsets 69 and 104 respectively.
    dest1 = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
    empty_1 = bit_field(5, int, default=0)
    dest2 = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
    empty_2 = bit_field(5, int, default=0)

    addressed = bit_field(1, bool, default=0)
    band_a = bit_field(1, bool, default=0)
    band_b = bit_field(1, bool, default=0)
    zonesize = bit_field(3, int, default=0)
    spare_2 = bit_field(23, int, default=0)


@attr.s(slots=True)
class MessageType22Broadcast(Payload):
    """
    Channel Management
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_22_channel_management
    """
    msg_type = bit_field(6, int, default=22, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    spare_1 = bit_field(2, int, default=0)

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
    spare_2 = bit_field(23, int, default=0)


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
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)
    spare_1 = bit_field(2, int, default=0)

    ne_lon = bit_field(18, int, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    ne_lat = bit_field(17, int, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    sw_lon = bit_field(18, int, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)
    sw_lat = bit_field(17, int, from_converter=from_10th, to_converter=to_10th, default=0, signed=True)

    station_type = bit_field(4, int, default=0, from_converter=StationType.from_value,
                             to_converter=StationType.from_value)
    ship_type = bit_field(8, int, default=0, from_converter=ShipType.from_value, to_converter=ShipType.from_value)
    spare_2 = bit_field(22, int, default=0)

    txrx = bit_field(2, int, default=0, from_converter=TransmitMode.from_value, to_converter=TransmitMode.from_value,
                     signed=False)
    interval = bit_field(4, int, default=0, from_converter=StationIntervals.from_value,
                         to_converter=StationIntervals.from_value)
    quiet = bit_field(4, int, default=0, signed=False)
    spare_3 = bit_field(6, int, default=0)


@attr.s(slots=True)
class MessageType24PartA(Payload):
    msg_type = bit_field(6, int, default=24, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    partno = bit_field(2, int, default=0, signed=False)
    shipname = bit_field(120, str, default='')
    spare_1 = bit_field(8, int, default=0)


@attr.s(slots=True)
class MessageType24PartB(Payload):
    msg_type = bit_field(6, int, default=24, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    partno = bit_field(2, int, default=0, signed=False)
    ship_type = bit_field(8, int, default=0, signed=False)
    vendorid = bit_field(18, str, default=0, signed=False)
    model = bit_field(4, int, default=0, signed=False)
    serial = bit_field(20, int, default=0, signed=False)
    callsign = bit_field(42, str, default='')

    to_bow = bit_field(9, int, default=0, signed=False)
    to_stern = bit_field(9, int, default=0, signed=False)
    to_port = bit_field(6, int, default=0, signed=False)
    to_starboard = bit_field(6, int, default=0, signed=False)

    spare_2 = bit_field(6, int, default=0)


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
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    dest_mmsi = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi, signed=False)
    app_id = bit_field(16, int, default=0, signed=False)
    data = bit_field(82, int, default=0, from_converter=int_to_bytes)


@attr.s(slots=True)
class MessageType25BroadcastStructured(Payload):
    msg_type = bit_field(6, int, default=25, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    app_id = bit_field(16, int, default=0, signed=False)
    data = bit_field(112, int, default=0, from_converter=int_to_bytes)


@attr.s(slots=True)
class MessageType25AddressedUnstructured(Payload):
    msg_type = bit_field(6, int, default=25, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    dest_mmsi = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
    data = bit_field(98, int, default=0, from_converter=int_to_bytes)


@attr.s(slots=True)
class MessageType25BroadcastUnstructured(Payload):
    msg_type = bit_field(6, int, default=25, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    data = bit_field(128, int, default=0, from_converter=int_to_bytes)


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
class MessageType26AddressedStructured(Payload):
    msg_type = bit_field(6, int, default=26, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    dest_mmsi = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
    app_id = bit_field(16, int, default=0, signed=False)
    data = bit_field(958, int, default=0, from_converter=int_to_bytes)
    radio = bit_field(20, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType26BroadcastStructured(Payload):
    msg_type = bit_field(6, int, default=26, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    app_id = bit_field(16, int, default=0, signed=False)
    data = bit_field(988, int, default=0, from_converter=int_to_bytes)
    radio = bit_field(20, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType26AddressedUnstructured(Payload):
    msg_type = bit_field(6, int, default=26, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    dest_mmsi = bit_field(30, int, default=0, from_converter=from_mmsi, to_converter=to_mmsi)
    app_id = bit_field(16, int, default=0, signed=False)
    data = bit_field(958, int, default=0, from_converter=int_to_bytes)
    radio = bit_field(20, int, default=0, signed=False)


@attr.s(slots=True)
class MessageType26BroadcastUnstructured(Payload):
    msg_type = bit_field(6, int, default=26, signed=False)
    repeat = bit_field(2, int, default=0, signed=False)
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    addressed = bit_field(1, bool, default=0, signed=False)
    structured = bit_field(1, bool, default=0, signed=False)

    data = bit_field(1004, int, default=0, from_converter=int_to_bytes)
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
                return MessageType26BroadcastStructured.create(**kwargs)
        else:
            if structured:
                return MessageType26AddressedUnstructured.create(**kwargs)
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
    mmsi = bit_field(30, int, from_converter=from_mmsi, to_converter=to_mmsi)

    accuracy = bit_field(1, int, default=0, signed=False)
    raim = bit_field(1, bool, default=0, signed=False)
    status = bit_field(4, int, default=0, from_converter=NavigationStatus, to_converter=NavigationStatus, signed=False)
    lon = bit_field(18, float, from_converter=from_lat_lon_600, to_converter=to_lat_lon_600, default=0)
    lat = bit_field(17, float, from_converter=from_lat_lon_600, to_converter=to_lat_lon_600, default=0)
    speed = bit_field(6, int, default=0, signed=False)
    course = bit_field(9, int, default=0, signed=False)
    gnss = bit_field(1, int, default=0, signed=False)
    spare = bit_field(1, int, default=0)


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
    MessageType8,
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
    MessageType22,
    MessageType23,
    MessageType24,
    MessageType25,
    MessageType26,
    MessageType27,
]

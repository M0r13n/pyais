from typing import Sequence
import json
import typing

from bitarray import bitarray

from pyais.decode import decode
from pyais.util import decode_into_bit_array, get_int, compute_checksum
from pyais.ais_types import AISType
from pyais.exceptions import InvalidNMEAMessageException, InvalidChecksumException


class NMEAMessage(object):
    __slots__ = (
        'ais_id',
        'raw',
        'talker',
        'msg_type',
        'count',
        'index',
        'seq_id',
        'channel',
        'data',
        'checksum',
        'bit_array'
    )

    def __init__(self, raw: bytes):
        # Set all values to None initially
        [setattr(self, name, None) for name in self.__slots__]

        # Store raw data
        self.raw = raw

        # An AIS NMEA message consists of seven, comma separated parts
        values = raw.split(b",")

        # Only encapsulated messages are currently supported
        if values[0][0] != 0x21:
            return

        if len(values) != 7:
            raise InvalidNMEAMessageException("A NMEA message needs to have exactly 7 comma separated entries.")

        # Unpack NMEA message parts
        (
            head,
            count,
            index,
            seq_id,
            channel,
            data,
            checksum
        ) = values

        # The talker is identified by the next 2 characters
        self.talker = head[1:3].decode('ascii')

        # The type of message is then identified by the next 3 characters
        self.msg_type = head[3:].decode('ascii')

        # Store other important parts
        self.count: int = int(count)
        self.index: int = int(index)
        self.seq_id = seq_id
        self.channel = channel
        self.data = data
        self.checksum = int(checksum[2:], 16)

        # Verify if the checksum is correct
        if not self.is_valid:
            raise InvalidChecksumException(
                f"Invalid Checksum. Expected {self.checksum}, got {compute_checksum(self.data)}.")

        # Finally decode bytes into bits
        self.bit_array = decode_into_bit_array(self.data)
        self.ais_id = get_int(self.bit_array, 0, 6)

    def __str__(self):
        return str(self.raw)

    def __dict__(self):
        def serializable(o):
            if isinstance(o, bytes):
                return o.decode('utf-8')
            elif isinstance(o, bitarray):
                return o.to01()

            return o

        return dict(
            [
                (slot, serializable(getattr(self, slot)))
                for slot in self.__slots__
            ]
        )

    def __eq__(self, other):
        return all([getattr(self, attr) == getattr(other, attr) for attr in self.__slots__])

    @classmethod
    def from_string(cls, nmea_str: str):
        return cls(str.encode(nmea_str))

    @classmethod
    def from_bytes(cls, nmea_byte_str: bytes):
        return cls(nmea_byte_str)

    @classmethod
    def assemble_from_iterable(cls, messages: Sequence):
        """
        Assemble a multiline message from a sequence of NMEA messages.
        :param messages: Sequence of NMEA messages
        :return: Single message
        """
        raw = b''
        data = b''
        bit_array = bitarray()

        for msg in messages:
            raw += msg.raw
            data += msg.data
            bit_array += msg.bit_array

        messages[0].raw = raw
        messages[0].data = data
        messages[0].bit_array = bit_array
        return messages[0]

    @property
    def is_valid(self) -> bool:
        return self.checksum == compute_checksum(self.raw)

    @property
    def is_single(self) -> bool:
        return not self.seq_id and self.index == self.count == 1

    @property
    def is_multi(self) -> bool:
        return not self.is_single

    @property
    def fragment_count(self) -> int:
        return self.count

    def decode(self, silent: bool = True):
        """
        Decode the message content.

        @param silent: Boolean. If set to true errors are ignored and None is returned instead
        """
        try:
            return AISMessage(self)
        except Exception as e:
            if silent:
                return None

            raise e


class AISMessage(object):
    """
    Initializes a generic AIS message.
    """

    def __init__(self, nmea_message: NMEAMessage):
        self.nmea: NMEAMessage = nmea_message
        self.msg_type: AISType = AISType(nmea_message.ais_id)
        self.content: typing.Dict = decode(self.nmea)

    def __getitem__(self, item: str):
        return self.content[item]

    def __str__(self):
        return str(self.content)

    def __dict__(self):
        return {
            'nmea': self.nmea.__dict__(),
            'decoded': self.content
        }

    def to_json(self):
        return json.dumps(
            self.__dict__(),
            indent=4
        )

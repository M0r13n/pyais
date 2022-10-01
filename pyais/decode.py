import typing

from pyais.exceptions import (
    TooManyMessagesException,
    MissingMultipartMessageException,
    InvalidNMEAChecksum
)
from pyais.messages import NMEAMessage, ANY_MESSAGE


def _assemble_messages(*args: bytes, error_if_checksum_invalid: bool = False) -> NMEAMessage:
    # Convert bytes into NMEAMessage and remember fragment_count and fragment_numbers
    temp: typing.List[NMEAMessage] = []
    frags: typing.List[int] = []
    frag_cnt: int = 1
    for msg in args:
        nmea = NMEAMessage(msg)
        if error_if_checksum_invalid and not nmea.is_valid:
            raise InvalidNMEAChecksum(f'The checksum is invalid for message "{nmea.raw!r}"')

        temp.append(nmea)
        frags.append(nmea.frag_num)
        frag_cnt = nmea.fragment_count

    # Make sure provided parts assemble a single (multiline message)
    if len(args) > frag_cnt:
        raise TooManyMessagesException(f"Got {len(args)} messages, but fragment count is {frag_cnt}")

    # Make sure all parts of a multipart message are provided
    diff = [x for x in range(1, frag_cnt + 1) if x not in frags]
    if len(diff):
        raise MissingMultipartMessageException(f"Missing fragment numbers: {diff}")

    # Assemble temporary messages
    final = NMEAMessage.assemble_from_iterable(temp)
    return final


def decode(*args: typing.Union[str, bytes], error_if_checksum_invalid: bool = False) -> ANY_MESSAGE:
    parts = tuple(msg.encode('utf-8') if isinstance(msg, str) else msg for msg in args)
    nmea = _assemble_messages(*parts, error_if_checksum_invalid=error_if_checksum_invalid)
    return nmea.decode()

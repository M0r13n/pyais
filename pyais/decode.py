import typing

from pyais.exceptions import UnknownMessageException, TooManyMessagesException, MissingMultipartMessageException
from pyais.messages import MessageType1, MessageType2, MessageType3, MessageType4, MessageType5, MessageType6, \
    MessageType7, MessageType8, MessageType9, MessageType10, MessageType11, MessageType12, MessageType13, MessageType14, \
    MessageType15, MessageType16, MessageType17, MessageType18, MessageType19, MessageType20, MessageType21, \
    MessageType22, MessageType23, MessageType24, MessageType25, MessageType26, MessageType27, NMEAMessage

DECODE_MSG = {
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


def _assemble_messages(*args: bytes) -> NMEAMessage:
    # Convert bytes into NMEAMessage and remember fragment_count and fragment_numbers
    temp: typing.List[NMEAMessage] = []
    frags: typing.List[int] = []
    frag_cnt: int = 1
    for msg in args:
        nmea = NMEAMessage(msg)
        temp.append(nmea)
        frags.append(nmea.fragment_number)
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


def decode(*args: typing.Union[str, bytes]):
    parts = tuple(msg.encode('utf-8') if isinstance(msg, str) else msg for msg in args)
    nmea = _assemble_messages(*parts)
    try:
        return DECODE_MSG[nmea.ais_id].from_bitarray(nmea.bit_array)
    except IndexError as e:
        raise UnknownMessageException(f"The message {nmea} is not supported!") from e

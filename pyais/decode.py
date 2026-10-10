import typing

from pyais.exceptions import (
    TooManyMessagesException,
    MissingMultipartMessageException,
    InvalidNMEAChecksum
)
from pyais.messages import NMEASentence, NMEASentenceFactory, AISSentence, ANY_MESSAGE


def _assemble_messages(
    *args: bytes,
    error_if_checksum_invalid: bool = False,
) -> AISSentence:
    # Convert bytes into NMEAMessage and remember fragment_count and fragment_numbers
    temp: typing.List[AISSentence] = []
    frags: typing.List[int] = []
    frag_cnt: int = 1
    for msg in args:

        sentence = NMEASentenceFactory.produce(msg)

        if error_if_checksum_invalid and not sentence.is_valid:
            raise InvalidNMEAChecksum(f'The checksum is invalid for message "{sentence.raw!r}"')

        # Ignore any other type of message
        if sentence.TYPE == AISSentence.TYPE:
            sentence = typing.cast(AISSentence, sentence)
            temp.append(sentence)
            frags.append(sentence.frag_num)
            frag_cnt = sentence.fragment_count

    if len(frags) == 0:
        raise MissingMultipartMessageException('no AIS message to decode')

    # Make sure provided parts assemble a single (multiline message)
    if len(temp) > frag_cnt:
        raise TooManyMessagesException(f"Got {len(temp)} messages, but fragment count is {frag_cnt}")

    # Make sure all parts of a multipart message are provided
    diff = [x for x in range(1, frag_cnt + 1) if x not in frags]
    if len(diff):
        raise MissingMultipartMessageException(f"Missing fragment numbers: {diff}")

    # Assemble temporary messages
    final = AISSentence.assemble_from_iterable(temp)
    return final


def decode(*args: typing.Union[str, bytes], error_if_checksum_invalid: bool = False) -> ANY_MESSAGE:
    """
    Decodes an AIS message.
    For multi part messages all parts are required.

    :param args: all parts of the AIS message to decode.
    :param error_if_checksum_invalid: Raise an error if the checksum of
                                      any part is invalid. (Default=False)
    :returns: The decoded message
    :raises UnknownMessageException: Only a small subset of all NMEA messages is supported.
    :raises InvalidNMEAChecksum: raised when the NMEA checksum is invalid.
    :raises MissingMultipartMessageException: raised when there are missing parts for multi part messages.
    :raises TooManyMessagesException: raised when more than one message is provided.
                                      NOTE: multiple parts for the SAME message are allowed.

    NOTE:
        This library is often used for data analysis. This means that a researcher
        analyzes large amounts of AIS messages. Such message streams might contain
        thousands of messages with invalid checksums. Its up to the researcher to
        decide whether he/she wants to include such messages in his/her analysis.
        Raising an exception for every invalid checksum would both cause a
        performance degradation because handling of such exceptions is expensive
        and make it impossible to include such messages into the analysis.

        If you want to raise an error if the checksum of a message is invalid set
        the key word argument `error_if_checksum_invalid` to True.
    """
    parts = tuple(msg.encode('utf-8') if isinstance(msg, str) else msg for msg in args)
    nmea = _assemble_messages(*parts, error_if_checksum_invalid=error_if_checksum_invalid)
    return nmea.decode()


def decode_nmea_and_ais(
        *args: typing.Union[str, bytes], error_if_checksum_invalid: bool = False
) -> typing.Tuple[NMEASentence, ANY_MESSAGE]:
    """Behaves just like `decode`.
    But it returns both: the NMEASentence and the AIS payload.
    Useful, if the NMEA sentence layer is of interest."""
    parts = tuple(msg.encode('utf-8') if isinstance(msg, str) else msg for msg in args)
    nmea = _assemble_messages(*parts, error_if_checksum_invalid=error_if_checksum_invalid)
    return nmea, nmea.decode()


def decode_nmea_line(line: bytes) -> NMEASentence:
    """
    Decode a single NMEA line/sentence.
    :param line: the NMEA line/sentence to decode
    :return: The decoded NMEA object.
             Note that AIS messages are encapsulated inside the NMEA protocol.
             A protocol inside a protocol sort of.
    """
    sentence = NMEASentenceFactory.produce(line)
    return sentence

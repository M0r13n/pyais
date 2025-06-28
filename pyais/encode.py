import math
import typing

from pyais.messages import Payload, MSG_CLASS
from pyais.util import chunks, compute_checksum

# Types
DATA_DICT = typing.Dict[str, typing.Union[str, int, float, bytes, bool]]
AIS_SENTENCES = typing.List[str]


def get_ais_type(data: DATA_DICT) -> int:
    """
    Get the message type from a set of keyword arguments. The first occurence of either
    `type` or `msg_type` will be used.
    """
    keys = ['type', 'msg_type']
    length = len(keys) - 1
    for i, key in enumerate(keys):
        try:
            ais_type = data[key]
            return int(ais_type)
        except (KeyError, ValueError) as err:
            if i == length:
                raise ValueError("Missing or invalid AIS type. Must be a number.") from err
    raise ValueError("Missing type")


def data_to_payload(ais_type: int, data: DATA_DICT) -> Payload:
    try:
        return MSG_CLASS[ais_type].create(**data)
    except KeyError as err:
        raise ValueError(f"AIS message type {ais_type} is not supported") from err


def ais_to_nmea_0183(
        payload: str,
        ais_talker_id: str,
        radio_channel: str,
        fill_bits: int,
        seq_id: typing.Optional[typing.Union[str, int]] = None
) -> AIS_SENTENCES:
    """
    Splits the AIS payload into sentences, ASCII encodes the payload, creates
    and sends the relevant NMEA 0183 sentences. Messages have a maximum length
    of 82 characters, including the $ or ! starting character and the ending <LF>.

    HINT:
        This method takes care of splitting large payloads (larger than 60 characters)
        into multiple sentences. With a total of 80 maximum chars excluding end of line
        per sentence, and 20 chars head + tail in the nmea 0183 carrier protocol, 60
        chars remain for the actual payload.

    @param payload:         Armored AIs payload.
    @param ais_talker_id:   AIS talker ID (AIVDO or AIVDM)
    @param radio_channel:   Radio channel (either A or B)
    @param fill_bits:       The number of fill bits requires to pad the data payload to a 6 bit boundary.
    @param seq_id:          Optional sequence ID
    @return:                A list of relevant AIS sentences.
    """
    messages = []
    max_len = 60
    frag_cnt = math.ceil(len(payload) / max_len)

    if seq_id is None:
        seq_id = '0' if frag_cnt > 1 else ''
    elif frag_cnt == 1:
        seq_id = ''

    if len(ais_talker_id) != 5:
        raise ValueError("AIS talker is must have exactly 6 characters. E.g. AIVDO")

    if len(radio_channel) != 1:
        raise ValueError("Radio channel must be a single character")

    for frag_num, chunk in enumerate(chunks(payload, max_len), start=1):
        tpl = "!{},{},{},{},{},{},{}*{:02X}"
        fill_bits_frag = fill_bits if frag_num == frag_cnt else 0  # Make sure we set fill bits only for last fragment
        dummy_message = tpl.format(ais_talker_id, frag_cnt, frag_num, seq_id, radio_channel, chunk, fill_bits_frag, 0)
        checksum = compute_checksum(dummy_message)
        msg = tpl.format(ais_talker_id, frag_cnt, frag_num, seq_id, radio_channel, chunk, fill_bits_frag, checksum)
        messages.append(msg)

    return messages


def encode_dict(
    data: DATA_DICT,
    talker_id: str = "AIVDO",
    radio_channel: str = "A",
    seq_id: typing.Optional[typing.Union[str, int]] = None
) -> AIS_SENTENCES:
    """
    Takes a dictionary of data and some NMEA specific kwargs and returns the NMEA 0183 encoded AIS sentence.

    Notes:
        - the data dict should also contain the AIS message type (1-27) under the `type` key.
        - different messages take different keywords. Refer to the payload classes above to get a glimpse
          on what fields each AIS message can take.

    @param data: The AIS data as a dictionary.
    @param talker_id: AIS packets have the introducer "AIVDM" or "AIVDO";
                      AIVDM packets are reports from other ships and AIVDO packets are reports from your own ship.
    @param radio_channel: The radio channel. Can be either 'A' (default) or 'B'.
    @param seq_id: Optional sequence ID
    @return: NMEA 0183 encoded AIS sentences.

    """
    if talker_id not in ("AIVDM", "AIVDO"):
        raise ValueError("talker_id must be any of ['AIVDM', 'AIVDO']")

    if radio_channel not in ('A', 'B'):
        raise ValueError("radio_channel must be any of ['A', 'B']")

    ais_type = get_ais_type(data)
    payload = data_to_payload(ais_type, data)
    armored_payload, fill_bits = payload.encode()
    return ais_to_nmea_0183(armored_payload, talker_id, radio_channel, fill_bits, seq_id=seq_id)


def encode_msg(
        msg: Payload,
        talker_id: str = "AIVDO",
        radio_channel: str = "A",
        seq_id: typing.Optional[typing.Union[str, int]] = None
) -> AIS_SENTENCES:
    if talker_id not in ("AIVDM", "AIVDO"):
        raise ValueError("talker_id must be any of ['AIVDM', 'AIVDO']")

    if radio_channel not in ('A', 'B'):
        raise ValueError("radio_channel must be any of ['A', 'B']")

    armored_payload, fill_bits = msg.encode()
    return ais_to_nmea_0183(armored_payload, talker_id, radio_channel, fill_bits, seq_id=seq_id)

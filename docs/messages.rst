##################
Message interface
##################

NMEA messages
----------------

The `NMEAMessage` is the first level of abstraction during parsing/decoding.
Every message that is decoded, is transformed into a `NMEAMessage`.


Every instance of `NMEAMessage` has a fixed set of attributes::

    msg = NMEAMessage(b"!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B")

    msg.ais_id                  # => AIS message type as :int:
    msg.raw                     # => Raw, decoded message as :byte:
    msg.talker                  # => Talker ID as :str:
    msg.type                    # => Message type (VDM, VDO, etc.) :str:
    msg.message_fragments       # => Number of fragments (some messages need more than one, maximum generally is 9) as :int:
    msg.fragment_number         # => Sentence number (1 unless it is a multi-sentence message) as :int:
    msg.message_id              # => Optional (can be None) sequential message ID (for multi-sentence messages) as :int:
    msg.channel                 # => The AIS channel (A or B) as :str:
    msg.payload                 # => he encoded AIS data, using AIS-ASCII6 as :bytes:
    msg.fill_bits               # => unused bits at end of data (0-5) as :int:
    msg.checksum                # => NMEA CRC1 checksum :int:
    msg.bit_array               # => Payload as :bitarray:


Fields are also subscribable::

    msg = NMEAMessage(b"!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B")

    msg['ais_id'] ==  msg.ais_id
    msg['raw'] == msg.raw
    # etc. ..

Every message can be transformed into a dictionary::

    msg = NMEAMessage(b"!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B")

    msg.asdict() == {'ais_id': 1,
     'bit_array': '000001000101011101110010000010000011100000000000000000000000010111001111111001000111101110011011001110101111001010110111000111010000000001001010000000011100000011100011',
     'channel': 'A',
     'checksum': 27,
     'fill_bits': 0,
     'fragment_number': 1,
     'message_fragments': 1,
     'message_id': None,
     'payload': '15Mj23P000G?q7fK>g:o7@1:0L3S',
     'raw': '!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B',
     'talker': 'AI',
     'type': 'VDM'}

Multiline messages can be created as follows::

      msg_1_part_0 = b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07'
        msg_1_part_1 = b'!AIVDM,2,2,1,A,F@V@00000000000,2*35'

        assert NMEAMessage.assemble_from_iterable(
            messages=[
                NMEAMessage(msg_1_part_0),
                NMEAMessage(msg_1_part_1)
            ]
        ).decode()

In order to decode a NMEA message, it is first transformed into a `AISMessage`. See the documentation below for details::

    msg = NMEAMessage(b"!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B")
    ais = msg.decode()

Sometimes, you might want quick access to a serialized JSON representation of a `NMEAMessage`::

    NMEAMessage(b"!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B").decode().to_json()



AISMessage
----------------


Every `AISMessage` message has the following interface:


Get the parent NMEA message::

    ais = AISMessage()
    ais.nmea

Get message type::

    ais = AISMessage()
    ais.msg_type

Get content::

    ais = AISMessage()
    ais.content

`AISMessage.content` is a dictionary that holds all decoded fields. You can get all available fields
for every message through the `fields` attribute. All available fields are documented here: https://gpsd.gitlab.io/gpsd/AIVDM.html

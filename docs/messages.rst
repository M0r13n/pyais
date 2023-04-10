##################
Message interface
##################

`pyais` supports all message types. But it can currently not decode message specific payloads. This should be done by the user.

This applies to messages of type 6, 8, 25, and 26. These messages have in common, that they contain unspecified binary payload.

- Message type 6: data field with up to 920 bits of binary payload
- Message type 8: data field with up to 952 bits of binary payload
- Message type 26: data field with up to 128 bits of binary payload
- Message type 27: data fiield with up to 1004 bits of binary payload

The decoding of the binary payload is message dependent and varies between different systems.
If you want to decode the binary payload of message type 6, you firstly would have to look at the
dac (Designated Area Code) and the fid (Functional ID). Dependening of their values, you would know, how to interpret the payload.

There are a lot of different application-specific messages, which are more or less standardized.
Therefore ``pyais`` does not even try to decode the payload. Instead, you can access the raw payload ::


    # Parse of message of type 8
    msg = NMEAMessage(b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47").decode()

    payload = msg.data

The data is stored as raw bytes to make it easy to post process such binary payload.
The lib also includes some handy helper functions to transform bytes to bits and vice versa::

    from pyais.utils import bits2bytes, bytes2bits

    bits2bytes('00100110')      #=> b'&'
    bytes2bits(b'&').to01()     #=> '00100110'

NMEA messages
----------------

The `NMEASentence` is the first level of abstraction during parsing/decoding.

Every instance of `NMEASentence` has a fixed set of attributes::

    msg = NMEASentence(b"!AIVDM,1,1,,A,15Mj23P000G?q7fK>g:o7@1:0L3S,0*1B")

    msg.raw                    # => Raw decoded message as :byte:
    msg.delimiter              # => Start delimiter. Normally $ or ?
    msg.data_fields            # => NMEA payload. Interpretation varies depending on the NMEA sentence type
    msg.talker_id              # => two letter talker ID
    msg.type                   # => three-letter type code.
    msg.checksum               # => NMEA sentence checksum. 8-bit XOR of all characters
    msg.is_valid               # => Check if checksum valid
    msg.wrapper_msg            # => Optional encapsulating message

This class is not meant to be instantiated directly. Instead, an inheriting class 
should subclass from it. Such a child class then defines the sentence specific logic.

**pyais** currently supports two NMEA sentence types:

- `GatehouseSentence`: wrapper messages that hold additional meta data.
- `AISSentence`: AIS messages


Gatehouse wrappers
-------------------

Some AIS messages have so-called Gatehouse wrappers. These encapsulating messages contain extra information, such as time and checksums. Some readers also process these. See some more documentation [here](https://www.iala-aism.org/wiki/iwrap/index.php/GH_AIS_Message_Format).

As an example, see the following, which is followed by a regular `!AIVDM` message

```
$PGHP,1,2020,12,31,23,59,58,239,0,0,0,1,2C*5B
```

Such messages are parsed by **pyais** only when using any of the classes from **pyais.stream**.
e.g. `FileReaderStream` or `TCPStream`.

Such additional information can then be accessed by the `.wrapper_msg` of every `NMEASentence`. This attribute is `None` by default.


Communication State
--------------------

The `ITU`_ documentation provides details regarding the Time-division multiple access (TDMA) synchronization.

.. _ITU: https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.1371-1-200108-S!!PDF-E.pdf

Such details include information used by the slot allocation algorithm (either SOTDMA or ITDMA) including their synchronization state.

This information can be found in the last 19 data-bits of some messages.

The following messages have the SOTDMA communication state:

- Type 1
- Type 2
- Type 4
- Type 9
- Type 11
- Type 18

The following messages have the ITDMA communication state:

- Type 3
- Type 18

These messages have in common that they have the `.radio` attribute. This attribute holds the **raw value** of the last 19 data-bits.

Further details can be retrieved by using one of the following methods:

- `.is_sotdma()`: Returns True when using the SOTDMA algorithm
- `.is_itdma()`: Returns True when using the ITDMA algorithm
- `get_communication_state()`: information used by the slot allocation algorithm as a dictionary

Example::

    msg = '!AIVDM,1,1,,A,B69Gk3h071tpI02lT2ek?wg61P06,0*1F'
    decoded = decode(msg)

    print("The raw radio value is:", decoded.radio)
    print("Communication state is SOTMDA:", decoded.is_sotdma)
    print("Communication state is ITDMA:", decoded.is_itdma)

    pretty_json = functools.partial(json.dumps, indent=4)
    print("Communication state:", pretty_json(decoded.get_communication_state()))

All other messages do not contain any details about the communication state. Therefore, the methods mentioned above are not available for these messages.

Message classes
----------------

There are 27 different types of AIS messages. Each message has different attributes and is encoded/decoded
differently depending of the AIS standard. But, there are some things that all messages do have in common:

When decoding:
    - if the message payload has fewer bits than would be needed to decode every field,
      the remaining fields are set to `None`

When encoding:
    - you should use `MessageType1.create(mmsi=123, ...)` for every message, as it sets default values
      for missing attributes.
    - `MessageType1.create(...)` always needs **at least** the mmsi keyword
    - if you create the instance directly e.g. `MessageType1(mmsi=1, ...)`, you need to provide
      **every possible** attribute, otherwise a `TypeError` is raised

MessageType1
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 1
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `status`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `turn`
            * type: <class 'int'>
            * bit-width: 8
            * default: 0
        * `speed`
            * type: <class 'float'>
            * bit-width: 10
            * default: 0
        * `accuracy`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `lon`
            * type: <class 'float'>
            * bit-width: 28
            * default: 0
        * `lat`
            * type: <class 'float'>
            * bit-width: 27
            * default: 0
        * `course`
            * type: <class 'float'>
            * bit-width: 12
            * default: 0
        * `heading`
            * type: <class 'int'>
            * bit-width: 9
            * default: 0
        * `second`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `maneuver`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `spare`
            * type: <class 'int'>
            * bit-width: 3
            * default: 0
        * `raim`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `radio`
            * type: <class 'int'>
            * bit-width: 19
            * default: 0
MessageType2
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 1
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `status`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `turn`
            * type: <class 'int'>
            * bit-width: 8
            * default: 0
        * `speed`
            * type: <class 'float'>
            * bit-width: 10
            * default: 0
        * `accuracy`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `lon`
            * type: <class 'float'>
            * bit-width: 28
            * default: 0
        * `lat`
            * type: <class 'float'>
            * bit-width: 27
            * default: 0
        * `course`
            * type: <class 'float'>
            * bit-width: 12
            * default: 0
        * `heading`
            * type: <class 'int'>
            * bit-width: 9
            * default: 0
        * `second`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `maneuver`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `spare`
            * type: <class 'int'>
            * bit-width: 3
            * default: 0
        * `raim`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `radio`
            * type: <class 'int'>
            * bit-width: 19
            * default: 0
MessageType3
    AIS Vessel position report using ITDMA (Incremental Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 1
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `status`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `turn`
            * type: <class 'int'>
            * bit-width: 8
            * default: 0
        * `speed`
            * type: <class 'float'>
            * bit-width: 10
            * default: 0
        * `accuracy`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `lon`
            * type: <class 'float'>
            * bit-width: 28
            * default: 0
        * `lat`
            * type: <class 'float'>
            * bit-width: 27
            * default: 0
        * `course`
            * type: <class 'float'>
            * bit-width: 12
            * default: 0
        * `heading`
            * type: <class 'int'>
            * bit-width: 9
            * default: 0
        * `second`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `maneuver`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `spare`
            * type: <class 'int'>
            * bit-width: 3
            * default: 0
        * `raim`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `radio`
            * type: <class 'int'>
            * bit-width: 19
            * default: 0
MessageType4
    AIS Vessel position report using SOTDMA (Self-Organizing Time Division Multiple Access)
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_4_base_station_report


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 4
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `year`
            * type: <class 'int'>
            * bit-width: 14
            * default: 1970
        * `month`
            * type: <class 'int'>
            * bit-width: 4
            * default: 1
        * `day`
            * type: <class 'int'>
            * bit-width: 5
            * default: 1
        * `hour`
            * type: <class 'int'>
            * bit-width: 5
            * default: 0
        * `minute`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `second`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `accuracy`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `lon`
            * type: <class 'float'>
            * bit-width: 28
            * default: 0
        * `lat`
            * type: <class 'float'>
            * bit-width: 27
            * default: 0
        * `epfd`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `spare`
            * type: <class 'int'>
            * bit-width: 10
            * default: 0
        * `raim`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `radio`
            * type: <class 'int'>
            * bit-width: 19
            * default: 0
MessageType5
    Static and Voyage Related Data
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_5_static_and_voyage_related_data


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 5
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `ais_version`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `imo`
            * type: <class 'int'>
            * bit-width: 30
            * default: 0
        * `callsign`
            * type: <class 'str'>
            * bit-width: 42
            * default:
        * `shipname`
            * type: <class 'str'>
            * bit-width: 120
            * default:
        * `ship_type`
            * type: <class 'int'>
            * bit-width: 8
            * default: 0
        * `to_bow`
            * type: <class 'int'>
            * bit-width: 9
            * default: 0
        * `to_stern`
            * type: <class 'int'>
            * bit-width: 9
            * default: 0
        * `to_port`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `to_starboard`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `epfd`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `month`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `day`
            * type: <class 'int'>
            * bit-width: 5
            * default: 0
        * `hour`
            * type: <class 'int'>
            * bit-width: 5
            * default: 0
        * `minute`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `draught`
            * type: <class 'float'>
            * bit-width: 8
            * default: 0
        * `destination`
            * type: <class 'str'>
            * bit-width: 120
            * default:
        * `dte`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `spare`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
MessageType6
    Binary Addresses Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_4_base_station_report


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 6
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `seqno`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `dest_mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `retransmit`
            * type: <class 'bool'>
            * bit-width: 1
            * default: False
        * `spare`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `dac`
            * type: <class 'int'>
            * bit-width: 10
            * default: 0
        * `fid`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `data`
            * type: <class 'int'>
            * bit-width: 920
            * default: 0
MessageType7
    Binary Acknowledge
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_7_binary_acknowledge


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 7
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `spare`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi1`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: 0
        * `mmsiseq1`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 2
            * default: 0
        * `mmsi2`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: 0
        * `mmsiseq2`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 2
            * default: 0
        * `mmsi3`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: 0
        * `mmsiseq3`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 2
            * default: 0
        * `mmsi4`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: 0
        * `mmsiseq4`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 2
            * default: 0
MessageType8
    Binary Acknowledge
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_8_binary_broadcast_message


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 8
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `spare`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `dac`
            * type: <class 'int'>
            * bit-width: 10
            * default: 0
        * `fid`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `data`
            * type: <class 'int'>
            * bit-width: 952
            * default: 0
MessageType9
    Standard SAR Aircraft Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_9_standard_sar_aircraft_position_report


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 9
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `alt`
            * type: <class 'int'>
            * bit-width: 12
            * default: 0
        * `speed`
            * type: <class 'int'>
            * bit-width: 10
            * default: 0
        * `accuracy`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `lon`
            * type: <class 'float'>
            * bit-width: 28
            * default: 0
        * `lat`
            * type: <class 'float'>
            * bit-width: 27
            * default: 0
        * `course`
            * type: <class 'float'>
            * bit-width: 12
            * default: 0
        * `second`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `reserved`
            * type: <class 'int'>
            * bit-width: 8
            * default: 0
        * `dte`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `spare`
            * type: <class 'int'>
            * bit-width: 3
            * default: 0
        * `assigned`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `raim`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `radio`
            * type: <class 'int'>
            * bit-width: 20
            * default: 0
MessageType10
    UTC/Date Inquiry
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_10_utc_date_inquiry


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 10
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `spare_1`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `dest_mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `spare_2`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
MessageType11
    UTC/Date Response
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_11_utc_date_response


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 4
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `year`
            * type: <class 'int'>
            * bit-width: 14
            * default: 1970
        * `month`
            * type: <class 'int'>
            * bit-width: 4
            * default: 1
        * `day`
            * type: <class 'int'>
            * bit-width: 5
            * default: 1
        * `hour`
            * type: <class 'int'>
            * bit-width: 5
            * default: 0
        * `minute`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `second`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `accuracy`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `lon`
            * type: <class 'float'>
            * bit-width: 28
            * default: 0
        * `lat`
            * type: <class 'float'>
            * bit-width: 27
            * default: 0
        * `epfd`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `spare`
            * type: <class 'int'>
            * bit-width: 10
            * default: 0
        * `raim`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `radio`
            * type: <class 'int'>
            * bit-width: 19
            * default: 0
MessageType12
    Addressed Safety-Related Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_12_addressed_safety_related_message


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 12
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `seqno`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `dest_mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `retransmit`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `spare`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `text`
            * type: <class 'str'>
            * bit-width: 936
            * default:
MessageType13
    Identical to type 7


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 7
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `spare`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi1`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: 0
        * `mmsiseq1`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 2
            * default: 0
        * `mmsi2`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: 0
        * `mmsiseq2`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 2
            * default: 0
        * `mmsi3`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: 0
        * `mmsiseq3`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 2
            * default: 0
        * `mmsi4`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: 0
        * `mmsiseq4`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 2
            * default: 0
MessageType14
    Safety-Related Broadcast Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_14_safety_related_broadcast_message


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 14
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `spare`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `text`
            * type: <class 'str'>
            * bit-width: 968
            * default:
MessageType15
    Interrogation
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_15_interrogation


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 15
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `spare_1`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi1`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: 0
        * `type1_1`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `offset1_1`
            * type: <class 'int'>
            * bit-width: 12
            * default: 0
        * `spare_2`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `type1_2`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `offset1_2`
            * type: <class 'int'>
            * bit-width: 12
            * default: 0
        * `spare_3`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi2`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: 0
        * `type2_1`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `offset2_1`
            * type: <class 'int'>
            * bit-width: 12
            * default: 0
        * `spare_4`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
MessageType16
    Assignment Mode Command
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_16_assignment_mode_command


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 16
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `spare`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi1`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: 0
        * `offset1`
            * type: <class 'int'>
            * bit-width: 12
            * default: 0
        * `increment1`
            * type: <class 'int'>
            * bit-width: 10
            * default: 0
        * `mmsi2`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: 0
        * `offset2`
            * type: <class 'int'>
            * bit-width: 12
            * default: 0
        * `increment2`
            * type: <class 'int'>
            * bit-width: 10
            * default: 0
MessageType17
    DGNSS Broadcast Binary Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_17_dgnss_broadcast_binary_message


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 17
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `spare_1`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `lon`
            * type: <class 'float'>
            * bit-width: 18
            * default: 0
        * `lat`
            * type: <class 'float'>
            * bit-width: 17
            * default: 0
        * `spare_2`
            * type: <class 'int'>
            * bit-width: 5
            * default: 0
        * `data`
            * type: <class 'int'>
            * bit-width: 736
            * default: 0
MessageType18
    Standard Class B CS Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_18_standard_class_b_cs_position_report


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 18
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `reserved`
            * type: <class 'int'>
            * bit-width: 8
            * default: 0
        * `speed`
            * type: <class 'float'>
            * bit-width: 10
            * default: 0
        * `accuracy`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `lon`
            * type: <class 'float'>
            * bit-width: 28
            * default: 0
        * `lat`
            * type: <class 'float'>
            * bit-width: 27
            * default: 0
        * `course`
            * type: <class 'float'>
            * bit-width: 12
            * default: 0
        * `heading`
            * type: <class 'int'>
            * bit-width: 9
            * default: 0
        * `second`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `reserved_2`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `cs`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `display`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `dsc`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `band`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `msg22`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `assigned`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `raim`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `radio`
            * type: <class 'int'>
            * bit-width: 20
            * default: 0
MessageType19
    Extended Class B CS Position Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_19_extended_class_b_cs_position_report


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 19
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `reserved`
            * type: <class 'int'>
            * bit-width: 8
            * default: 0
        * `speed`
            * type: <class 'float'>
            * bit-width: 10
            * default: 0
        * `accuracy`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `lon`
            * type: <class 'float'>
            * bit-width: 28
            * default: 0
        * `lat`
            * type: <class 'float'>
            * bit-width: 27
            * default: 0
        * `course`
            * type: <class 'float'>
            * bit-width: 12
            * default: 0
        * `heading`
            * type: <class 'int'>
            * bit-width: 9
            * default: 0
        * `second`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `regional`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `shipname`
            * type: <class 'str'>
            * bit-width: 120
            * default:
        * `ship_type`
            * type: <class 'int'>
            * bit-width: 8
            * default: 0
        * `to_bow`
            * type: <class 'int'>
            * bit-width: 9
            * default: 0
        * `to_stern`
            * type: <class 'int'>
            * bit-width: 9
            * default: 0
        * `to_port`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `to_starboard`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `epfd`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `raim`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `dte`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `assigned`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `spare`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
MessageType20
    Data Link Management Message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_20_data_link_management_message


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 20
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `spare`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `offset1`
            * type: <class 'int'>
            * bit-width: 12
            * default: 0
        * `number1`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `timeout1`
            * type: <class 'int'>
            * bit-width: 3
            * default: 0
        * `increment1`
            * type: <class 'int'>
            * bit-width: 11
            * default: 0
        * `offset2`
            * type: <class 'int'>
            * bit-width: 12
            * default: 0
        * `number2`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `timeout2`
            * type: <class 'int'>
            * bit-width: 3
            * default: 0
        * `increment2`
            * type: <class 'int'>
            * bit-width: 11
            * default: 0
        * `offset3`
            * type: <class 'int'>
            * bit-width: 12
            * default: 0
        * `number3`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `timeout3`
            * type: <class 'int'>
            * bit-width: 3
            * default: 0
        * `increment3`
            * type: <class 'int'>
            * bit-width: 11
            * default: 0
        * `offset4`
            * type: <class 'int'>
            * bit-width: 12
            * default: 0
        * `number4`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `timeout4`
            * type: <class 'int'>
            * bit-width: 3
            * default: 0
        * `increment4`
            * type: <class 'int'>
            * bit-width: 11
            * default: 0
MessageType21
    Aid-to-Navigation Report
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_21_aid_to_navigation_report


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 21
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `aid_type`
            * type: <class 'int'>
            * bit-width: 5
            * default: 0
        * `name`
            * type: <class 'str'>
            * bit-width: 120
            * default:
        * `accuracy`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `lon`
            * type: <class 'float'>
            * bit-width: 28
            * default: 0
        * `lat`
            * type: <class 'float'>
            * bit-width: 27
            * default: 0
        * `to_bow`
            * type: <class 'int'>
            * bit-width: 9
            * default: 0
        * `to_stern`
            * type: <class 'int'>
            * bit-width: 9
            * default: 0
        * `to_port`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `to_starboard`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `epfd`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `second`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `off_position`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `regional`
            * type: <class 'int'>
            * bit-width: 8
            * default: 0
        * `raim`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `virtual_aid`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `assigned`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `spare`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `name_ext`
            * type: <class 'str'>
            * bit-width: 88
            * default:
MessageType23
    Group Assignment Command
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_23_group_assignment_command


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 23
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `spare_1`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `ne_lon`
            * type: <class 'int'>
            * bit-width: 18
            * default: 0
        * `ne_lat`
            * type: <class 'int'>
            * bit-width: 17
            * default: 0
        * `sw_lon`
            * type: <class 'int'>
            * bit-width: 18
            * default: 0
        * `sw_lat`
            * type: <class 'int'>
            * bit-width: 17
            * default: 0
        * `station_type`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `ship_type`
            * type: <class 'int'>
            * bit-width: 8
            * default: 0
        * `spare_2`
            * type: <class 'int'>
            * bit-width: 22
            * default: 0
        * `txrx`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `interval`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `quiet`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `spare_3`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
MessageType27
    Long Range AIS Broadcast message
    Src: https://gpsd.gitlab.io/gpsd/AIVDM.html#_type_27_long_range_ais_broadcast_message


    Attributes:
        * `msg_type`
            * type: <class 'int'>
            * bit-width: 6
            * default: 27
        * `repeat`
            * type: <class 'int'>
            * bit-width: 2
            * default: 0
        * `mmsi`
            * type: (<class 'int'>, <class 'str'>)
            * bit-width: 30
            * default: None
        * `accuracy`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `raim`
            * type: <class 'bool'>
            * bit-width: 1
            * default: 0
        * `status`
            * type: <class 'int'>
            * bit-width: 4
            * default: 0
        * `lon`
            * type: <class 'float'>
            * bit-width: 18
            * default: 0
        * `lat`
            * type: <class 'float'>
            * bit-width: 17
            * default: 0
        * `speed`
            * type: <class 'int'>
            * bit-width: 6
            * default: 0
        * `course`
            * type: <class 'int'>
            * bit-width: 9
            * default: 0
        * `gnss`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0
        * `spare`
            * type: <class 'int'>
            * bit-width: 1
            * default: 0


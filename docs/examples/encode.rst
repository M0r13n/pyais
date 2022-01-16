#############################
Encode AIS messages
#############################

It is also possible to encode messages using pyais.
Currently, this library supports creating NMEA formatted AIS type messages from type 1 to type 10. Support for other types
is planned.

Examples
----------

Create a type 1 message through a dict::

    from pyais import encode_dict

    # Every message needs at least a MMSI and a message-type (1-27)
    data = {'mmsi': 12345, 'type': 1}

    # Because larger payloads may need to split over several fragment sentences
    # `encode_dict` always returns a list of parts (even if the message has a single part)
    encoded = encode_dict(data)

You can also create the message payload using it's class::

    from pyais import encode_payload
    from pyais.encode import MessageType1

    # Each message type has it's own message class that can be imported from `pyais.encode`
    payload = MessageType1.create(mmsi=123456)
    encoded = encode_payload(payload)

    print(encoded)

Create a multi-part Binary Addressed message (type 6) with ::

    from pyais import encode_payload
    from pyais.encode import MessageType6

    payload = MessageType6.create(mmsi=123456, dest_mmsi=13374269, data=0xffff)
    encoded = encode_payload(payload)

    print(encoded)

**Note**: Message type 6 is an addressed point-to-point message with unspecified binary payload. The interpretation of
the binary payload is application specific and is controlled by the `dac` and the `fid` fields. The data needs to be an
integer or bytes object::

    # Both statements are equivalent
    x = MessageType6.create(mmsi=123456, dest_mmsi=13374269, data=0xffff)
    y = MessageType6.create(mmsi=123456, dest_mmsi=13374269, data=b'\xff\xff')

    assert x.data == y.data

Create a type 5 message with `shipname`, `callsign` and `shiptype` fields::

    from pyais.encode import MessageType5, encode_payload

    payload = MessageType5.create(mmsi=123456, shipname="RMS Titanic", callsign="MGY", destination="NEW YORK")
    encoded = encode_payload(payload)

    for msg in encoded:
        print(msg)

Create a type 4 message with values for latitude and longitude. You can either pass ints, floats or strings to these
params - as long as they can be interpreted as an float::

    from pyais.encode import MessageType4, encode_payload

    payload = MessageType4.create(mmsi=123, lon=37.794285, lat="-122.464775")

    for msg in encode_payload(payload):
        print(msg)

By default, `pyais` creates AIVDO packets (reports from your own ship). But you can also send AIVDM messages (other ship)::

    from pyais.encode import MessageType5, encode_payload

    payload = MessageType5.create(mmsi=123456, shipname="RMS Titanic", callsign="MGY", destination="NEW YORK")
    encoded = encode_payload(payload, talker_id="AIVDM")
    print(encoded)
    # => ['!AIVDM,2,1,,A,5007R@000000lMT00018m>1@U@4pT<000000000000000000003QEp6ClRh00,2*14', '!AIVDM,2,2,,A,0000000000,2*24']

By default, `pyais` creates AIS Channel A messages, but can also create channel B messages::

    from pyais.encode import MessageType5, encode_payload

    payload = MessageType5.create(mmsi=123456, shipname="RMS Titanic", callsign="MGY", destination="NEW YORK")
    encoded = encode_payload(payload, radio_channel="B")
    print(encoded)
    # => ['!AIVDO,2,1,,B,5007R@000000lMT00018m>1@U@4pT<000000000000000000003QEp6ClRh00,2*15', '!AIVDO,2,2,,B,0000000000,2*25']

If you want to known which fields can be encoded for each message, you can take a look at the `pyais/encode.py` file.
Otherwise you can import the message class that you are interested in and inspect it::

    from pyais.encode import MessageType5

    fields = MessageType5.fields()

    for field in fields:
        print(field.name, field.metadata)

        # Will print:
        # msg_type {'width': 6, 'd_type': <class 'int'>, 'default': 5}
        # mmsi {'width': 30, 'd_type': <class 'int'>, 'default': None}
        # ...

You should always use the `MessageType5.create()` interface to create messages. This method has a couple of benefits:

1. it handles default values
    * you can use the `__init__` method of each message directly, but **then you need to pass ALL values that the message can encode**
2. it ignores all unknown fields
    * `MessageType5.create(mmsi=123, foo_bar=42)` will not cause any errors
    * `MessageType5(mmsi=123, foo_bar=42)` will yield in a `TypeError: __init__() got an unexpected keyword argument`
3. it is equally fast than using the native `__init__` method

Special messages
------------------

Some messages are special in that they encode differently depending on some value(s) of some field(s).
Types 22, 24, 25 and 26 are affected. As long as you use the `encode_dict`` interface,
this detail is invisible for you as a user: The library will automatically encode the correct
message based on the given values. Look at a [Type 25 message](https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a):

> If the 'addressed' flag is on, 30 bits of data at offset 40 are interpreted as a destination MMSI. Otherwise that field span becomes part of the message payload, with the first 16 bits used as an Application ID if the 'structured' flag is on.

It is easy to encode a dictionary of values with `encode_dict` ::

    data = {
        'addressed': 1,
        'data': b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xc0",
        'dest_mmsi': '134218384',
        'mmsi': '440006460',
        'repeat': 0,
        'structured': 0,
        'type': 25
    }

    encoded = encode_dict(data)
    assert encoded[0] == "!AIVDO,1,1,,A,I6SWo?8P00a0003wwwwwwwwwwww0,0*35"



Errors
----------------

- `TypeError: __init__() missing 1 required positional argument: 'mmsi'`:
    * this means that the message is missing a required parameter
    * pass `mmsi` (or whatever value is missing) to make it work
- `ValueError: could not convert string to float: 'Foo'`:
    * this might happen is you passed a value to a message that could not be converted to the expected data type
    * this could happen if you pass a non-float string to `lon`
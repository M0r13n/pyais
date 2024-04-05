##################
Examples
##################

There are many different examples that show the usage of pyais. Each example explains a different feature of pyais. All examples can be found in the examples folder: https://github.com/M0r13n/pyais/tree/master/examples

Communication State
--------------------

The following example shows how you can get the communication state
of a message. This works for message types 1, 2, 4, 9, 11 and 18.

These messages contain diagnostic information for the radio system.::

    from pyais import decode
    from pyais.messages import MessageType18
    import json
    import functools

    msg = '!AIVDM,1,1,,A,B69Gk3h071tpI02lT2ek?wg61P06,0*1F'
    decoded = decode(msg)

    # the following methods are only available for messages of types: 1, 2, 3, 4, 9, 11, 18
    assert isinstance(decoded, MessageType18)

    print("The raw radio value is:", decoded.radio)
    print("Communication state is SOTMDA:", decoded.is_sotdma)
    print("Communication state is ITDMA:", decoded.is_itdma)

    pretty_json = functools.partial(json.dumps, indent=4)
    print("Communication state:", pretty_json(decoded.get_communication_state()))

Encode Dict
--------------------

The following example shows how to create an AIS message using a dictionary of values::

    from pyais.encode import encode_dict
    from pyais.messages import MessageType1

    # This statement tells us which fields can be set for messages of type 1
    print(MessageType1.fields())

    # A dictionary of fields that we want to encode
    # Note that you can pass many more fields for type 1 messages, but we let pyais
    # use default values for those keys
    data = {
        'course': 219.3,
        'lat': 37.802,
        'lon': -122.341,
        'mmsi': '366053209',
        'type': 1
    }

    # This creates an encoded AIS message
    # Note, that `encode_dict` returns always a list of fragments.
    # This is done, because you may never know if a message fits into the 82 character
    # size limit of payloads
    encoded = encode_dict(data)
    print(encoded)

    # You can also change the NMEA fields like the radio channel:
    print(encode_dict(data, radio_channel="B"))

File stream
------------

The following example shows how to read and parse AIS messages from a file::

    import pathlib

    from pyais.stream import FileReaderStream

    filename = pathlib.Path(__file__).parent.joinpath('sample.ais')

    for msg in FileReaderStream(str(filename)):
        decoded = msg.decode()
        print(decoded)

Gatehouse wrappers
-------------------

Some AIS messages have so-called Gatehouse wrappers::

    import pathlib

    from pyais.stream import FileReaderStream

    filename = pathlib.Path(__file__).parent.joinpath('gatehouse.nmea')

    for msg in FileReaderStream(str(filename)):
        print('*' * 80)
        if msg.wrapper_msg is not None:  # <= optional gatehouse wrapper
            print('Country', msg.wrapper_msg.country)
            print('Online', msg.wrapper_msg.online_data)
            print('PSS', msg.wrapper_msg.pss)
            print('Region', msg.wrapper_msg.region)
            print('Timestamp', msg.wrapper_msg.timestamp)
        decoded = msg.decode()
        print(decoded)

Livestream
-----------
The Norwegian Coastal Administration offers real-time AIS data.
This live feed can be accessed via TCP/IP without prior registration.
The AIS data is freely available under the norwegian license for public data:

- https://data.norge.no/nlod/no/1.0
- https://kystverket.no/navigasjonstjenester/ais/tilgang-pa-ais-data/

Data can be read from a TCP/IP socket and is encoded according to IEC 62320-1:

- IP:   153.44.253.27
- Port: 5631

Code::

    from pyais.stream import TCPConnection

    host = '153.44.253.27'
    port = 5631

    for msg in TCPConnection(host, port=port):
        decoded_message = msg.decode()
        ais_content = decoded_message

        print('*' * 80)
        if msg.tag_block:
            # decode & print the tag block if it is available
            msg.tag_block.init()
            print(msg.tag_block.asdict())

        print(ais_content)

CSV
---

The following example shows how you could write the decoded data to CSV.
You first need to decode the data into a dictionary and then write the
dictionary to a CSV file using a `DictWriter`::

    import csv

    from pyais import decode

    ais_msg = "!AIVDO,1,1,,,B>qc:003wk?8mP=18D3Q3wgTiT;T,0*13"
    data_dict = decode(ais_msg).asdict()

    with open('decoded_message.csv', 'w') as f:
        w = csv.DictWriter(f, data_dict.keys())
        w.writeheader()
        w.writerow(data_dict)

TCP socket
-----------

The following example shows how to decode AIS messages from a TCP socket::

    from pyais.stream import TCPConnection

    url = '127.0.0.1'
    port = 12346

    for msg in TCPConnection(url, port=port):
        decoded_message = msg.decode()
        ais_content = decoded_message
        print(ais_content)
        # Do something with the AIS message

Event tracking
----------------

This example shows how to register event listeners as callbacks,
so that you are is instantly notified whenever a track is created, updated, or deleted::

    import pyais
    from pyais.tracker import AISTrackEvent

    host = '153.44.253.27'
    port = 5631


    def handle_create(track):
        # called every time an AISTrack is created
        print('create', track.mmsi)


    def handle_update(track):
        # called every time an AISTrack is updated
        print('update', track.mmsi)


    def handle_delete(track):
        # called every time an AISTrack is deleted (pruned)
        print('delete', track.mmsi)


    with pyais.AISTracker() as tracker:
        tracker.register_callback(AISTrackEvent.CREATED, handle_create)
        tracker.register_callback(AISTrackEvent.UPDATED, handle_update)
        tracker.register_callback(AISTrackEvent.DELETED, handle_delete)

        for msg in pyais.TCPConnection(host, port=port):
            tracker.update(msg)
            latest_tracks = tracker.n_latest_tracks(10)

Country and Flag
-----------------

The first 3 digits of any MMSI number are indicative of the vessel's flag:

    country_code, country_name = get_country(249110000)
    assert country_code, country_name == ('MT', 'Malta')

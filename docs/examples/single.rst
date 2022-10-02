###############################
Decode a single AIS message
###############################

You can decode AIVDM/AIVDO messages, as long as they are valid NMEA 0183 messages.

Please note that invalid checksums are ignored. If you want to raise an error for
invalid checksums set `error_if_checksum_invalid=True`.

References
----------

* AIS: https://en.wikipedia.org/wiki/Automatic_identification_system
* NMEA 0183: https://en.wikipedia.org/wiki/NMEA_0183
* AIVDM/AIVDO protocol decoding reference: https://gpsd.gitlab.io/gpsd/AIVDM.html

Examples
--------

Decode a single part AIS message using `decode()`::

    from pyais import decode
    decoded = decode(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
    print(decoded)

The `decode()` functions accepts a list of arguments: One argument for every part of a multipart message::

    from pyais import decode

    parts = [
        b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08",
        b"!AIVDM,2,2,4,A,000000000000000,2*20",
    ]

    # Decode a multipart message using decode
    decoded = decode(*parts)
    print(decoded)


Also the `decode()` function accepts either strings or bytes::

    decoded_b = decode(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
    decoded_s = decode("!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
    assert decoded_b == decoded_s

Decode the message into a dictionary::

    decoded = decode(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
    as_dict = decoded.asdict()
    print(as_dict)

Decode the message into a serialized JSON string::

    decoded = decode("!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
    json = decoded.to_json()
    print(json)

Read a file::

    from pyais.stream import FileReaderStream

    filename = "sample.ais"

    for msg in FileReaderStream(filename):
        decoded = msg.decode()
        print(decoded)

Decode a stream of messages (e.g. a list or generator)::

    from pyais import IterMessages

    fake_stream = [
        b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23",
        b"!AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F",
        b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B",
        b"!AIVDM,1,1,,B,13eaJF0P00Qd388Eew6aagvH85Ip,0*45",
        b"!AIVDM,1,1,,A,14eGrSPP00ncMJTO5C6aBwvP2D0?,0*7A",
        b"!AIVDM,1,1,,A,15MrVH0000KH<:V:NtBLoqFP2H9:,0*2F",
    ]
    for msg in IterMessages(fake_stream):
        print(msg.decode())

Note
--------
This library is often used for data analysis. This means that a researcher
analyzes large amounts of AIS messages. Such message streams might contain
thousands of messages with invalid checksums. Its up to the researcher to
decide whether he/she wants to include such messages in his/her analysis.
Raising an exception for every invalid checksum would both cause a
performance degradation because handling of such exceptions is expensive
and make it impossible to include such messages into the analysis.

If you want to raise an error if the checksum of a message is invalid set
the key word argument `error_if_checksum_invalid` to True.
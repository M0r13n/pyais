Public API
==========

Everything you need to decode, encode, stream, filter, and track AIS messages.

All names listed here can be imported from ``pyais`` directly, unless noted
otherwise.

.. contents::
   :local:
   :depth: 2

Decode
------

``decode(*args, error_if_checksum_invalid=False)``
   Decode one or more NMEA sentences into an AIS message object.
   Pass multiple arguments for multi-part messages. Accepts ``str`` or ``bytes``.

   .. code-block:: python

      from pyais import decode

      msg = decode(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
      print(msg.mmsi, msg.lat, msg.lon)

      # Multi-part message
      parts = [
          b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08",
          b"!AIVDM,2,2,4,A,000000000000000,2*20",
      ]
      msg = decode(*parts)

   Returns an instance of one of the ``MessageType*`` classes (see :doc:`messages`).

``decode_nmea_and_ais(*args, error_if_checksum_invalid=False)``
   Like ``decode()``, but returns a tuple ``(nmea_sentence, ais_message)``.
   Use this when you need access to the NMEA layer (tag blocks, checksums, etc.).

   Import from ``pyais.decode``.

``decode_nmea_line(line)``
   Parse a single raw NMEA line into an ``NMEASentence`` without decoding the
   AIS payload. Import from ``pyais.decode``.

Encode
------

``encode_dict(data, talker_id="AI", sentence_type="VDO", radio_channel="A", seq_id=None)``
   Encode a dictionary of values into NMEA 0183 AIS sentences.
   The dictionary must contain ``type`` (or ``msg_type``) and ``mmsi``.
   Returns a list of sentence strings (one per fragment).

   .. code-block:: python

      from pyais.encode import encode_dict

      data = {"type": 1, "mmsi": "366053209", "lat": 37.802, "lon": -122.341, "course": 219.3}
      sentences = encode_dict(data, radio_channel="B")

``encode_msg(msg, talker_id="AI", sentence_type="VDO", radio_channel="A", seq_id=None)``
   Encode a message object (created with ``MessageType*.create()``) into NMEA sentences.

   .. code-block:: python

      from pyais.messages import MessageType1
      from pyais.encode import encode_msg

      payload = MessageType1.create(mmsi="366053209", lat=37.802, lon=-122.341)
      sentences = encode_msg(payload)

``ais_to_nmea_0183(payload, talker_id, sentence_type, radio_channel, fill_bits, seq_id=None)``
   Low-level function. Takes an armored AIS payload string and wraps it in
   NMEA 0183 sentences. Import from ``pyais.encode``.

Messages
--------

``NMEAMessage``
   Base class for NMEA sentences. Parses the NMEA 0183 layer. Has attributes:
   ``raw``, ``delimiter``, ``talker_id``, ``type``, ``data_fields``, ``checksum``,
   ``is_valid``, ``tag_block``, ``wrapper_msg``. Call ``.decode()`` to get the AIS payload.

``AISSentence``
   An AIS sentence (``!AIVDM`` or ``!AIVDO``). Extends ``NMEAMessage`` with AIS-specific
   attributes: ``ais_id``, ``fragment_count``, ``fragment_number``, ``payload``,
   ``fill_bits``, ``is_single``, ``is_multi``, ``seq_id``, ``channel``.

``TagBlock``
   Represents an NMEA 4.10 tag block (the ``\\...\\`` prefix before a sentence).
   Call ``.init()`` to parse lazily, then ``.asdict()`` to get a dictionary.
   Create new tag blocks with ``TagBlock.create(...)`` or ``TagBlock.create_str(...)``.

``ANY_MESSAGE``
   Type alias: a union of all ``MessageType*`` classes. Use for type hints.

``MSG_CLASS``
   Dictionary mapping AIS message type IDs (0–28) to their classes.
   Import from ``pyais.messages``.

All ``MessageType*`` classes
   One class per AIS message type (1–28), plus subtypes for types 6 and 8.
   See :doc:`messages` for the full list.

   Every message class has:

   - ``.create(**kwargs)`` — create an instance with defaults for missing fields
   - ``.fields()`` — return a tuple of all field names
   - ``.asdict()`` — return a dictionary of all fields
   - ``.to_json()`` — return a JSON string
   - ``.encode()`` — return ``(armored_payload, fill_bits)``

Streams
-------

All stream classes are iterable. Each iteration yields an ``NMEAMessage``
(or ``AISSentence``). Call ``.decode()`` on each to get the AIS payload.
All support the ``with`` statement and accept optional ``preprocessor`` and
``tbq`` (tag block queue) arguments.

``FileReaderStream(filename, mode="rb", ...)``
   Read NMEA messages from a file.

   .. code-block:: python

      from pyais.stream import FileReaderStream

      with FileReaderStream("sample.ais") as stream:
          for msg in stream:
              print(msg.decode())

``TCPConnection(host, port=80, ...)``
   Connect to a remote TCP server and read AIS data.

   .. code-block:: python

      from pyais.stream import TCPConnection

      for msg in TCPConnection("153.44.253.27", port=5631):
          print(msg.decode())

``UDPReceiver(host, port, ...)``
   Listen for incoming UDP packets. Import from ``pyais.stream``.

``TCPServer(host, port=80, ..., timeout=-1)``
   A TCP server that accepts multiple concurrent client connections.
   Uses ``selectors`` for I/O multiplexing. Import from ``pyais.stream``.

``IterMessages(messages, ...)``
   Wrap any iterable of bytes (or strings via ``IterMessages.from_strings()``)
   and assemble multi-part messages.

   .. code-block:: python

      from pyais import IterMessages

      messages = [b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23", ...]
      for msg in IterMessages(messages):
          print(msg.decode())

``ByteStream(iterable, ...)``
   Like ``IterMessages`` but for use with the ``Stream`` base class interface.
   Import from ``pyais.stream``.

``TagBlockQueue(maxsize=0)``
   A queue for grouping NMEA sentences by their tag block group ID.
   Pass an instance to any stream class via the ``tbq`` argument.
   Import from ``pyais.stream``.

``NMEAQueue(maxsize=0, tbq=None)``
   A thread-safe queue for assembling NMEA sentences from raw lines.
   Call ``put_line(line)`` to feed data, ``get_or_none()`` to retrieve
   assembled sentences. Import from ``pyais.queue``.

``PreprocessorProtocol``
   A protocol for preprocessing raw lines into NMEA 0183 format.
   Implement ``process(line: bytes) -> bytes`` and pass an instance to any
   stream class via the ``preprocessor`` argument.

Tracking
--------

``AISTracker(ttl_in_seconds=600, stream_is_ordered=False)``
   Maintains a collection of vessel tracks. Each track is identified by MMSI.
   Handles out-of-order messages. Set ``stream_is_ordered=True`` for better
   performance when messages arrive in timestamp order.

   .. code-block:: python

      from pyais import AISTracker

      with AISTracker() as tracker:
          tracker.update(msg)                    # add/update a track
          track = tracker.get_track(366053209)   # get a specific track
          latest = tracker.n_latest_tracks(10)   # get the 10 most recent tracks
          tracker.cleanup()                      # remove expired tracks

   Register callbacks for track events:

   .. code-block:: python

      from pyais.tracker import AISTrackEvent

      tracker.register_callback(AISTrackEvent.CREATED, lambda t: print("new", t.mmsi))
      tracker.register_callback(AISTrackEvent.UPDATED, lambda t: print("update", t.mmsi))
      tracker.register_callback(AISTrackEvent.DELETED, lambda t: print("gone", t.mmsi))

``AISTrack``
   A consolidated view of a vessel. Fields: ``mmsi``, ``turn``, ``speed``,
   ``lon``, ``lat``, ``course``, ``heading``, ``imo``, ``callsign``,
   ``shipname``, ``ship_type``, ``destination``, ``last_updated``, and more.

``AISTrackEvent``
   Enum with values ``CREATED``, ``UPDATED``, ``DELETED``.
   Import from ``pyais.tracker``.

Filters
-------

All filters are in ``pyais.filter``. Chain them with ``FilterChain``.

``AttributeFilter(func)``
   Keep messages where ``func(msg)`` returns ``True``.

``NoneFilter(*attrs)``
   Keep messages where the named attributes are not ``None``.

``MessageTypeFilter(*types)``
   Keep messages of the given AIS types (e.g. ``MessageTypeFilter(1, 2, 3)``).

``DistanceFilter((lat, lon), distance_km)``
   Keep messages within ``distance_km`` of a reference point.

``GridFilter(lat_min, lon_min, lat_max, lon_max)``
   Keep messages inside a geographic bounding box.

``FilterChain([filter1, filter2, ...])``
   Apply filters in sequence. Call ``chain.filter(stream)`` to get a
   generator of filtered, decoded messages.

   .. code-block:: python

      from pyais.filter import FilterChain, MessageTypeFilter, DistanceFilter
      from pyais.stream import TCPConnection

      chain = FilterChain([
          MessageTypeFilter(1, 2, 3),
          DistanceFilter((51.9, 5.3), distance_km=100),
      ])

      with TCPConnection("153.44.253.27", port=5631) as stream:
          for msg in chain.filter(stream):
              print(msg.mmsi, msg.lat, msg.lon)

``haversine((lat1, lon1), (lat2, lon2))``
   Great-circle distance between two points in kilometers.

``is_in_grid(lat, lon, lat_min, lon_min, lat_max, lon_max)``
   Check if a point is inside a bounding box.

Utilities
---------

``get_country(mmsi)``
   Return ``(country_code, country_name)`` for an MMSI number.
   The first 3 digits of an MMSI identify the flag state.
   Import from ``pyais.util``.

   .. code-block:: python

      from pyais.util import get_country

      code, name = get_country(249110000)
      print(code, name)  # MT Malta

``bit_vector``
   A bit-level accessor for binary data. Import from ``pyais``.

``compute_checksum(msg)``
   Compute the NMEA 0183 checksum for a message. Import from ``pyais.util``.

``json_to_data(data)``
   Decode base64-encoded byte fields in a dictionary produced by ``to_json()``,
   so the result can be passed to ``encode_dict()``. Import from ``pyais.util``.

``decode_bytes_as_ascii6(data, start_bit=0, total_bits=-1)``
   Decode 6-bit ASCII encoded text from binary data. Import from ``pyais.util``.

Exceptions
----------

All exceptions are in ``pyais.exceptions`` and inherit from ``AISBaseException``.

- ``InvalidNMEAMessageException`` — the NMEA sentence is malformed
- ``InvalidNMEAChecksum`` — the NMEA checksum does not match
- ``UnknownMessageException`` — the message type is not supported
- ``MissingMultipartMessageException`` — a multi-part message is missing fragments
- ``TooManyMessagesException`` — too many fragments provided
- ``InvalidDataTypeException`` — wrong data type passed to encode/decode
- ``TagBlockNotInitializedException`` — ``.asdict()`` called before ``.init()``
- ``MissingPayloadException`` — valid NMEA sentence without AIS payload

Examples
========

Every example is a runnable Python script. The source files are in the
`examples directory <https://github.com/M0r13n/pyais/tree/master/examples>`_.

.. contents::
   :local:
   :depth: 2

Decoding
--------

Decode a single message
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais import decode

   msg = decode(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
   print(msg.mmsi, msg.lat, msg.lon)

Decode a multi-part message
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais import decode

   parts = [
       b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08",
       b"!AIVDM,2,2,4,A,000000000000000,2*20",
   ]
   msg = decode(*parts)
   print(msg)

Decode to a dictionary or JSON
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais import decode

   msg = decode(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
   print(msg.asdict())    # dictionary of all fields
   print(msg.to_json())   # JSON string

Decode from a list of messages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais import IterMessages

   messages = [
       b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23",
       b"!AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F",
       b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B",
   ]
   for msg in IterMessages(messages):
       print(msg.decode())

Access raw binary payload (types 6, 8, 17, 25, 26, 27)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais import decode

   # Type 6 with unknown DAC/FID — payload is raw bytes
   msg = decode(b"!AIVDM,1,1,,B,6B?n;be:cbapalgc;i6?Ow4,2*4A")
   print(msg.dac, msg.fid)
   print(msg.data)  # b'\xeb/\x11\x8f\x7f\xf1'

Decode from raw binary (no NMEA layer)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais import bit_vector
   from pyais.messages import MSG_CLASS

   payload = b'\x20\x6f\xab\x71\xdf\x80\x32\xe3\x6e\x78\x3d\xda\xa7\x49\x65\xf4\xca\x9f\x6b\xe7\x07'
   bv = bit_vector(payload, pad=0)
   ais_id = bv.get(0, 6)
   msg = MSG_CLASS[ais_id].from_vector(bv)
   print(msg)

Decode a single NMEA sentence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais.messages import NMEAMessage

   msg = NMEAMessage(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")
   print(msg.decode())

   # Or from a string
   msg = NMEAMessage.from_string("!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")

Encoding
--------

Encode from a dictionary
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais.encode import encode_dict
   from pyais.messages import MessageType1

   # See available fields
   print(MessageType1.fields())

   data = {
       "type": 1,
       "mmsi": "366053209",
       "lat": 37.802,
       "lon": -122.341,
       "course": 219.3,
   }
   sentences = encode_dict(data, radio_channel="B")
   print(sentences[0])

Encode from a message object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais.messages import MessageType1, MessageType5
   from pyais.encode import encode_msg

   # Create a position report
   pos = MessageType1.create(mmsi="366053209", lat=37.802, lon=-122.341, course=219.3)
   print(encode_msg(pos))

   # Create a static data report
   static = MessageType5.create(mmsi="123", shipname="TITANIC", callsign="TITANIC", destination="New York")
   print(encode_msg(static))

Encode with a tag block
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais.encode import encode_dict
   from pyais.messages import TagBlock

   data = {"type": 1, "mmsi": "366053209", "lat": 37.802, "lon": -122.341}
   nmea = encode_dict(data, radio_channel="B")[0]

   tb = TagBlock.create_str(receiver_timestamp=12415440354, source_station="foobar", line_count=157036)
   print(f"\\{tb}\\{nmea}")

Round-trip: decode to JSON and back
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import json
   from pyais import decode, encode_dict
   from pyais.util import json_to_data

   orig = b"!AIVDO,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*45"
   decoded = decode(orig)
   json_str = decoded.to_json(ignore_spare=False)

   # Re-encode from JSON
   nmea = encode_dict(json_to_data(json.loads(json_str)))
   assert nmea[0].encode() == orig

CLI encoder
^^^^^^^^^^^

pyais includes a command-line encoder. Pipe JSON to stdin:

.. code-block:: console

   $ echo '{"type": 1, "mmsi": "366053209", "lat": 37.802, "lon": -122.341}' | ais-encode

Streaming
---------

Read from a file
^^^^^^^^^^^^^^^^

.. code-block:: python

   import pathlib
   from pyais.stream import FileReaderStream

   filename = pathlib.Path(__file__).parent / "sample.ais"

   with FileReaderStream(str(filename)) as stream:
       for msg in stream:
           decoded = msg.decode()
           print(decoded.mmsi, decoded.lat, decoded.lon)

Connect to a live TCP feed
^^^^^^^^^^^^^^^^^^^^^^^^^^

The Norwegian Coastal Administration offers free real-time AIS data:

- IP: ``153.44.253.27``, Port: ``5631``
- License: https://data.norge.no/nlod/no/1.0

.. code-block:: python

   from pyais.stream import TCPConnection

   for msg in TCPConnection("153.44.253.27", port=5631):
       decoded = msg.decode()
       print(decoded)

       if msg.tag_block:
           msg.tag_block.init()
           print(msg.tag_block.asdict())

Connect to a TCP server (local)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais.stream import TCPConnection

   for msg in TCPConnection("127.0.0.1", port=12346):
       print(msg.decode())

Listen for UDP packets
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais.stream import UDPReceiver

   for msg in UDPReceiver("127.0.0.1", 12346):
       print(msg.decode())

Run a TCP server
^^^^^^^^^^^^^^^^

Accept multiple concurrent client connections:

.. code-block:: python

   from pyais.stream import TCPServer

   with TCPServer("0.0.0.0", 5678) as server:
       for i, msg in enumerate(server, 1):
           print(i, msg)

Handle out-of-order messages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

UDP and other unreliable transports may deliver fragments out of order.
``IterMessages`` handles reassembly:

.. code-block:: python

   from pyais.stream import IterMessages

   messages = [
       b"!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07",
       b"!AIVDM,2,2,1,A,F@V@00000000000,2*35",
       b"!AIVDM,2,2,9,A,F@V@00000000000,2*3D",
       b"!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F",
   ]
   for msg in IterMessages(messages):
       print(msg.decode())

Work with tag blocks
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import pathlib
   from pyais.decode import decode_nmea_and_ais
   from pyais.messages import TagBlock
   from pyais.stream import FileReaderStream

   # Single message with tag block
   raw = b"\\g:1-2-73874,n:157036,s:r003669945,c:12415440354*A\\!AIVDM,1,1,,B,15N4cJ005Jrek0H@9nDW5608EP,013"
   nmea, ais = decode_nmea_and_ais(raw)
   if nmea.tag_block:
       nmea.tag_block.init()
       print(nmea.tag_block.asdict())

   # Stream with tag blocks
   with FileReaderStream("sample.ais") as stream:
       for msg in stream:
           if msg.tag_block:
               msg.tag_block.init()
               print(msg.tag_block.asdict())
           print(msg.decode())

   # Create tag blocks
   tb_bytes = TagBlock.create(receiver_timestamp=12415440354, source_station="foobar", line_count=157036)
   tb_str = TagBlock.create_str(receiver_timestamp=12415440354, source_station="foobar", line_count=157036)

Group tag blocks
^^^^^^^^^^^^^^^^

Use ``TagBlockQueue`` to buffer sentences until a tag block group is complete:

.. code-block:: python

   import pathlib
   from pyais.stream import FileReaderStream, TagBlockQueue

   tbq = TagBlockQueue()
   with FileReaderStream("sample.ais", tbq=tbq) as stream:
       for msg in stream:
           while not tbq.empty():
               print(tbq.get_nowait())

Use NMEAQueue for thread-safe assembly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais.queue import NMEAQueue

   q = NMEAQueue()

   # Feed lines from any source
   q.put_line(b"!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C")
   q.put_line(b"!AIVDM,2,2,1,A,88888888880,2*25")

   msg = q.get_or_none()
   if msg:
       print(msg.decode())

Gatehouse wrappers
^^^^^^^^^^^^^^^^^^

Some feeds prepend Gatehouse wrapper sentences (``$PGHP,...``):

.. code-block:: python

   import pathlib
   from pyais.stream import FileReaderStream

   with FileReaderStream("gatehouse.nmea") as stream:
       for msg in stream:
           if msg.wrapper_msg is not None:
               print("Country:", msg.wrapper_msg.country)
               print("Timestamp:", msg.wrapper_msg.timestamp)
               print("Region:", msg.wrapper_msg.region)
           print(msg.decode())

Preprocessing
^^^^^^^^^^^^^

Implement ``PreprocessorProtocol`` to handle custom input formats:

.. code-block:: python

   import re
   from pyais.stream import FileReaderStream, PreprocessorProtocol

   class MyPreprocessor(PreprocessorProtocol):
       def process(self, line: bytes) -> bytes:
           # Strip a custom prefix like "[2024-07-19 08:45:27.141] "
           match = re.search(b".* (.*)", line)
           return match.group(1)

   with FileReaderStream("custom.log", preprocessor=MyPreprocessor()) as stream:
       for msg in stream:
           print(msg.decode())

Tracking
--------

Track vessels from a file
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import pathlib
   from pyais import AISTracker
   from pyais.stream import FileReaderStream

   with FileReaderStream("sample.ais") as stream:
       with AISTracker() as tracker:
           for msg in stream:
               tracker.update(msg)

   # Get the latest 10 tracks
   for track in tracker.n_latest_tracks(10):
       print(track.mmsi, track.shipname, track.lat, track.lon)

   # Get a specific track
   track = tracker.get_track(249191000)

Track vessels from a live feed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import pyais

   with pyais.AISTracker() as tracker:
       for msg in pyais.TCPConnection("153.44.253.27", port=5631):
           tracker.update(msg)
           for track in tracker.n_latest_tracks(10):
               print(track.mmsi, track.lat, track.lon)

Track with event callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import pyais
   from pyais.tracker import AISTrackEvent

   def on_create(track):
       print("new vessel:", track.mmsi)

   def on_update(track):
       print("update:", track.mmsi)

   def on_delete(track):
       print("expired:", track.mmsi)

   with pyais.AISTracker() as tracker:
       tracker.register_callback(AISTrackEvent.CREATED, on_create)
       tracker.register_callback(AISTrackEvent.UPDATED, on_update)
       tracker.register_callback(AISTrackEvent.DELETED, on_delete)

       for msg in pyais.TCPConnection("153.44.253.27", port=5631):
           tracker.update(msg)

Track with filters
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import pathlib
   from pyais import AISTracker
   from pyais.filter import AttributeFilter, FilterChain, MessageTypeFilter, NoneFilter
   from pyais.stream import FileReaderStream

   chain = FilterChain([
       AttributeFilter(lambda x: not hasattr(x, "turn") or x.turn == -128.0),
       NoneFilter("lon", "lat"),
       MessageTypeFilter(1, 2, 3),
   ])

   with FileReaderStream("sample.ais") as stream:
       with AISTracker() as tracker:
           for msg in chain.filter(stream):
               tracker.update(msg)
               for track in tracker.n_latest_tracks(10):
                   print(track.mmsi, track.lat, track.lon)

Print tracks as a table
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import sys
   import pyais

   def print_table(tracks):
       headers = ["mmsi", "callsign", "shipname", "lat", "lon"]
       rows = [[getattr(t, a) or "N.A." for a in headers] for t in tracks]
       fmt = "{:>15}" * (len(headers) + 1)
       sys.stdout.write(fmt.format("", *headers) + "\n")
       for i, row in enumerate(rows, 1):
           sys.stdout.write(fmt.format(i, *row) + "\n")

   with pyais.AISTracker() as tracker:
       for msg in pyais.TCPConnection("153.44.253.27", port=5631):
           tracker.update(msg)
           print_table(tracker.n_latest_tracks(10))

Filtering
---------

Filter a live stream
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais.filter import (
       AttributeFilter, DistanceFilter, FilterChain,
       GridFilter, MessageTypeFilter, NoneFilter,
   )
   from pyais.stream import TCPConnection

   chain = FilterChain([
       AttributeFilter(lambda x: not hasattr(x, "turn") or x.turn == -128.0),
       NoneFilter("lon", "lat", "mmsi2"),
       MessageTypeFilter(1, 2, 3),
       DistanceFilter((51.900, 5.320), distance_km=1000),
       GridFilter(lat_min=50, lon_min=0, lat_max=52, lon_max=5),
   ])

   with TCPConnection("153.44.253.27", port=5631) as stream:
       for msg in chain.filter(stream):
           print(msg.mmsi, msg.lat, msg.lon)

Utilities
---------

Get communication state
^^^^^^^^^^^^^^^^^^^^^^^

Messages of types 1, 2, 3, 4, 9, 11, and 18 contain TDMA communication state:

.. code-block:: python

   import json
   from pyais import decode

   msg = decode(b"!AIVDM,1,1,,A,B69Gk3h071tpI02lT2ek?wg61P06,0*1F")

   print("Radio:", msg.radio)
   print("SOTDMA:", msg.is_sotdma)
   print("ITDMA:", msg.is_itdma)
   print("State:", json.dumps(msg.get_communication_state(), indent=2))

Get vessel country from MMSI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyais.util import get_country

   code, name = get_country(249110000)
   print(code, name)  # MT Malta

Write decoded data to CSV
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import csv
   from pyais import decode

   msg = decode("!AIVDO,1,1,,,B>qc:003wk?8mP=18D3Q3wgTiT;T,0*13")
   data = msg.asdict()

   with open("output.csv", "w") as f:
       writer = csv.DictWriter(f, data.keys())
       writer.writeheader()
       writer.writerow(data)

AIS Monitor TUI
---------------

``examples/ais_monitor.py`` is a full terminal application for real-time
ship traffic monitoring. It displays a live message stream, a sortable
vessel table, and vessel detail views. Built entirely with pyais and
Python's standard library.

.. code-block:: console

   $ python examples/ais_monitor.py

Requires a terminal that supports ANSI escape codes.

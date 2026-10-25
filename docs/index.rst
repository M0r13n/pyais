pyais
=====

Decode and encode AIS (Automatic Identification System) messages. Pure Python.

AIS is a tracking system used by vessels and coastal stations. Ships broadcast
their identity, position, course, and speed over VHF radio. pyais reads these
messages from NMEA 0183 sentences and turns them into Python objects.

- Decode single messages, files, TCP/UDP sockets, or any iterable of bytes
- Encode messages from dictionaries or message objects
- Track vessels over time with ``AISTracker``
- Filter messages by type, location, or any attribute
- Supports all 28 AIS message types, including binary subtypes for types 6 and 8

Installation
------------

.. code-block:: console

   $ pip install pyais

Requires Python 3.9+.

Quick start
-----------

Decode a single message:

.. code-block:: python

   from pyais import decode

   msg = decode(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
   print(msg.mmsi)    # 366053209
   print(msg.lat)     # 37.8031
   print(msg.lon)     # -122.3413
   print(msg.speed)   # 12.3

Read a file:

.. code-block:: python

   from pyais.stream import FileReaderStream

   with FileReaderStream("sample.ais") as stream:
       for msg in stream:
           decoded = msg.decode()
           print(decoded.mmsi, decoded.lat, decoded.lon)

Connect to a live TCP feed:

.. code-block:: python

   from pyais.stream import TCPConnection

   for msg in TCPConnection("153.44.253.27", port=5631):
       decoded = msg.decode()
       print(decoded)

Encode a message:

.. code-block:: python

   from pyais.encode import encode_dict

   data = {"type": 1, "mmsi": "366053209", "lat": 37.802, "lon": -122.341, "course": 219.3}
   encoded = encode_dict(data)
   print(encoded[0])

Track vessels:

.. code-block:: python

   from pyais import AISTracker
   from pyais.stream import FileReaderStream

   with FileReaderStream("sample.ais") as stream:
       with AISTracker() as tracker:
           for msg in stream:
               tracker.update(msg)
           for track in tracker.n_latest_tracks(10):
               print(track.mmsi, track.shipname, track.lat, track.lon)

What to read next
-----------------

- :doc:`api` — the full public API, organized by task
- :doc:`messages` — all 28 message types, with subtype tables for types 6 and 8
- :doc:`examples` — runnable examples for every feature
- :doc:`install` — installation details and troubleshooting

Performance
-----------

pyais decodes roughly 270,000 messages per second on CPython (single core,
Apple M3). Under PyPy it reaches about 1.2 million messages per second after
JIT warmup.

.. toctree::
   :maxdepth: 2
   :hidden:

   install
   api
   messages
   examples

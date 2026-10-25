AIS Messages
============

pyais supports all 28 AIS message types defined in ITU-R M.1371.
When you decode a message, pyais returns an instance of the matching
``MessageType*`` class. The class name tells you the message type.

.. contents::
   :local:
   :depth: 2

Message type overview
---------------------

.. list-table::
   :header-rows: 1
   :widths: 5 35 20 40

   * - Type
     - Name
     - Class
     - Key fields
   * - 1
     - Position Report (Class A, SOTDMA)
     - ``MessageType1``
     - mmsi, lat, lon, speed, course, heading, status
   * - 2
     - Position Report (Class A, SOTDMA)
     - ``MessageType2``
     - same as type 1
   * - 3
     - Position Report (Class A, ITDMA)
     - ``MessageType3``
     - same as type 1
   * - 4
     - Base Station Report
     - ``MessageType4``
     - mmsi, year, month, day, hour, minute, lat, lon
   * - 5
     - Static and Voyage Related Data
     - ``MessageType5``
     - mmsi, imo, callsign, shipname, destination, draught, ship_type
   * - 6
     - Binary Addressed Message
     - ``MessageType6``
     - mmsi, dest_mmsi, dac, fid, data — see subtypes below
   * - 7
     - Binary Acknowledge
     - ``MessageType7``
     - mmsi, mmsi1–mmsi4
   * - 8
     - Binary Broadcast Message
     - ``MessageType8``
     - mmsi, dac, fid, data — see subtypes below
   * - 9
     - SAR Aircraft Position Report
     - ``MessageType9``
     - mmsi, lat, lon, speed, course, alt
   * - 10
     - UTC/Date Inquiry
     - ``MessageType10``
     - mmsi, dest_mmsi
   * - 11
     - UTC/Date Response
     - ``MessageType11``
     - mmsi, year, month, day, hour, minute, lat, lon
   * - 12
     - Addressed Safety-Related Message
     - ``MessageType12``
     - mmsi, dest_mmsi, text
   * - 13
     - Identical to type 7
     - ``MessageType13``
     - same as type 7
   * - 14
     - Safety-Related Broadcast Message
     - ``MessageType14``
     - mmsi, text
   * - 15
     - Interrogation
     - ``MessageType15``
     - mmsi, mmsi1, mmsi2
   * - 16
     - Assignment Mode Command
     - ``MessageType16``
     - mmsi, mmsi1, mmsi2, offset1, increment1
   * - 17
     - DGNSS Broadcast Binary Message
     - ``MessageType17``
     - mmsi, lat, lon, data
   * - 18
     - Position Report (Class B, CS)
     - ``MessageType18``
     - mmsi, lat, lon, speed, course, heading
   * - 19
     - Extended Class B Position Report
     - ``MessageType19``
     - mmsi, lat, lon, speed, course, shipname, ship_type
   * - 20
     - Data Link Management
     - ``MessageType20``
     - mmsi, offset1–4, number1–4, timeout1–4
   * - 21
     - Aid-to-Navigation Report
     - ``MessageType21``
     - mmsi, name, lat, lon, aid_type, to_bow, to_stern
   * - 22
     - Channel Management
     - ``MessageType22``
     - mmsi, channel_a, channel_b, ne_lon, ne_lat, sw_lon, sw_lat
   * - 23
     - Group Assignment Command
     - ``MessageType23``
     - mmsi, ne_lon, ne_lat, sw_lon, sw_lat, station_type
   * - 24
     - Static Data Report
     - ``MessageType24``
     - mmsi, shipname (part A) or ship_type (part B)
   * - 25
     - Single Slot Binary Message
     - ``MessageType25``
     - mmsi, dest_mmsi (addressed) or data (broadcast)
   * - 26
     - Multiple Slot Binary Message
     - ``MessageType26``
     - mmsi, dest_mmsi (addressed) or data (broadcast)
   * - 27
     - Long Range AIS Broadcast
     - ``MessageType27``
     - mmsi, lat, lon, speed, course, status
   * - 28
     - Aid-to-Navigation Report (single-slot)
     - ``MessageType28``
     - mmsi, lat, lon, aid_type, station_type

Message type 6 — Binary Addressed Message
------------------------------------------

Type 6 messages carry binary payloads addressed to a specific vessel.
The payload format depends on two fields:

- **DAC** (Designated Area Code, 10 bits): identifies the standards body
- **FID** (Functional ID, 6 bits): identifies the message function

pyais decodes known DAC/FID combinations into typed subtypes. Unknown
combinations return ``MessageType6Default`` with the raw payload in ``.data``.

.. list-table::
   :header-rows: 1
   :widths: 8 8 30 54

   * - DAC
     - FID
     - Class
     - Description
   * - 1
     - 16
     - ``MessageType6Dac1Fid16A``
     - Number of persons on board (no destination address)
   * - 1
     - 16
     - ``MessageType6Dac1Fid16B``
     - Number of persons on board (with destination address)
   * - 1
     - 18
     - ``MessageType6Dac1Fid18``
     - Clearance time to enter port
   * - 1
     - 20
     - ``MessageType6Dac1Fid20``
     - Berthing data (addressed)
   * - 1
     - 23
     - ``MessageType6Dac1Fid23``
     - Area notice (addressed)
   * - 1
     - 25
     - ``MessageType6Dac1Fid25``
     - Dangerous cargo indication
   * - any
     - any
     - ``MessageType6Default``
     - Unspecified binary payload (raw bytes in ``.data``)

Accessing the raw payload of an unknown subtype:

.. code-block:: python

   from pyais import decode

   msg = decode(b"!AIVDM,1,1,,B,6B?n;be:cbapalgc;i6?Ow4,2*4A")
   print(msg.dac)       # 1
   print(msg.fid)       # 0
   print(msg.data)      # b'\xeb/\x11\x8f\x7f\xf1' (raw bytes)

Message type 8 — Binary Broadcast Message
------------------------------------------

Type 8 messages carry binary payloads broadcast to all vessels in range.
Like type 6, the payload format depends on DAC and FID.

.. list-table::
   :header-rows: 1
   :widths: 8 8 30 54

   * - DAC
     - FID
     - Class
     - Description
   * - 1
     - 0
     - ``MessageType8Dac1Fid0``
     - Broadcast text (6-bit ASCII)
   * - 1
     - 11
     - ``MessageType8Dac1Fid11``
     - Meteorological/Hydrological data (IMO 236, superseded by FID 31)
   * - 1
     - 16
     - ``MessageType8Dac1Fid16``
     - IALA VTS targets (targets from non-AIS sources)
   * - 1
     - 17
     - ``MessageType8Dac1Fid17``
     - VTS synthetic targets (IMO 236)
   * - 1
     - 19
     - ``MessageType8Dac1Fid19``
     - Marine traffic signal (IMO 289)
   * - 1
     - 20
     - ``MessageType8Dac1Fid20``
     - Berthing data (broadcast, IMO 289)
   * - 1
     - 21
     - ``MessageType8Dac1Fid21``
     - Weather observation from ship (WMO variant, IMO 289)
   * - 1
     - 21
     - ``MessageType8Dac1Fid21NonWmo``
     - Weather observation from ship (non-WMO variant, IMO 289)
   * - 1
     - 22
     - ``MessageType8Dac1Fid22``
     - Area notice (broadcast, IMO 289)
   * - 1
     - 24
     - ``MessageType8Dac1Fid24``
     - Extended ship static and voyage data (IMO 289)
   * - 1
     - 26
     - ``MessageType8Dac1Fid26``
     - Environmental data (IMO 289)
   * - 1
     - 27
     - ``MessageType8Dac1Fid27``
     - Route information (broadcast, IMO 289)
   * - 1
     - 29
     - ``MessageType8Dac1Fid29``
     - Text description (broadcast, IMO 289)
   * - 1
     - 31
     - ``MessageType8Dac1Fid31``
     - Meteorological/Hydrological data (IMO 289)
   * - 200
     - 10
     - ``MessageType8Dac200Fid10``
     - Binary broadcast (DAC 200)
   * - 200
     - 23
     - ``MessageType8Dac200Fid23``
     - Binary broadcast (DAC 200)
   * - 200
     - 24
     - ``MessageType8Dac200Fid24``
     - Binary broadcast (DAC 200)
   * - 200
     - 40
     - ``MessageType8Dac200Fid40``
     - Binary broadcast (DAC 200)
   * - 367
     - 33
     - ``MessageType8Dac367Fid33``
     - US environmental message (DAC 367)
   * - any
     - any
     - ``MessageType8Default``
     - Unspecified binary payload (raw bytes in ``.data``)

Accessing the raw payload of an unknown subtype:

.. code-block:: python

   from pyais import decode

   msg = decode(b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47")
   print(msg.dac)       # 1
   print(msg.fid)       # 12
   print(msg.data)      # raw bytes

Common message operations
--------------------------

Every decoded message has these methods:

``msg.asdict()``
   Return all fields as a dictionary. Spare fields are omitted by default.

   .. code-block:: python

      from pyais import decode

      msg = decode(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05")
      print(msg.asdict())
      # {'msg_type': 1, 'mmsi': 366053209, 'lat': 37.8031, 'lon': -122.3413, ...}

``msg.to_json()``
   Return all fields as a JSON string. Byte fields are base64-encoded.

``msg.fields()``
   Class method. Return a tuple of all field names for this message type.

   .. code-block:: python

      from pyais.messages import MessageType1

      print(MessageType1.fields())
      # ('msg_type', 'repeat', 'mmsi', 'status', 'turn', 'speed', ...)

Creating messages for encoding
-------------------------------

Use ``MessageType*.create()`` to create a message with defaults for missing fields:

.. code-block:: python

   from pyais.messages import MessageType1, MessageType5
   from pyais.encode import encode_msg

   # Only mmsi is required; all other fields have defaults
   pos = MessageType1.create(mmsi="366053209", lat=37.802, lon=-122.341, course=219.3)
   sentences = encode_msg(pos)

   # Type 5: static data
   static = MessageType5.create(mmsi="366053209", shipname="TITANIC", callsign="TITANIC")
   sentences = encode_msg(static)

For type 6 and 8 messages, ``create()`` dispatches to the correct subtype
based on the ``dac`` and ``fid`` keyword arguments:

.. code-block:: python

   from pyais.messages import MessageType8

   # Creates a MessageType8Dac1Fid31 (Meteorological/Hydrological, IMO 289)
   msg = MessageType8.create(mmsi="366053209", dac=1, fid=31, ...)

Communication state
--------------------

Messages of types 1, 2, 3, 4, 9, 11, and 18 contain a 19–20 bit
communication state field (``.radio``). This field holds TDMA
synchronization information.

.. code-block:: python

   from pyais import decode

   msg = decode(b"!AIVDM,1,1,,A,B69Gk3h071tpI02lT2ek?wg61P06,0*1F")

   msg.radio                        # raw integer value
   msg.is_sotdma                    # True if SOTDMA (property)
   msg.is_itdma                     # True if ITDMA (property)
   msg.get_communication_state()    # dict with sync state, slot timeout, etc.

NMEA sentence layer
--------------------

Every ``NMEAMessage`` (the object yielded by streams) has these attributes:

- ``raw`` — the original bytes
- ``talker_id`` — two-letter talker ID (e.g. ``"AI"``)
- ``type`` — three-letter sentence type (e.g. ``"VDM"``, ``"VDO"``)
- ``channel`` — radio channel (``"A"`` or ``"B"``)
- ``is_valid`` — whether the NMEA checksum is correct
- ``tag_block`` — optional ``TagBlock`` (call ``.init()`` before use)
- ``wrapper_msg`` — optional Gatehouse wrapper message
- ``is_single`` / ``is_multi`` — whether the sentence is single or multi-part

Gatehouse wrappers
------------------

Some AIS feeds prepend a Gatehouse wrapper sentence (``$PGHP,...``) before
each AIS message. These wrappers carry metadata such as timestamps and
region information. pyais parses them automatically when using any stream
class. Access the wrapper via ``msg.wrapper_msg``.

.. code-block:: python

   from pyais.stream import FileReaderStream

   with FileReaderStream("gatehouse.nmea") as stream:
       for msg in stream:
           if msg.wrapper_msg is not None:
               print(msg.wrapper_msg.timestamp)
               print(msg.wrapper_msg.country)
           print(msg.decode())

Tag blocks
----------

NMEA 4.10 tag blocks are key-value metadata wrapped in backslashes before
a sentence: ``\\s:2573135,c:1671620143*0B\\!AIVDM,...``

Tag blocks are parsed lazily. Call ``.init()`` before accessing fields:

.. code-block:: python

   from pyais.stream import FileReaderStream

   with FileReaderStream("sample.ais") as stream:
       for msg in stream:
           if msg.tag_block is not None:
               msg.tag_block.init()
               print(msg.tag_block.asdict())
               # {'source_station': '2573135', 'receiver_timestamp': 1671620143, ...}

Create tag blocks with ``TagBlock.create(...)`` (returns bytes) or
``TagBlock.create_str(...)`` (returns str).

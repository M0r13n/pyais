###############################
Decode a single AIS message
###############################

You can decode AIVDM/AIVDO messages, as long as they are valid NMEA 0183 messages.

References
----------

* AIS: https://en.wikipedia.org/wiki/Automatic_identification_system
* NMEA 0183: https://en.wikipedia.org/wiki/NMEA_0183
* AIVDM/AIVDO protocol decoding reference: https://gpsd.gitlab.io/gpsd/AIVDM.html

Examples
--------

The newest version of Pyais introduced a more convinenient method to decode messages: `decode_msg`::

    from pyais import decode_msg
    decode_msg(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")
    # => {'type': 1, 'repeat': 0, 'mmsi': '366053209', 'status': <NavigationStatus.RestrictedManoeuverability: 3>, 'turn': 0, 'speed': 0.0, 'accuracy': 0, 'lon': -122.34161833333333, 'lat': 37.80211833333333, 'course': 219.3, 'heading': 1, 'second': 59, 'maneuver': <ManeuverIndicator.NotAvailable: 0>, 'raim': 0, 'radio': 2281}

    # or
    decode_msg("!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")
    # => {'type': 1, 'repeat': 0, 'mmsi': '366053209', 'status': <NavigationStatus.RestrictedManoeuverability: 3>, 'turn': 0, 'speed': 0.0, 'accuracy': 0, 'lon': -122.34161833333333, 'lat': 37.80211833333333, 'course': 219.3, 'heading': 1, 'second': 59, 'maneuver': <ManeuverIndicator.NotAvailable: 0>, 'raim': 0, 'radio': 2281}


    # or decode a multiline message
    decode_msg(
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
            b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
        )
    # => {'type': 5, 'repeat': 0, 'mmsi': '210035000', 'ais_version': 0, 'imo': 9514755, 'callsign': '5BXT2', 'shipname': 'NORDIC HAMBURG', 'shiptype': <ShipType.Cargo_HazardousCategory_A: 71>, 'to_bow': 142, 'to_stern': 10, 'to_port': 11, 'to_starboard': 11, 'epfd': <EpfdType.GPS: 1>, 'month': 7, 'day': 20, 'hour': 5, 'minute': 0, 'draught': 7.1, 'destination': 'CTT-LAYBY', 'dte': 0}


.. warning::

   **Please note**, that `decode_msg` is only meant to decode a single message.
   You **can not** use it to decode multiple messages at once.
   But it supports multiline messages


Decode a single message (bytes)::

    message = NMEAMessage(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")
    print(message.decode())
    # => {'type': 1, 'repeat': 0, 'mmsi': '366053209', 'status': <NavigationStatus.RestrictedManoeuverability: 3>, 'turn': 0, 'speed': 0.0, 'accuracy': 0, 'lon': -122.34161833333333, 'lat': 37.80211833333333, 'course': 219.3, 'heading': 1, 'second': 59, 'maneuver': <ManeuverIndicator.NotAvailable: 0>, 'raim': 0, 'radio': 2281}


Decode a single message (str)::

    message = NMEAMessage.from_string("!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")
    print(message.decode())
    # => {'type': 1, 'repeat': 0, 'mmsi': '366053209', 'status': <NavigationStatus.RestrictedManoeuverability: 3>, 'turn': 0, 'speed': 0.0, 'accuracy': 0, 'lon': -122.34161833333333, 'lat': 37.80211833333333, 'course': 219.3, 'heading': 1, 'second': 59, 'maneuver': <ManeuverIndicator.NotAvailable: 0>, 'raim': 0, 'radio': 2281}

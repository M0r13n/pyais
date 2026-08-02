import unittest

from pyais import decode
from pyais.encode import encode_dict, encode_msg, ais_to_nmea_0183
from pyais.util import SixBitNibleEncoder, to_six_bit
from pyais.messages import (
    MessageType8Default,
    MessageType8Dac1Fid0,
    MessageType8Dac1Fid11,
    MessageType8Dac1Fid16,
    MessageType8Dac1Fid17,
    MessageType8Dac1Fid19,
    MessageType8Dac1Fid20,
    MessageType8Dac1Fid21NonWmo,
    MessageType8Dac1Fid22,
    MessageType8Dac1Fid31,
)


def _twos(value: int, bits: int) -> str:
    """Render `value` as a `bits`-wide two's complement bit string."""
    if value < 0:
        value += 1 << bits
    return format(value & ((1 << bits) - 1), f'0{bits}b')


def _sixbit(text: str, chars: int) -> str:
    """Encode `text` as `chars` six-bit ASCII characters."""
    padded = text.ljust(chars, '@')[:chars]
    out = ''
    for ch in padded:
        c = ord(ch)
        out += format((c - 64) if c >= 64 else c, '06b')
    return out


def _pack_targets(targets) -> bytes:
    """Pack (id_type, target_id, lat, lon, course, second, speed) tuples.

    Mirrors IALA IFM 16 Table 44: 120 bits per record, coordinates in
    1/1000 minutes. `target_id` may be an int (MMSI/IMO) or a call sign str.
    """
    bits = ''
    for id_type, target_id, lat, lon, course, second, speed in targets:
        bits += _twos(id_type, 2)
        if isinstance(target_id, str):
            bits += _sixbit(target_id, 7)
        else:
            bits += _twos(target_id, 42)
        bits += '0' * 4  # spare
        bits += _twos(round(lat * 60000), 24)
        bits += _twos(round(lon * 60000), 25)
        bits += _twos(course, 9)
        bits += _twos(second, 6)
        bits += _twos(speed, 8)
    return int(bits, 2).to_bytes(len(bits) // 8, 'big') if bits else b''


def _to_sentences(bits: str):
    """Turn a bit string of any length into AIVDM sentence(s)."""
    padded = bits + '0' * (-len(bits) % 8)
    data = int(padded, 2).to_bytes(len(padded) // 8, 'big')
    payload, fill_bits = SixBitNibleEncoder().encode(data, len(bits))
    sentences = ais_to_nmea_0183(payload, 'AI', 'VDM', 'A', fill_bits)
    return [part.encode() for part in sentences]


def _area_notice_header(**over) -> str:
    """Pack the fixed 111-bit Area Notice header (IMO289 DAC=1/FID=22)."""
    bits = _twos(8, 6)                                  # Message Type
    bits += _twos(over.get('repeat', 0), 2)             # Repeat Indicator
    bits += _twos(over.get('mmsi', 366999707), 30)      # Source MMSI
    bits += '00'                                        # Spare
    bits += _twos(1, 10)                                # DAC
    bits += _twos(22, 6)                                # FID
    bits += _twos(over.get('linkage', 42), 10)          # Message Linkage ID
    bits += _twos(over.get('notice', 10), 7)            # Notice Description
    bits += _twos(over.get('month', 7), 4)              # Month (UTC)
    bits += _twos(over.get('day', 26), 5)               # Day (UTC)
    bits += _twos(over.get('hour', 14), 5)              # Hour (UTC)
    bits += _twos(over.get('minute', 27), 6)            # Minute (UTC)
    bits += _twos(over.get('duration', 120), 18)        # Duration in minutes
    assert len(bits) == 111
    return bits


def _sub_circle(lon, lat, radius, scale=0, precision=4) -> str:
    bits = _twos(0, 3) + _twos(scale, 2)
    bits += _twos(round(lon * 60000), 25) + _twos(round(lat * 60000), 24)
    bits += _twos(precision, 3) + _twos(radius, 12) + '0' * 18
    assert len(bits) == 87
    return bits


def _sub_rectangle(lon, lat, east, north, orientation, scale=0, precision=4) -> str:
    bits = _twos(1, 3) + _twos(scale, 2)
    bits += _twos(round(lon * 60000), 25) + _twos(round(lat * 60000), 24)
    bits += _twos(precision, 3) + _twos(east, 8) + _twos(north, 8)
    bits += _twos(orientation, 9) + '0' * 5
    assert len(bits) == 87
    return bits


def _sub_sector(lon, lat, radius, left, right, scale=0, precision=4) -> str:
    bits = _twos(2, 3) + _twos(scale, 2)
    bits += _twos(round(lon * 60000), 25) + _twos(round(lat * 60000), 24)
    bits += _twos(precision, 3) + _twos(radius, 12)
    bits += _twos(left, 9) + _twos(right, 9)
    assert len(bits) == 87
    return bits


def _sub_waypoints(shape, points, scale=0) -> str:
    """Polyline (shape 3) or polygon (shape 4): four (bearing, distance) pairs."""
    bits = _twos(shape, 3) + _twos(scale, 2)
    for bearing, distance in points:
        bits += _twos(bearing, 10) + _twos(distance, 10)
    bits += '00'
    assert len(bits) == 87
    return bits


def _sub_text(text) -> str:
    bits = _twos(5, 3) + _sixbit(text, 14)
    assert len(bits) == 87
    return bits


def _pack_sub_areas(bits: str) -> bytes:
    """Left-align a run of 87-bit sub-area records into whole bytes.

    87 is not a multiple of 8, so the records are padded on the right rather
    than truncated to a byte boundary.
    """
    padded = bits + '0' * (-len(bits) % 8)
    return int(padded, 2).to_bytes(len(padded) // 8, 'big')


# (id_type, target_id, lat, lon, course, second, speed)
_TARGET_A = (0, 211234560, 50.4321, 18.1234, 245, 33, 123)
_TARGET_B = (2, 'DEUTSCH', 54.3233, 10.1394, 90, 12, 8)
_TARGET_C = (1, 9074729, -33.85, -151.2, 359, 59, 254)


class MessageType8Tests(unittest.TestCase):

    def test_dac_1_fid_0_encode(self):
        encoded = encode_msg(MessageType8Dac1Fid0.create(
            mmsi=1010101010,
            text_sequence=1337,
            text="Foo Bar TEXT!!",
        ))
        self.assertEqual(
            encoded[0],
            "!AIVDO,1,1,,A,8?3Cc4P0@5>ASkp0PD`51F58H@,4*21"
        )

    def test_dac_1_fid_0_decode(self):
        decoded = decode(b"!AIVDO,1,1,,A,8?3Cc4P0@5>ASkp0PD`51F58H@,4*21")
        assert isinstance(decoded, MessageType8Dac1Fid0)
        self.assertEqual(decoded.mmsi, 1010101010)
        self.assertEqual(decoded.text, "FOO BAR TEXT!!")

    def test_dac_1_fid_11_encode(self):
        encoded = encode_dict({
            "accuracy": True,
            "airtemp": -102.4,
            "cdepth2": 31,
            "cdepth3": 31,
            "cdir": 360,
            "cdir2": 360,
            "cdir3": 360,
            "cspeed": 25.5,
            "cspeed2": 25.5,
            "cspeed3": 25.5,
            "dac": 1,
            "day": 19,
            "dewpoint": 50.1,
            "fid": 11,
            "hour": 14,
            "humidity": 101,
            "ice": 3,
            "lat": 59.66375,
            "leveltrend": 3,
            "lon": 18.931983,
            "minute": 12,
            "mmsi": 2655619,
            "msg_type": 8,
            "preciptype": 7,
            "pressure": 1310,
            "pressuretend": 3,
            "repeat": 1,
            "salinity": 51.0,
            "seastate": 13,
            "swelldir": 360,
            "swellheight": 25.5,
            "swellperiod": 63,
            "visgreater": True,
            "visibility": 1.1,
            "waterlevel": 30.01,
            "watertemp": 50.1,
            "wavedir": 360,
            "waveheight": 25.5,
            "waveperiod": 63,
            "wdir": 360,
            "wgust": 127,
            "wgustdir": 360,
            "wspeed": 127,
        })
        self.assertEqual(
            encoded[0],
            "!AIVDO,1,1,,A,8@2R5Ph0BkJOd@RbUto6Owu`e6F<eNws2tQwu`wsAwwe7wwvlOwu`nFOwd,2*49"
        )

    def test_dac_1_fid_11_decode(self):
        decoded = decode(b"!AIVDO,1,1,,A,8@2R5Ph0BkJOd@RbUto6Owu`e6F<eNws2tQwu`wsAwwe7wwvlOwu`nFOwd,2*49")
        assert isinstance(decoded, MessageType8Dac1Fid11)
        self.assertEqual(decoded.airtemp, 102.4)
        self.assertEqual(decoded.cdepth2, 31)
        self.assertEqual(decoded.cdepth3, 31)
        self.assertEqual(decoded.cdir, 360)
        self.assertEqual(decoded.cdir2, 360)
        self.assertEqual(decoded.cdir3, 360)
        self.assertEqual(decoded.cspeed, 25.5)
        self.assertEqual(decoded.cspeed2, 25.5)
        self.assertEqual(decoded.cspeed3, 25.5)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.day, 19)
        self.assertEqual(decoded.dewpoint, 50.1)
        self.assertEqual(decoded.fid, 11)
        self.assertEqual(decoded.hour, 14)
        self.assertEqual(decoded.humidity, 101)
        self.assertEqual(decoded.ice, 3)
        self.assertEqual(decoded.lat, 59.66375)
        self.assertEqual(decoded.leveltrend, 3)
        self.assertEqual(decoded.lon, 18.931983)
        self.assertEqual(decoded.minute, 12)
        self.assertEqual(decoded.mmsi, 2655619)
        self.assertEqual(decoded.msg_type, 8)
        self.assertEqual(decoded.preciptype, 7)
        self.assertEqual(decoded.pressure, 1310)
        self.assertEqual(decoded.pressuretend, 3)
        self.assertEqual(decoded.repeat, 1)
        self.assertEqual(decoded.salinity, 51.0)
        self.assertEqual(decoded.seastate, 13)
        self.assertEqual(decoded.swelldir, 360)
        self.assertEqual(decoded.swellheight, 25.5)
        self.assertEqual(decoded.swellperiod, 63)
        self.assertEqual(decoded.visibility, 1.1)
        self.assertEqual(decoded.waterlevel, 30.00)
        self.assertEqual(decoded.watertemp, 50.1)
        self.assertEqual(decoded.wavedir, 360)
        self.assertEqual(decoded.waveheight, 25.5)
        self.assertEqual(decoded.waveperiod, 63)
        self.assertEqual(decoded.wdir, 360)
        self.assertEqual(decoded.wgust, 127)
        self.assertEqual(decoded.wgustdir, 360)
        self.assertEqual(decoded.wspeed, 127)

    # ---------------------------------------------------------------
    # DAC=1, FID=16 -- IALA VTS targets (1 to 7 records of 120 bits)
    # ---------------------------------------------------------------

    def test_dac_1_fid_16_single_target(self):
        data = _pack_targets([_TARGET_A])
        encoded = encode_msg(MessageType8Dac1Fid16.create(mmsi=11223344, target_data=data))
        decoded = decode(encoded[0].encode())
        assert isinstance(decoded, MessageType8Dac1Fid16)
        self.assertEqual(decoded.mmsi, 11223344)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 16)
        self.assertEqual(len(decoded.targets), 1)
        self.assertEqual(decoded.targets[0], {
            'id_type': 0, 'target_id': 211234560, 'lat': 50.4321,
            'lon': 18.1234, 'course': 245, 'second': 33, 'speed': 123,
        })

    def test_dac_1_fid_16_seven_targets(self):
        targets = [_TARGET_A, _TARGET_B, _TARGET_C] + [_TARGET_A] * 4
        data = _pack_targets(targets)
        self.assertEqual(len(data), 7 * 15)
        encoded = encode_msg(MessageType8Dac1Fid16.create(mmsi=11223344, target_data=data))
        decoded = decode(*[part.encode() for part in encoded])
        assert isinstance(decoded, MessageType8Dac1Fid16)
        self.assertEqual(len(decoded.targets), 7)
        self.assertEqual(decoded.targets[0]['target_id'], 211234560)
        self.assertEqual(decoded.targets[1]['target_id'], 'DEUTSCH')
        self.assertEqual(decoded.targets[1]['id_type'], 2)
        self.assertEqual(decoded.targets[2]['lat'], -33.85)
        self.assertEqual(decoded.targets[2]['lon'], -151.2)

    def test_dac_1_fid_16_all_target_counts_round_trip(self):
        """1 through 7 targets must all survive an encode/decode round trip."""
        for count in range(1, 8):
            pool = [_TARGET_A, _TARGET_B, _TARGET_C] + [_TARGET_A] * 4
            data = _pack_targets(pool[:count])
            encoded = encode_msg(MessageType8Dac1Fid16.create(mmsi=11223344, target_data=data))
            decoded = decode(*[part.encode() for part in encoded])
            assert isinstance(decoded, MessageType8Dac1Fid16)
            self.assertEqual(len(decoded.targets), count, f"count={count}")

    def test_dac_1_fid_16_caps_at_seven_targets(self):
        """An over-long region must not yield more than seven targets."""
        data = _pack_targets([_TARGET_A] * 9)
        decoded_targets = MessageType8Dac1Fid16.create(
            mmsi=11223344, target_data=data
        ).targets
        self.assertEqual(len(decoded_targets), 7)

    def test_dac_1_fid_16_empty_and_partial_region(self):
        """No data, or a partial record, must not raise."""
        self.assertEqual(MessageType8Dac1Fid16.create(mmsi=1, target_data=b'').targets, [])
        partial = _pack_targets([_TARGET_A])[:10]
        self.assertEqual(MessageType8Dac1Fid16.create(mmsi=1, target_data=partial).targets, [])

    def test_dac_1_fid_16_not_available_sentinels(self):
        """Spec defaults: course 360, second 60, speed 255 survive decoding."""
        data = _pack_targets([(3, 0, 50.0, 18.0, 360, 60, 255)])
        target = MessageType8Dac1Fid16.create(mmsi=1, target_data=data).targets[0]
        self.assertEqual(target['course'], 360)
        self.assertEqual(target['second'], 60)
        self.assertEqual(target['speed'], 255)
        self.assertEqual(target['id_type'], 3)

    def test_dac_1_fid_17_encode(self):
        encoded = encode_msg(MessageType8Dac1Fid17.create(
            mmsi=11223344,
            target_data=b'\x00\xb4\x7f\xff\xfbG\xf8^\xc2\xd0L\x00\x05\x10\x0b\x8b\x01\x82\x12\xf4Z \x06W\xd8\xf5\x85\xec\x16\x88\x01\x95\xf6=a',
        ))
        self.assertEqual(
            encoded[0],
            "!AIVDO,1,1,,A,80:e1<00D@2lOwwsAwQNhe1<00D@2pd1PQ;lFR06EuSmQNhFR06EuSmQ,0*52"
        )

    def test_dac_1_fid_17_decode(self):
        decoded = decode(b"!AIVDO,1,1,,A,80:e1<00D@2lOwwsAwQNhe1<00D@2pd1PQ;lFR06EuSmQNhFR06EuSmQ,0*52")
        assert isinstance(decoded, MessageType8Dac1Fid17)
        self.assertEqual(len(decoded.targets), 2)
        self.assertEqual(decoded.targets[0], {'id': '@-G??>4', 'lat': -8.33383, 'lon': -104.20907, 'course': 20, 'speed': 11})
        self.assertEqual(decoded.targets[1], {'id': 'K@XHR=E', 'lat': 34.97958, 'lon': -85.28622, 'speed': 136, 'course': 432})

    # ---------------------------------------------------------------
    # DAC=1, FID=19 -- Marine Traffic Signal (IMO289), fixed 360 bits
    # ---------------------------------------------------------------

    def test_dac_1_fid_19_encode(self):
        encoded = encode_dict({
            "msg_type": 8,
            "repeat": 0,
            "mmsi": 2655619,
            "dac": 1,
            "fid": 19,
            "linkage": 337,
            "station": "KIEL HOLTENAU",
            "lon": 9.9576,
            "lat": 54.3661,
            "status": 1,
            "signal": 3,
            "hour": 14,
            "minute": 27,
            "nextsignal": 4,
        })
        self.assertEqual(len(encoded), 1)
        self.assertEqual(
            encoded[0],
            "!AIVDO,1,1,,A,802R5Ph0DmA;95<P8?<D5>1E000000018s`6><78o=T00000000000000000,0*65"
        )

    def test_dac_1_fid_19_decode(self):
        decoded = decode(b"!AIVDM,1,1,,A,802R5Ph0DmA;95<P8?<D5>1E000000018s`6><78o=T00000000000000000,0*67")
        assert isinstance(decoded, MessageType8Dac1Fid19)
        self.assertEqual(decoded.msg_type, 8)
        self.assertEqual(decoded.repeat, 0)
        self.assertEqual(decoded.mmsi, 2655619)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 19)
        self.assertEqual(decoded.linkage, 337)
        self.assertEqual(decoded.station, "KIEL HOLTENAU")
        self.assertEqual(decoded.lon, 9.9576)
        self.assertEqual(decoded.lat, 54.3661)
        self.assertEqual(decoded.status, 1)
        self.assertEqual(decoded.signal, 3)
        self.assertEqual(decoded.hour, 14)
        self.assertEqual(decoded.minute, 27)
        self.assertEqual(decoded.nextsignal, 4)

    def test_dac_1_fid_19_bit_layout_matches_spec(self):
        """Hand-pack the 360 bits per the IALA table and decode them.

        This is deliberately not a round trip: it pins the field offsets and
        widths against the specification independently of pyais' encoder.
        """
        bits = ''
        bits += _twos(8, 6)                                    # Message ID
        bits += _twos(0, 2)                                    # Repeat Indicator
        bits += _twos(2655619, 30)                             # Source ID
        bits += _twos(0, 2)                                    # Spare
        bits += _twos(1, 10)                                   # DAC
        bits += _twos(19, 6)                                   # FI
        bits += _twos(337, 10)                                 # Message Linkage ID
        station = "KIEL HOLTENAU".ljust(20, '@')
        bits += ''.join(to_six_bit(c) for c in station)     # Name of Signal Station
        bits += _twos(round(9.9576 * 60000), 25)               # Longitude
        bits += _twos(round(54.3661 * 60000), 24)              # Latitude
        bits += _twos(1, 2)                                    # Status of Signal
        bits += _twos(3, 5)                                    # Signal in Service
        bits += _twos(14, 5)                                   # UTC Hour
        bits += _twos(27, 6)                                   # UTC Minute
        bits += _twos(4, 5)                                    # Expected Next Signal
        bits += _twos(0, 102)                                  # Spare
        self.assertEqual(len(bits), 360)

        data = int(bits, 2).to_bytes(len(bits) // 8, 'big')
        payload, fill_bits = SixBitNibleEncoder().encode(data, len(bits))
        sentences = ais_to_nmea_0183(payload, 'AI', 'VDM', 'A', fill_bits)
        decoded = decode(*[part.encode() for part in sentences])

        assert isinstance(decoded, MessageType8Dac1Fid19)
        self.assertEqual(decoded.linkage, 337)
        self.assertEqual(decoded.station, "KIEL HOLTENAU")
        self.assertEqual(decoded.lon, 9.9576)
        self.assertEqual(decoded.lat, 54.3661)
        self.assertEqual(decoded.status, 1)
        self.assertEqual(decoded.signal, 3)
        self.assertEqual(decoded.hour, 14)
        self.assertEqual(decoded.minute, 27)
        self.assertEqual(decoded.nextsignal, 4)

    def test_dac_1_fid_19_southern_western_hemisphere(self):
        """Negative coordinates use 2's complement across 25/24 bit fields."""
        encoded = encode_dict({
            "msg_type": 8, "mmsi": 2655619, "dac": 1, "fid": 19,
            "lon": -70.6483, "lat": -33.4569, "status": 2, "signal": 13,
        })
        decoded = decode(*[part.encode() for part in encoded])
        assert isinstance(decoded, MessageType8Dac1Fid19)
        self.assertEqual(decoded.lon, -70.6483)
        self.assertEqual(decoded.lat, -33.4569)
        self.assertEqual(decoded.status, 2)
        self.assertEqual(decoded.signal, 13)

    def test_dac_1_fid_19_not_available_defaults(self):
        """Spec defaults: linkage 0, hour 24, minute 60, status/signal 0."""
        encoded = encode_dict({"msg_type": 8, "mmsi": 2655619, "dac": 1, "fid": 19})
        decoded = decode(*[part.encode() for part in encoded])
        assert isinstance(decoded, MessageType8Dac1Fid19)
        self.assertEqual(decoded.linkage, 0)
        self.assertEqual(decoded.hour, 24)
        self.assertEqual(decoded.minute, 60)
        self.assertEqual(decoded.status, 0)
        self.assertEqual(decoded.signal, 0)
        self.assertEqual(decoded.nextsignal, 0)
        self.assertEqual(decoded.station, "")

    def test_dac_1_fid_19_station_name_truncated_to_20_chars(self):
        """The station name field holds at most 20 six-bit characters."""
        encoded = encode_dict({
            "msg_type": 8, "mmsi": 2655619, "dac": 1, "fid": 19,
            "station": "A" * 30,
        })
        decoded = decode(*[part.encode() for part in encoded])
        assert isinstance(decoded, MessageType8Dac1Fid19)
        self.assertEqual(decoded.station, "A" * 20)

    # ---------------------------------------------------------------
    # DAC=1, FID=20 -- Berthing data (IMO289), fixed 328 bits
    # ---------------------------------------------------------------

    def test_dac_1_fid_20_encode(self):
        encoded = encode_dict({
            "msg_type": 8,
            "repeat": 0,
            "mmsi": 2655619,
            "dac": 1,
            "fid": 20,
            "linkage": 42,
            "berth_length": 300,
            "berth_depth": 12.5,
            "position": 1,
            "month": 7,
            "day": 26,
            "hour": 14,
            "minute": 27,
            "availability": True,
            "agent": 1,
            "fuel": 2,
            "water": 1,
            "tugs": 1,
            "hazardouswaste": 3,
            "berth_name": "KIEL OSTUFERHAFEN",
            "berth_lon": 10.1394,
            "berth_lat": 54.3233,
        })
        self.assertEqual(len(encoded), 1)
        self.assertEqual(
            encoded[0],
            "!AIVDO,1,1,,A,802R5Ph0E0bUSrGlqfh20008H01I8aT1rJR`hbA08hah0009B6hig0H,2*09"
        )

    def test_dac_1_fid_20_decode(self):
        decoded = decode(b"!AIVDM,1,1,,A,802R5Ph0E0bUSrGlqfh20008H01I8aT1rJR`hbA08hah0009B6hig0H,2*0B")
        assert isinstance(decoded, MessageType8Dac1Fid20)
        self.assertEqual(decoded.msg_type, 8)
        self.assertEqual(decoded.repeat, 0)
        self.assertEqual(decoded.mmsi, 2655619)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 20)
        self.assertEqual(decoded.linkage, 42)
        self.assertEqual(decoded.berth_length, 300)
        self.assertEqual(decoded.berth_depth, 12.5)
        self.assertEqual(decoded.position, 1)
        self.assertEqual(decoded.month, 7)
        self.assertEqual(decoded.day, 26)
        self.assertEqual(decoded.hour, 14)
        self.assertEqual(decoded.minute, 27)
        self.assertTrue(decoded.availability)
        self.assertEqual(decoded.agent, 1)
        self.assertEqual(decoded.fuel, 2)
        self.assertEqual(decoded.water, 1)
        self.assertEqual(decoded.tugs, 1)
        self.assertEqual(decoded.hazardouswaste, 3)
        self.assertEqual(decoded.berth_name, "KIEL OSTUFERHAFEN")
        self.assertEqual(decoded.berth_lon, 10.1394)
        self.assertEqual(decoded.berth_lat, 54.3233)

    def test_dac_1_fid_20_bit_layout_matches_spec(self):
        """Hand-pack the 328 bits per the IMO289 table and decode them.

        The application block is identical to the addressed Message 6 variant
        (bits 88-359 there); here it sits behind the 56 bit Message 8 header.
        This is deliberately not a round trip: it pins the field offsets and
        widths against the specification independently of pyais' encoder.
        """
        bits = ''
        bits += _twos(8, 6)                                    # Message ID
        bits += _twos(0, 2)                                    # Repeat Indicator
        bits += _twos(2655619, 30)                             # Source ID
        bits += _twos(0, 2)                                    # Spare
        bits += _twos(1, 10)                                   # DAC
        bits += _twos(20, 6)                                   # FI
        bits += _twos(42, 10)                                  # Message Linkage ID
        bits += _twos(300, 9)                                  # Berth length
        bits += _twos(125, 8)                                  # Berth water depth (0.1m)
        bits += _twos(1, 3)                                    # Mooring position
        bits += _twos(7, 4)                                    # UTC Month
        bits += _twos(26, 5)                                   # UTC Day
        bits += _twos(14, 5)                                   # UTC Hour
        bits += _twos(27, 6)                                   # UTC Minute
        bits += _twos(1, 1)                                    # Services availability
        services = [
            1,  # agent
            2,  # fuel
            0,  # chandler
            0,  # stevedore
            0,  # electrical
            1,  # water
            0,  # customs
            0,  # cartage
            0,  # crane
            0,  # lift
            0,  # medical
            0,  # navrepair
            0,  # provisions
            0,  # shiprepair
            0,  # surveyor
            0,  # steam
            1,  # tugs
            0,  # solidwaste
            0,  # liquidwaste
            3,  # hazardouswaste
            0,  # ballast
            0,  # additional
            0,  # regional1
            0,  # regional2
            0,  # future1
            0,  # future2
        ]
        self.assertEqual(len(services), 26)
        for service in services:
            bits += _twos(service, 2)
        name = "KIEL OSTUFERHAFEN".ljust(20, '@')
        bits += ''.join(to_six_bit(c) for c in name)           # Name of berth
        bits += _twos(round(10.1394 * 60000), 25)              # Longitude
        bits += _twos(round(54.3233 * 60000), 24)              # Latitude
        self.assertEqual(len(bits), 328)

        data = int(bits, 2).to_bytes(len(bits) // 8, 'big')
        payload, fill_bits = SixBitNibleEncoder().encode(data, len(bits))
        sentences = ais_to_nmea_0183(payload, 'AI', 'VDM', 'A', fill_bits)
        decoded = decode(*[part.encode() for part in sentences])

        assert isinstance(decoded, MessageType8Dac1Fid20)
        self.assertEqual(decoded.linkage, 42)
        self.assertEqual(decoded.berth_length, 300)
        self.assertEqual(decoded.berth_depth, 12.5)
        self.assertEqual(decoded.position, 1)
        self.assertEqual(decoded.month, 7)
        self.assertEqual(decoded.day, 26)
        self.assertEqual(decoded.hour, 14)
        self.assertEqual(decoded.minute, 27)
        self.assertTrue(decoded.availability)
        self.assertEqual(decoded.agent, 1)
        self.assertEqual(decoded.fuel, 2)
        self.assertEqual(decoded.water, 1)
        self.assertEqual(decoded.tugs, 1)
        self.assertEqual(decoded.hazardouswaste, 3)
        self.assertEqual(decoded.berth_name, "KIEL OSTUFERHAFEN")
        self.assertEqual(decoded.berth_lon, 10.1394)
        self.assertEqual(decoded.berth_lat, 54.3233)

    def test_dac_1_fid_20_southern_western_hemisphere(self):
        """Negative coordinates use 2's complement across 25/24 bit fields."""
        encoded = encode_dict({
            "msg_type": 8, "mmsi": 2655619, "dac": 1, "fid": 20,
            "berth_lon": -70.6483, "berth_lat": -33.4569, "position": 5,
        })
        decoded = decode(*[part.encode() for part in encoded])
        assert isinstance(decoded, MessageType8Dac1Fid20)
        self.assertEqual(decoded.berth_lon, -70.6483)
        self.assertEqual(decoded.berth_lat, -33.4569)
        self.assertEqual(decoded.position, 5)

    def test_dac_1_fid_20_not_available_defaults(self):
        """Spec defaults: hour 24, minute 60, everything else zero/empty."""
        encoded = encode_dict({"msg_type": 8, "mmsi": 2655619, "dac": 1, "fid": 20})
        decoded = decode(*[part.encode() for part in encoded])
        assert isinstance(decoded, MessageType8Dac1Fid20)
        self.assertEqual(decoded.linkage, 0)
        self.assertEqual(decoded.berth_length, 0)
        self.assertEqual(decoded.berth_depth, 0)
        self.assertEqual(decoded.position, 0)
        self.assertEqual(decoded.month, 0)
        self.assertEqual(decoded.day, 0)
        self.assertEqual(decoded.hour, 24)
        self.assertEqual(decoded.minute, 60)
        self.assertFalse(decoded.availability)
        self.assertEqual(decoded.berth_name, "")
        self.assertEqual(decoded.berth_lon, 0)
        self.assertEqual(decoded.berth_lat, 0)

    def test_dac_1_fid_20_all_service_fields_round_trip(self):
        """All 26 two-bit service fields are addressable and independent."""
        names = [
            'agent', 'fuel', 'chandler', 'stevedore', 'electrical', 'water',
            'customs', 'cartage', 'crane', 'lift', 'medical', 'navrepair',
            'provisions', 'shiprepair', 'surveyor', 'steam', 'tugs',
            'solidwaste', 'liquidwaste', 'hazardouswaste', 'ballast',
            'additional', 'regional1', 'regional2', 'future1', 'future2',
        ]
        # cycle through the four service status codes: 0, 1, 2, 3, 0, ...
        values = {name: i % 4 for i, name in enumerate(names)}
        message = {"msg_type": 8, "mmsi": 2655619, "dac": 1, "fid": 20, "availability": True}
        message.update(values)

        encoded = encode_dict(message)
        decoded = decode(*[part.encode() for part in encoded])
        assert isinstance(decoded, MessageType8Dac1Fid20)
        self.assertTrue(decoded.availability)
        for name, value in values.items():
            self.assertEqual(getattr(decoded, name), value, name)

    def test_dac_1_fid_20_berth_name_truncated_to_20_chars(self):
        """The berth name field holds at most 20 six-bit characters."""
        encoded = encode_dict({
            "msg_type": 8, "mmsi": 2655619, "dac": 1, "fid": 20,
            "berth_name": "B" * 30,
        })
        decoded = decode(*[part.encode() for part in encoded])
        assert isinstance(decoded, MessageType8Dac1Fid20)
        self.assertEqual(decoded.berth_name, "B" * 20)

    def test_dac_1_fid_20_extremes(self):
        """Sentinel/maximum values for the length and depth fields."""
        encoded = encode_dict({
            "msg_type": 8, "mmsi": 2655619, "dac": 1, "fid": 20,
            "berth_length": 511, "berth_depth": 25.5,
        })
        decoded = decode(*[part.encode() for part in encoded])
        assert isinstance(decoded, MessageType8Dac1Fid20)
        self.assertEqual(decoded.berth_length, 511)
        self.assertEqual(decoded.berth_depth, 25.5)

    # ---------------------------------------------------------------
    # DAC=1, FID=21 -- Weather observation report from ship (IMO289)
    # ---------------------------------------------------------------

    def test_dac_1_fid_21_encode(self):
        encoded = encode_dict({
            "msg_type": 8,
            "repeat": 0,
            "mmsi": 2655619,
            "dac": 1,
            "fid": 21,
            "location": "KIEL LIGHTSHIP",
            "lon": 10.1394,
            "lat": 54.3233,
            "day": 26,
            "hour": 14,
            "minute": 27,
            "weather": 2,
            "vislimit": True,
            "visibility": 8.4,
            "humidity": 78,
            "wspeed": 22,
            "wdir": 270,
            "pressure": 1013,
            "pressuretend": 5,
            "airtemp": 18.3,
            "watertemp": 16.7,
            "waveperiod": 7,
            "waveheight": 1.4,
            "wavedir": 280,
            "swellheight": 0.8,
            "swelldir": 300,
            "swellperiod": 9,
        })
        self.assertEqual(len(encoded), 1)
        self.assertEqual(
            encoded[0],
            "!AIVDO,1,1,,A,802R5Ph0EAI8aT1Q8q2RI1:00000009B6hig0KCVjm9iJ7=IAKU>>7AP8UQ8,0*6C"
        )

    def test_dac_1_fid_21_decode(self):
        decoded = decode(b"!AIVDM,1,1,,A,802R5Ph0EAI8aT1Q8q2RI1:00000009B6hig0KCVjm9iJ7=EAK`F>7AP8UQ8,0*2F")
        assert isinstance(decoded, MessageType8Dac1Fid21NonWmo)
        self.assertEqual(decoded.msg_type, 8)
        self.assertEqual(decoded.mmsi, 2655619)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 21)
        self.assertFalse(decoded.wmo)
        self.assertEqual(decoded.location, "KIEL LIGHTSHIP")
        self.assertEqual(decoded.lon, 10.1394)
        self.assertEqual(decoded.lat, 54.3233)
        self.assertEqual(decoded.day, 26)
        self.assertEqual(decoded.hour, 14)
        self.assertEqual(decoded.minute, 27)
        self.assertEqual(decoded.weather, 2)
        self.assertTrue(decoded.vislimit)
        self.assertEqual(decoded.visibility, 8.4)
        self.assertEqual(decoded.humidity, 78)
        self.assertEqual(decoded.wspeed, 22)
        self.assertEqual(decoded.wdir, 270)
        self.assertEqual(decoded.pressure, 1012)
        self.assertEqual(decoded.pressuretend, 5)
        self.assertEqual(decoded.airtemp, 18.3)
        self.assertEqual(decoded.watertemp, 26.7)
        self.assertEqual(decoded.waveperiod, 7)
        self.assertEqual(decoded.waveheight, 1.4)
        self.assertEqual(decoded.wavedir, 280)
        self.assertEqual(decoded.swellheight, 0.8)
        self.assertEqual(decoded.swelldir, 300)
        self.assertEqual(decoded.swellperiod, 9)

    def test_dac_1_fid_21_bit_layout_matches_spec(self):
        """Hand-pack the 360 bits per the IMO289 non-WMO table and decode them.

        This is deliberately not a round trip: it pins the field offsets and
        widths against the specification independently of pyais' encoder.
        """
        bits = ''
        bits += _twos(8, 6)                                    # Message ID
        bits += _twos(0, 2)                                    # Repeat Indicator
        bits += _twos(2655619, 30)                             # Source ID
        bits += _twos(0, 2)                                    # Spare
        bits += _twos(1, 10)                                   # DAC
        bits += _twos(21, 6)                                   # FI
        bits += _twos(0, 1)                                    # Variant (WMO bit)
        location = "KIEL LIGHTSHIP".ljust(20, '@')
        bits += ''.join(to_six_bit(c) for c in location)       # Location
        bits += _twos(round(10.1394 * 60000), 25)              # Longitude
        bits += _twos(round(54.3233 * 60000), 24)              # Latitude
        bits += _twos(26, 5)                                   # UTC Day
        bits += _twos(14, 5)                                   # UTC Hour
        bits += _twos(27, 6)                                   # UTC Minute
        bits += _twos(2, 4)                                    # Present Weather
        bits += _twos(1, 1)                                    # Visibility Limit
        bits += _twos(84, 7)                                   # Horiz. Visibility (0.1nm)
        bits += _twos(78, 7)                                   # Relative Humidity
        bits += _twos(22, 7)                                   # Average Wind Speed
        bits += _twos(270, 9)                                  # Wind Direction
        bits += _twos(1013 - 800, 9)                           # Air Pressure (offset 800)
        bits += _twos(5, 4)                                    # Pressure Tendency
        bits += _twos(183, 11)                                 # Air Temperature (0.1C)
        bits += _twos(round((16.7 + 10.0) / 0.1), 10)          # Water Temperature
        bits += _twos(7, 6)                                    # Wave period
        bits += _twos(14, 8)                                   # Wave height (0.1m)
        bits += _twos(280, 9)                                  # Wave direction
        bits += _twos(8, 8)                                    # Swell height (0.1m)
        bits += _twos(300, 9)                                  # Swell direction
        bits += _twos(9, 6)                                    # Swell period
        bits += _twos(0, 3)                                    # Spare
        self.assertEqual(len(bits), 360)

        data = int(bits, 2).to_bytes(len(bits) // 8, 'big')
        payload, fill_bits = SixBitNibleEncoder().encode(data, len(bits))
        sentences = ais_to_nmea_0183(payload, 'AI', 'VDM', 'A', fill_bits)
        decoded = decode(*[part.encode() for part in sentences])

        assert isinstance(decoded, MessageType8Dac1Fid21NonWmo)
        self.assertEqual(decoded.location, "KIEL LIGHTSHIP")
        self.assertEqual(decoded.lon, 10.1394)
        self.assertEqual(decoded.lat, 54.3233)
        self.assertEqual(decoded.weather, 2)
        self.assertTrue(decoded.vislimit)
        self.assertEqual(decoded.visibility, 8.4)
        self.assertEqual(decoded.humidity, 78)
        self.assertEqual(decoded.wspeed, 22)
        self.assertEqual(decoded.wdir, 270)
        self.assertEqual(decoded.pressure, 1012)
        self.assertEqual(decoded.pressuretend, 5)
        self.assertEqual(decoded.airtemp, 18.3)
        self.assertEqual(decoded.watertemp, 26.7)
        self.assertEqual(decoded.waveheight, 1.4)
        self.assertEqual(decoded.swellheight, 0.8)
        self.assertEqual(decoded.swellperiod, 9)

    def test_dac_1_fid_21_wmo_variant_falls_back_to_default(self):
        """Bit 56 set selects the WMO BUFR layout, which is not decoded.

        Rather than mis-reading it against the non-WMO field offsets, the
        payload must come back as MessageType8Default with raw `data`.
        """
        bits = ''
        bits += _twos(8, 6)
        bits += _twos(0, 2)
        bits += _twos(2655619, 30)
        bits += _twos(0, 2)
        bits += _twos(1, 10)
        bits += _twos(21, 6)
        bits += _twos(1, 1)                                    # Variant (WMO bit) set
        bits += _twos(0, 303)                                  # WMO body, not decoded
        self.assertEqual(len(bits), 360)

        data = int(bits, 2).to_bytes(len(bits) // 8, 'big')
        payload, fill_bits = SixBitNibleEncoder().encode(data, len(bits))
        sentences = ais_to_nmea_0183(payload, 'AI', 'VDM', 'A', fill_bits)
        decoded = decode(*[part.encode() for part in sentences])

        self.assertNotIsInstance(decoded, MessageType8Dac1Fid21NonWmo)
        assert isinstance(decoded, MessageType8Default)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 21)
        self.assertTrue(decoded.data)

    def test_dac_1_fid_21_negative_temperatures(self):
        """Test with negative temperatures"""
        encoded = encode_dict({
            "msg_type": 8, "mmsi": 2655619, "dac": 1, "fid": 21,
            "airtemp": -12.4, "watertemp": -3.5,
            "lon": -70.6483, "lat": -33.4569,
        })
        decoded = decode(*[part.encode() for part in encoded])
        assert isinstance(decoded, MessageType8Dac1Fid21NonWmo)
        self.assertEqual(decoded.airtemp, -12.4)
        self.assertEqual(decoded.watertemp, -3.5)
        self.assertEqual(decoded.lon, -70.6483)
        self.assertEqual(decoded.lat, -33.4569)

    def test_dac_1_fid_21_pressure_range_round_trips(self):
        """The documented 800-1200 hPa range fits the 9 bit field."""
        for hpa in (800, 900, 1013, 1200):
            encoded = encode_dict({
                "msg_type": 8, "mmsi": 2655619, "dac": 1, "fid": 21,
                "pressure": hpa,
            })
            decoded = decode(*[part.encode() for part in encoded])
            assert isinstance(decoded, MessageType8Dac1Fid21NonWmo)
            self.assertEqual(decoded.pressure, hpa)

    def test_dac_1_fid_21_not_available_defaults(self):
        """Spec defaults: hour 24, minute 60, weather 8, humidity/wspeed 127."""
        encoded = encode_dict({"msg_type": 8, "mmsi": 2655619, "dac": 1, "fid": 21})
        decoded = decode(*[part.encode() for part in encoded])
        assert isinstance(decoded, MessageType8Dac1Fid21NonWmo)
        self.assertFalse(decoded.wmo)
        self.assertEqual(decoded.location, "")
        self.assertEqual(decoded.day, 0)
        self.assertEqual(decoded.hour, 24)
        self.assertEqual(decoded.minute, 60)
        self.assertEqual(decoded.weather, 8)
        self.assertFalse(decoded.vislimit)
        self.assertEqual(decoded.humidity, 127)
        self.assertEqual(decoded.wspeed, 127)
        self.assertEqual(decoded.wdir, 360)
        self.assertEqual(decoded.pressuretend, 15)
        self.assertEqual(decoded.waveperiod, 63)
        self.assertEqual(decoded.wavedir, 360)
        self.assertEqual(decoded.swelldir, 360)
        self.assertEqual(decoded.swellperiod, 63)

    def test_dac_1_fid_21_location_truncated_to_20_chars(self):
        """The location field holds at most 20 six-bit characters."""
        encoded = encode_dict({
            "msg_type": 8, "mmsi": 2655619, "dac": 1, "fid": 21,
            "location": "C" * 30,
        })
        decoded = decode(*[part.encode() for part in encoded])
        assert isinstance(decoded, MessageType8Dac1Fid21NonWmo)
        self.assertEqual(decoded.location, "C" * 20)

    def test_dac_1_fid_31_encode(self):
        encoded = encode_dict({
            "accuracy": True,
            "airtemp": -102.4,
            "cdepth2": 31,
            "cdepth3": 31,
            "cdir": 360,
            "cdir2": 360,
            "cdir3": 360,
            "cspeed": 25.5,
            "cspeed2": 25.5,
            "cspeed3": 25.5,
            "dac": 1,
            "day": 19,
            "dewpoint": 50.1,
            "fid": 31,
            "hour": 14,
            "humidity": 101,
            "ice": 3,
            "lat": 59.66375,
            "leveltrend": 3,
            "lon": 18.931983,
            "minute": 12,
            "mmsi": 2655619,
            "msg_type": 8,
            "preciptype": 7,
            "pressure": 1310,
            "pressuretend": 3,
            "repeat": 1,
            "salinity": 51.0,
            "seastate": 13,
            "swelldir": 360,
            "swellheight": 25.5,
            "swellperiod": 63,
            "visgreater": True,
            "visibility": 1.1,
            "waterlevel": 30.01,
            "watertemp": 50.1,
            "wavedir": 360,
            "waveheight": 25.5,
            "waveperiod": 63,
            "wdir": 360,
            "wgust": 127,
            "wgustdir": 360,
            "wspeed": 127,
        })

        self.assertEqual(
            encoded[0],
            "!AIVDO,1,1,,A,8@2R5Ph0GhRbUqe?n>KS?wvlFR06EuOwiOl?wnSwe7wvlOwwsAwwnSGmwvh,4*10"
        )

    def test_dac_1_fid_31_decode(self):
        decoded = decode(b"!AIVDM,1,1,0,A,8@2R5Ph0GhRbUqe?n>KS?wvlFR06EuOwiOl?wnSwe7wvlOwwsAwwnSGmwvwt,0*4E")
        assert isinstance(decoded, MessageType8Dac1Fid31)
        self.assertEqual(decoded.accuracy, True)
        self.assertEqual(decoded.airtemp, -102.4)
        self.assertEqual(decoded.cdepth2, 31)
        self.assertEqual(decoded.cdepth3, 31)
        self.assertEqual(decoded.cdir, 360)
        self.assertEqual(decoded.cdir2, 360)
        self.assertEqual(decoded.cdir3, 360)
        self.assertEqual(decoded.cspeed, 25.5)
        self.assertEqual(decoded.cspeed2, 25.5)
        self.assertEqual(decoded.cspeed3, 25.5)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.day, 19)
        self.assertEqual(decoded.dewpoint, 50.1)
        self.assertEqual(decoded.fid, 31)
        self.assertEqual(decoded.hour, 14)
        self.assertEqual(decoded.humidity, 101)
        self.assertEqual(decoded.ice, 3)
        self.assertEqual(decoded.lat, 59.66375)
        self.assertEqual(decoded.leveltrend, 3)
        self.assertEqual(decoded.lon, 18.931983)
        self.assertEqual(decoded.minute, 12)
        self.assertEqual(decoded.mmsi, 2655619)
        self.assertEqual(decoded.msg_type, 8)
        self.assertEqual(decoded.preciptype, 7)
        self.assertEqual(decoded.pressure, 1310)
        self.assertEqual(decoded.pressuretend, 3)
        self.assertEqual(decoded.repeat, 1)
        self.assertEqual(decoded.salinity, 51.0)
        self.assertEqual(decoded.seastate, 13)
        self.assertEqual(decoded.swelldir, 360)
        self.assertEqual(decoded.swellheight, 25.5)
        self.assertEqual(decoded.swellperiod, 63)
        self.assertEqual(decoded.visgreater, True)
        self.assertEqual(decoded.visibility, 1.1)
        self.assertEqual(decoded.waterlevel, 30.01)
        self.assertEqual(decoded.watertemp, 50.1)
        self.assertEqual(decoded.wavedir, 360)
        self.assertEqual(decoded.waveheight, 25.5)
        self.assertEqual(decoded.waveperiod, 63)
        self.assertEqual(decoded.wdir, 360)
        self.assertEqual(decoded.wgust, 127)
        self.assertEqual(decoded.wgustdir, 360)
        self.assertEqual(decoded.wspeed, 127)


class MessageType8Dac1Fid22Tests(unittest.TestCase):
    """IMO289 Area Notice (broadcast). DAC=1, FID=22."""

    def test_real_world_right_whale_notice(self):
        """A real NOAA right whale area notice: one circle sub-area.

        Notice 0 is "Caution Area: Marine mammals habitat" and the radius is
        926 at scale factor 1, i.e. 9260 m, which is exactly 5 nautical miles.
        """
        decoded = decode(b"!AIVDM,1,1,,B,803Ovrh0EP:024`@02PN04da=3V<>N0000,4*39")

        assert isinstance(decoded, MessageType8Dac1Fid22)
        self.assertEqual(decoded.msg_type, 8)
        self.assertEqual(decoded.repeat, 0)
        self.assertEqual(decoded.mmsi, 3669739)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 22)
        self.assertEqual(decoded.linkage, 10)
        self.assertEqual(decoded.notice, 0)
        self.assertEqual(decoded.month, 1)
        self.assertEqual(decoded.day, 1)
        self.assertEqual(decoded.hour, 5)
        self.assertEqual(decoded.minute, 2)
        self.assertEqual(decoded.duration, 20)

        self.assertEqual(len(decoded.sub_areas), 1)
        self.assertEqual(decoded.sub_areas[0], {
            'shape': 0,
            'scale': 1,
            'lon': -69.86498,
            'lat': 42.08295,
            'precision': 4,
            'radius': 9260,
        })

    def test_bit_layout_matches_spec(self):
        """Hand-pack the header plus one sub-area of every shape."""
        bits = _area_notice_header()
        bits += _sub_circle(-70.8, 42.3, radius=250, scale=1)
        bits += _sub_rectangle(-70.9, 42.2, east=200, north=150, orientation=45)
        bits += _sub_sector(-70.7, 42.4, radius=1000, left=30, right=120)
        bits += _sub_waypoints(3, [(90, 500), (180, 300), (720, 0), (720, 0)])
        bits += _sub_waypoints(4, [(0, 100), (180, 100), (360, 100), (540, 100)])
        bits += _sub_text("DIVERS DOWN")
        # 111-bit header + 6 sub-areas of 87 bits
        self.assertEqual(len(bits), 111 + 6 * 87)

        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid22)
        self.assertEqual(decoded.mmsi, 366999707)
        self.assertEqual(decoded.linkage, 42)
        self.assertEqual(decoded.notice, 10)  # Caution Area: Divers down
        self.assertEqual(decoded.month, 7)
        self.assertEqual(decoded.day, 26)
        self.assertEqual(decoded.hour, 14)
        self.assertEqual(decoded.minute, 27)
        self.assertEqual(decoded.duration, 120)

        areas = decoded.sub_areas
        self.assertEqual(len(areas), 6)

        # Circle: radius is scaled by 10^scale, so 250 at scale 1 is 2500 m.
        self.assertEqual(areas[0], {
            'shape': 0, 'scale': 1, 'lon': -70.8, 'lat': 42.3,
            'precision': 4, 'radius': 2500,
        })
        self.assertEqual(areas[1], {
            'shape': 1, 'scale': 0, 'lon': -70.9, 'lat': 42.2,
            'precision': 4, 'east': 200, 'north': 150, 'orientation': 45,
        })
        self.assertEqual(areas[2], {
            'shape': 2, 'scale': 0, 'lon': -70.7, 'lat': 42.4,
            'precision': 4, 'radius': 1000, 'left': 30, 'right': 120,
        })
        # Bearings are half-degree steps, so 90 raw is 45 degrees.
        self.assertEqual(areas[3], {
            'shape': 3, 'scale': 0, 'points': [
                {'angle': 90.0, 'bearing': 45.0, 'distance': 500},
                {'angle': 180.0, 'bearing': 90.0, 'distance': 300},
                {'angle': 720.0, 'bearing': 360.0, 'distance': 0},   # 720 = N/A
                {'angle': 720.0, 'bearing': 360.0, 'distance': 0},
            ],
        })
        self.assertEqual(areas[4], {
            'shape': 4, 'scale': 0, 'points': [
                {'angle': 00.0, 'bearing': 0.0, 'distance': 100},
                {'angle': 180.0, 'bearing': 90.0, 'distance': 100},
                {'angle': 360.0, 'bearing': 180.0, 'distance': 100},
                {'angle': 540.0, 'bearing': 270.0, 'distance': 100},
            ],
        })
        self.assertEqual(areas[5], {'shape': 5, 'text': 'DIVERS DOWN'})

    def test_scale_factor_applies_to_linear_dimensions(self):
        """Each scale step multiplies radius/east/north/distance by ten."""
        for scale, radius in ((0, 4095), (1, 40950), (2, 409500), (3, 4095000)):
            bits = _area_notice_header() + _sub_circle(0.0, 0.0, 4095, scale=scale)
            decoded = decode(*_to_sentences(bits))
            assert isinstance(decoded, MessageType8Dac1Fid22)
            self.assertEqual(decoded.sub_areas[0]['radius'], radius)

        bits = _area_notice_header() + _sub_rectangle(0.0, 0.0, 255, 255, 0, scale=2)
        decoded = decode(*_to_sentences(bits))
        assert isinstance(decoded, MessageType8Dac1Fid22)
        self.assertEqual(decoded.sub_areas[0]['east'], 25500)
        self.assertEqual(decoded.sub_areas[0]['north'], 25500)

        bits = _area_notice_header() + _sub_waypoints(3, [(0, 1023)] * 4, scale=3)
        decoded = decode(*_to_sentences(bits))
        assert isinstance(decoded, MessageType8Dac1Fid22)
        self.assertEqual(decoded.sub_areas[0]['points'][0]['distance'], 1023000)

    def test_single_and_maximum_sub_area_counts(self):
        """1 sub-area is the minimum (198 bits) and 10 the maximum (981 bits)."""
        bits = _area_notice_header() + _sub_text("ONE")
        self.assertEqual(len(bits), 198)
        decoded = decode(*_to_sentences(bits))
        assert isinstance(decoded, MessageType8Dac1Fid22)
        self.assertEqual(len(decoded.sub_areas), 1)
        self.assertEqual(decoded.sub_areas[0]['text'], 'ONE')

        bits = _area_notice_header()
        for i in range(10):
            bits += _sub_circle(1.0 * i, 2.0 * i, radius=i)
        self.assertEqual(len(bits), 981)
        decoded = decode(*_to_sentences(bits))
        assert isinstance(decoded, MessageType8Dac1Fid22)
        self.assertEqual(len(decoded.sub_areas), 10)
        self.assertEqual(decoded.sub_areas[9]['lon'], 9.0)
        self.assertEqual(decoded.sub_areas[9]['lat'], 18.0)
        self.assertEqual(decoded.sub_areas[9]['radius'], 9)

    def test_defaults_and_na_sentinels(self):
        """The N/A defaults from the spec table survive a round trip."""
        bits = _area_notice_header(
            notice=127,      # Undefined (default)
            month=0,         # N/A
            day=0,           # N/A
            hour=24,         # N/A
            minute=60,       # N/A
            duration=262143  # N/A
        )
        bits += _sub_text("")
        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid22)
        self.assertEqual(decoded.notice, 127)
        self.assertEqual(decoded.month, 0)
        self.assertEqual(decoded.day, 0)
        self.assertEqual(decoded.hour, 24)
        self.assertEqual(decoded.minute, 60)
        self.assertEqual(decoded.duration, 262143)
        self.assertEqual(decoded.sub_areas[0], {'shape': 5, 'text': ''})

    def test_notice_126_cancels_the_area_by_linkage_id(self):
        """Notice 126 plus duration 0 is the documented cancellation form."""
        bits = _area_notice_header(notice=126, linkage=1023, duration=0)
        bits += _sub_circle(-70.8, 42.3, radius=0)
        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid22)
        self.assertEqual(decoded.notice, 126)
        self.assertEqual(decoded.linkage, 1023)
        self.assertEqual(decoded.duration, 0)
        # radius 0 means the shape is a point rather than a circle
        self.assertEqual(decoded.sub_areas[0]['radius'], 0)

    def test_reserved_shapes_are_kept_raw(self):
        """Shapes 6-7 are reserved, so the payload is not guessed at."""
        for shape in (6, 7):
            bits = _area_notice_header() + _twos(shape, 3) + _twos(12345, 84)
            decoded = decode(*_to_sentences(bits))
            assert isinstance(decoded, MessageType8Dac1Fid22)
            self.assertEqual(decoded.sub_areas[0], {'shape': shape, 'data': 12345})

    def test_negative_and_extreme_coordinates(self):
        """Positions are signed 1/1000-minute values."""
        bits = _area_notice_header()
        bits += _sub_circle(-179.99998, -89.99998, radius=1)
        bits += _sub_circle(179.99998, 89.99998, radius=1)
        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid22)
        self.assertEqual(decoded.sub_areas[0]['lon'], -179.99998)
        self.assertEqual(decoded.sub_areas[0]['lat'], -89.99998)
        self.assertEqual(decoded.sub_areas[1]['lon'], 179.99998)
        self.assertEqual(decoded.sub_areas[1]['lat'], 89.99998)

    def test_encode_decode_round_trip(self):
        """Build a message with create()/encode_msg() and read it back."""
        area_bits = _sub_circle(11.5, 55.25, radius=300)
        area_bits += _sub_text("SURVEY OPS")
        area_data = _pack_sub_areas(area_bits)

        encoded = encode_msg(MessageType8Dac1Fid22.create(
            mmsi='219000001',
            linkage=7,
            notice=13,  # Caution Area: Survey operations
            month=3,
            day=9,
            hour=6,
            minute=45,
            duration=600,
            area_data=area_data,
        ))
        decoded = decode(*encoded)

        assert isinstance(decoded, MessageType8Dac1Fid22)
        self.assertEqual(decoded.mmsi, 219000001)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 22)
        self.assertEqual(decoded.linkage, 7)
        self.assertEqual(decoded.notice, 13)
        self.assertEqual(decoded.duration, 600)
        self.assertEqual(len(decoded.sub_areas), 2)
        self.assertEqual(decoded.sub_areas[0]['lon'], 11.5)
        self.assertEqual(decoded.sub_areas[0]['lat'], 55.25)
        self.assertEqual(decoded.sub_areas[0]['radius'], 300)
        self.assertEqual(decoded.sub_areas[1]['text'], 'SURVEY OPS')

    def test_encode_dict_round_trip(self):
        """The (dac, fid) pair routes through encode_dict as well."""
        area_data = _pack_sub_areas(_sub_text("HIGH WIND"))
        encoded = encode_dict({
            'msg_type': 8,
            'mmsi': '219000001',
            'dac': 1,
            'fid': 22,
            'notice': 26,  # Environmental Caution Area: High wind
            'area_data': area_data,
        })
        decoded = decode(*encoded)

        assert isinstance(decoded, MessageType8Dac1Fid22)
        self.assertEqual(decoded.notice, 26)
        self.assertEqual(decoded.sub_areas[0]['text'], 'HIGH WIND')

    def test_empty_area_region_yields_no_sub_areas(self):
        """A header-only message decodes without raising."""
        decoded = MessageType8Dac1Fid22.create(mmsi='219000001')
        self.assertEqual(decoded.sub_areas, [])


if __name__ == "__main__":
    unittest.main()

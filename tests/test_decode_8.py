import unittest

from pyais import decode
from pyais.encode import encode_dict, encode_msg, ais_to_nmea_0183
from pyais.util import SixBitNibleEncoder, to_six_bit
from pyais.messages import (
    MessageType8Dac1Fid29,
    MessageType8Default,
    MessageType8Dac1Fid0,
    MessageType8Dac1Fid11,
    MessageType8Dac1Fid16,
    MessageType8Dac1Fid17,
    MessageType8Dac1Fid19,
    MessageType8Dac1Fid20,
    MessageType8Dac1Fid21NonWmo,
    MessageType8Dac1Fid22,
    MessageType8Dac1Fid24,
    MessageType8Dac1Fid26,
    MessageType8Dac1Fid27,
    MessageType8Dac1Fid31,
)
from pyais.constants import SOLASStatus, IceClass


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
            "airtemp": 102.4,
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
        bits += ''.join(to_six_bit(c) for c in station)        # Name of Signal Station
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
        decoded = decode(b"!AIVDO,1,1,,A,802R5Ph0EAI8aT1Q8q2RI1:00000009B6hig0KCVjm9iJ7=IAKU>>7AP8UQ8,0*6C")
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
        self.assertEqual(decoded.pressure, 1013)
        self.assertEqual(decoded.pressuretend, 5)
        self.assertEqual(decoded.airtemp, 18.3)
        self.assertEqual(decoded.watertemp, 16.7)
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
        bits += _twos(1013 - 799, 9)                           # Air Pressure
        bits += _twos(5, 4)                                    # Pressure Tendency
        bits += _twos(183, 11)                                 # Air Temperature (0.1C)
        bits += _twos(round((16.7) / 0.1), 10)                 # Water Temperature
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
        self.assertEqual(decoded.pressure, 1013)
        self.assertEqual(decoded.pressuretend, 5)
        self.assertEqual(decoded.airtemp, 18.3)
        self.assertEqual(decoded.watertemp, 16.7)
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
            'shape_str': 'circle',
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
            'precision': 4, 'radius': 2500, 'shape_str': 'circle'
        })
        self.assertEqual(areas[1], {
            'shape': 1, 'scale': 0, 'lon': -70.9, 'lat': 42.2,
            'precision': 4, 'east': 200, 'north': 150, 'orientation': 45,
            'shape_str': 'rectangle'
        })
        self.assertEqual(areas[2], {
            'shape': 2, 'scale': 0, 'lon': -70.7, 'lat': 42.4,
            'precision': 4, 'radius': 1000, 'left': 30, 'right': 120,
            'shape_str': 'sector'
        })
        # Bearings are half-degree steps, so 90 raw is 45 degrees.
        self.assertEqual(areas[3], {
            'shape': 3, 'scale': 0, 'points': [
                {'bearing': 45.0, 'distance': 500},
                {'bearing': 90.0, 'distance': 300},
                {'bearing': 360.0, 'distance': 0},   # 720 = N/A
                {'bearing': 360.0, 'distance': 0},
            ],
            'shape_str': 'polyline'
        })
        self.assertEqual(areas[4], {
            'shape': 4, 'scale': 0, 'points': [
                {'bearing': 0.0, 'distance': 100},
                {'bearing': 90.0, 'distance': 100},
                {'bearing': 180.0, 'distance': 100},
                {'bearing': 270.0, 'distance': 100},
            ], 'shape_str': 'polygon'
        })
        self.assertEqual(areas[5], {'shape': 5, 'text': 'DIVERS DOWN', 'shape_str': 'text'})

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
        self.assertEqual(decoded.sub_areas[0], {'shape': 5, 'shape_str': 'text', 'text': ''})

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
            self.assertEqual(decoded.sub_areas[0], {'shape': shape, 'shape_str': 'reserved', 'data': 12345})

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


def _fid24_message(**over) -> str:
    """Pack the fixed 360-bit IMO289 Extended Ship Static and Voyage
    Related Data message (DAC=1, FID=24) field-by-field per the spec."""
    states = [
        'ais_state', 'ata_state', 'bnwas_state', 'ecdisb_state', 'chart_state',
        'sounder_state', 'epaid_state', 'steer_state', 'gnss_state', 'gyro_state',
        'lrit_state', 'magcomp_state', 'navtex_state', 'arpa_state', 'sband_state',
        'xband_state', 'hfradio_state', 'inmarsat_state', 'mfradio_state',
        'vhfradio_state', 'grndlog_state', 'waterlog_state', 'thd_state',
        'tcs_state', 'vdr_state',
    ]
    bits = _twos(8, 6)                                      # Message Type
    bits += _twos(over.get('repeat', 0), 2)                 # Repeat Indicator
    bits += _twos(over.get('mmsi', 219000001), 30)          # Source MMSI
    bits += '00'                                            # Spare
    bits += _twos(1, 10)                                    # DAC
    bits += _twos(24, 6)                                    # FID
    bits += _twos(over.get('linkage', 7), 10)               # Message Linkage ID
    bits += _twos(over.get('airdraught', 2550), 13)         # Air Draught (0.01m units)
    bits += _sixbit(over.get('lastport', 'USNYC'), 5)
    bits += _sixbit(over.get('nextport', 'NLRTM'), 5)
    bits += _sixbit(over.get('secondport', 'DEHAM'), 5)
    for name in states:
        bits += _twos(over.get(name, 0), 2)
    bits += '00'                                            # Reserved
    bits += _twos(over.get('iceclass', 15), 4)
    bits += _twos(over.get('horsepower', 262143), 18)
    bits += _twos(over.get('vhfchan', 0), 12)
    bits += _sixbit(over.get('lshiptype', ''), 7)
    bits += _twos(over.get('tonnage', 262143), 18)
    bits += _twos(over.get('lading', 0), 2)
    bits += _twos(over.get('heavyoil', 0), 2)
    bits += _twos(over.get('lightoil', 0), 2)
    bits += _twos(over.get('dieseloil', 0), 2)
    bits += _twos(over.get('totaloil', 16382), 14)
    bits += _twos(over.get('persons', 0), 13)
    bits += '0' * 10                                        # Spare
    return bits


class MessageType8Dac1Fid24Tests(unittest.TestCase):
    """IMO289 Extended Ship Static and Voyage Related Data. DAC=1, FID=24."""

    def test_bit_layout_matches_spec(self):
        """Hand-pack every field with a distinct value and decode it back."""
        bits = _fid24_message(
            mmsi=366999707,
            linkage=99,
            airdraught=1234,
            lastport='NLRTM',
            nextport='USNYC',
            secondport='DEHAM',
            ais_state=1, ata_state=2, bnwas_state=3, ecdisb_state=0,
            chart_state=1, sounder_state=2, epaid_state=3, steer_state=0,
            gnss_state=1, gyro_state=2, lrit_state=3, magcomp_state=0,
            navtex_state=1, arpa_state=2, sband_state=3, xband_state=0,
            hfradio_state=1, inmarsat_state=2, mfradio_state=3, vhfradio_state=0,
            grndlog_state=1, waterlog_state=2, thd_state=3, tcs_state=0,
            vdr_state=1,
            iceclass=7,
            horsepower=54321,
            vhfchan=16,
            lshiptype='TANKERS',
            tonnage=123456 % 262142,
            lading=1,
            heavyoil=2,
            lightoil=1,
            dieseloil=2,
            totaloil=8000,
            persons=42,
        )
        self.assertEqual(len(bits), 360)

        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid24)
        self.assertEqual(decoded.msg_type, 8)
        self.assertEqual(decoded.mmsi, 366999707)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 24)
        self.assertEqual(decoded.linkage, 99)
        self.assertEqual(decoded.airdraught, 12.34)
        self.assertEqual(decoded.lastport, 'NLRTM')
        self.assertEqual(decoded.nextport, 'USNYC')
        self.assertEqual(decoded.secondport, 'DEHAM')

        self.assertEqual(decoded.ais_state, SOLASStatus.Operational)
        self.assertEqual(decoded.ata_state, SOLASStatus.NotOperational)
        self.assertEqual(decoded.bnwas_state, SOLASStatus.NoData)
        self.assertEqual(decoded.ecdisb_state, SOLASStatus.NotAvailable)
        self.assertEqual(decoded.chart_state, SOLASStatus.Operational)
        self.assertEqual(decoded.sounder_state, SOLASStatus.NotOperational)
        self.assertEqual(decoded.epaid_state, SOLASStatus.NoData)
        self.assertEqual(decoded.steer_state, SOLASStatus.NotAvailable)
        self.assertEqual(decoded.gnss_state, SOLASStatus.Operational)
        self.assertEqual(decoded.gyro_state, SOLASStatus.NotOperational)
        self.assertEqual(decoded.lrit_state, SOLASStatus.NoData)
        self.assertEqual(decoded.magcomp_state, SOLASStatus.NotAvailable)
        self.assertEqual(decoded.navtex_state, SOLASStatus.Operational)
        self.assertEqual(decoded.arpa_state, SOLASStatus.NotOperational)
        self.assertEqual(decoded.sband_state, SOLASStatus.NoData)
        self.assertEqual(decoded.xband_state, SOLASStatus.NotAvailable)
        self.assertEqual(decoded.hfradio_state, SOLASStatus.Operational)
        self.assertEqual(decoded.inmarsat_state, SOLASStatus.NotOperational)
        self.assertEqual(decoded.mfradio_state, SOLASStatus.NoData)
        self.assertEqual(decoded.vhfradio_state, SOLASStatus.NotAvailable)
        self.assertEqual(decoded.grndlog_state, SOLASStatus.Operational)
        self.assertEqual(decoded.waterlog_state, SOLASStatus.NotOperational)
        self.assertEqual(decoded.thd_state, SOLASStatus.NoData)
        self.assertEqual(decoded.tcs_state, SOLASStatus.NotAvailable)
        self.assertEqual(decoded.vdr_state, SOLASStatus.Operational)

        self.assertEqual(decoded.iceclass, IceClass.IacsPC7_FsicrIa_RsArc4)
        self.assertEqual(decoded.horsepower, 54321)
        self.assertEqual(decoded.vhfchan, 16)
        self.assertEqual(decoded.lshiptype, 'TANKERS')
        self.assertEqual(decoded.tonnage, 123456 % 262142)
        self.assertEqual(decoded.lading, 1)
        self.assertEqual(decoded.heavyoil, 2)
        self.assertEqual(decoded.lightoil, 1)
        self.assertEqual(decoded.dieseloil, 2)
        self.assertEqual(decoded.totaloil, 8000)
        self.assertEqual(decoded.persons, 42)

    def test_defaults_and_na_sentinels(self):
        """The N/A defaults from the spec table survive a round trip."""
        bits = _fid24_message(
            airdraught=0,       # N/A
            lastport='',
            nextport='',
            secondport='',
            iceclass=15,        # N/A (default)
            horsepower=262143,  # N/A (default)
            vhfchan=0,          # N/A (default)
            lshiptype='',
            tonnage=262143,     # N/A (default)
            lading=0,
            heavyoil=0,
            lightoil=0,
            dieseloil=0,
            totaloil=16382,     # N/A (default)
            persons=0,          # N/A (default)
        )
        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid24)
        self.assertEqual(decoded.airdraught, 0)
        self.assertEqual(decoded.lastport, '')
        self.assertEqual(decoded.nextport, '')
        self.assertEqual(decoded.secondport, '')
        self.assertEqual(decoded.iceclass, IceClass.NotAvailable)
        self.assertEqual(decoded.horsepower, 262143)
        self.assertEqual(decoded.vhfchan, 0)
        self.assertEqual(decoded.lshiptype, '')
        self.assertEqual(decoded.tonnage, 262143)
        self.assertEqual(decoded.totaloil, 16382)
        self.assertEqual(decoded.persons, 0)

        for name in (
            'ais_state', 'ata_state', 'bnwas_state', 'ecdisb_state', 'chart_state',
            'sounder_state', 'epaid_state', 'steer_state', 'gnss_state', 'gyro_state',
            'lrit_state', 'magcomp_state', 'navtex_state', 'arpa_state', 'sband_state',
            'xband_state', 'hfradio_state', 'inmarsat_state', 'mfradio_state',
            'vhfradio_state', 'grndlog_state', 'waterlog_state', 'thd_state',
            'tcs_state', 'vdr_state',
        ):
            self.assertEqual(getattr(decoded, name), SOLASStatus.NotAvailable)

    def test_ice_class_reserved_codes_fall_back_to_not_available(self):
        """Codes 11-14 are reserved for future use; treat them as N/A."""
        for code in (11, 12, 13, 14):
            bits = _fid24_message(iceclass=code)
            decoded = decode(*_to_sentences(bits))
            assert isinstance(decoded, MessageType8Dac1Fid24)
            self.assertEqual(decoded.iceclass, IceClass.NotAvailable)

    def test_airdraught_special_value(self):
        """8191 raw (81.91m) is the documented '>= 81.91 m' sentinel."""
        bits = _fid24_message(airdraught=8191)
        decoded = decode(*_to_sentences(bits))
        assert isinstance(decoded, MessageType8Dac1Fid24)
        self.assertEqual(decoded.airdraught, 81.91)

    def test_encode_decode_round_trip(self):
        """Build a message with create()/encode_msg() and read it back."""
        encoded = encode_msg(MessageType8Dac1Fid24.create(
            mmsi='219000001',
            linkage=3,
            airdraught=25.5,
            lastport='USNYC',
            nextport='NLRTM',
            secondport='DEHAM',
            gnss_state=SOLASStatus.Operational,
            bnwas_state=SOLASStatus.NotOperational,
            thd_state=SOLASStatus.NoData,
            iceclass=IceClass.IacsPC6_FsicrIaSuper_RsArc5,
            horsepower=12000,
            vhfchan=16,
            lshiptype='TANKER',
            tonnage=50000,
            lading=1,
            heavyoil=2,
            lightoil=1,
            dieseloil=1,
            totaloil=500,
            persons=20,
        ))
        decoded = decode(*encoded)

        assert isinstance(decoded, MessageType8Dac1Fid24)
        self.assertEqual(decoded.mmsi, 219000001)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 24)
        self.assertEqual(decoded.linkage, 3)
        self.assertEqual(decoded.airdraught, 25.5)
        self.assertEqual(decoded.lastport, 'USNYC')
        self.assertEqual(decoded.nextport, 'NLRTM')
        self.assertEqual(decoded.secondport, 'DEHAM')
        self.assertEqual(decoded.gnss_state, SOLASStatus.Operational)
        self.assertEqual(decoded.bnwas_state, SOLASStatus.NotOperational)
        self.assertEqual(decoded.thd_state, SOLASStatus.NoData)
        self.assertEqual(decoded.iceclass, IceClass.IacsPC6_FsicrIaSuper_RsArc5)
        self.assertEqual(decoded.horsepower, 12000)
        self.assertEqual(decoded.vhfchan, 16)
        self.assertEqual(decoded.lshiptype, 'TANKER')
        self.assertEqual(decoded.tonnage, 50000)
        self.assertEqual(decoded.lading, 1)
        self.assertEqual(decoded.heavyoil, 2)
        self.assertEqual(decoded.lightoil, 1)
        self.assertEqual(decoded.dieseloil, 1)
        self.assertEqual(decoded.totaloil, 500)
        self.assertEqual(decoded.persons, 20)

    def test_encode_dict_round_trip(self):
        """The (dac, fid) pair routes through encode_dict as well."""
        encoded = encode_dict({
            'msg_type': 8,
            'mmsi': '219000001',
            'dac': 1,
            'fid': 24,
            'linkage': 11,
            'iceclass': 6,
            'persons': 5,
        })
        decoded = decode(*encoded)

        assert isinstance(decoded, MessageType8Dac1Fid24)
        self.assertEqual(decoded.linkage, 11)
        self.assertEqual(decoded.iceclass, IceClass.IacsPC6_FsicrIaSuper_RsArc5)
        self.assertEqual(decoded.persons, 5)

    def test_dispatch_is_registered_not_default(self):
        """DAC=1/FID=24 must route to the structured class, not the fallback."""
        decoded = MessageType8Dac1Fid24.create(mmsi='219000001')
        self.assertNotIsInstance(decoded, MessageType8Default)


def _env_header(**over) -> str:
    """Pack the fixed 56-bit Environmental header (IMO289 DAC=1/FID=26)."""
    bits = _twos(8, 6)                                  # Message Type
    bits += _twos(over.get('repeat', 0), 2)             # Repeat Indicator
    bits += _twos(over.get('mmsi', 366999707), 30)      # Source MMSI
    bits += '00'                                        # Spare
    bits += _twos(1, 10)                                # DAC
    bits += _twos(26, 6)                                # FID
    return bits


def _env_record_header(sensor: int, **over) -> str:
    """Pack the common 27-bit record header shared by every sensor type."""
    bits = _twos(sensor, 4)
    bits += _twos(over.get('day', 0), 5)
    bits += _twos(over.get('hour', 24), 5)
    bits += _twos(over.get('minute', 60), 6)
    bits += _twos(over.get('site', 0), 7)
    return bits


def _env_site_location(lon=0.0, lat=0.0, alt=0, owner=0, timeout=0, **over) -> str:
    bits = _env_record_header(0, **over)
    bits += _twos(round(lon * 600000), 28)
    bits += _twos(round(lat * 600000), 27)
    bits += _twos(alt, 11)
    bits += _twos(owner, 4)
    bits += _twos(timeout, 3)
    bits += '0' * 12
    return bits


def _env_station_id(name='', **over) -> str:
    bits = _env_record_header(1, **over)
    bits += _sixbit(name, 14)
    bits += '0'
    return bits


def _env_wind(wspeed=0, wgust=0, wdir=0, wgustdir=0, sensortype=0,
              fwspeed=0, fwgust=0, fwdir=0, fday=0, fhour=24, fminute=60,
              duration=255, **over) -> str:
    bits = _env_record_header(2, **over)
    bits += _twos(wspeed, 7) + _twos(wgust, 7) + _twos(wdir, 9) + _twos(wgustdir, 9)
    bits += _twos(sensortype, 3)
    bits += _twos(fwspeed, 7) + _twos(fwgust, 7) + _twos(fwdir, 9)
    bits += _twos(fday, 5) + _twos(fhour, 5) + _twos(fminute, 6) + _twos(duration, 8)
    bits += '0' * 3
    return bits


def _env_water_level(absolute=False, level=0, leveltrend=3, datum=14, sensortype=0,
                     fabsolute=False, flevel=0, fday=0, fhour=24, fminute=60,
                     duration=255, **over) -> str:
    bits = _env_record_header(3, **over)
    bits += _twos(int(absolute), 1)
    bits += _twos(round(level * 100), 16)
    bits += _twos(leveltrend, 2) + _twos(datum, 5) + _twos(sensortype, 3)
    bits += _twos(int(fabsolute), 1)
    bits += _twos(round(flevel * 100), 16)
    bits += _twos(fday, 5) + _twos(fhour, 5) + _twos(fminute, 6) + _twos(duration, 8)
    bits += '0' * 17
    return bits


def _env_airgap(airdraught=0, airgap=0, gaptrend=3, fairgap=0,
                fday=0, fhour=24, fminute=60, **over) -> str:
    bits = _env_record_header(10, **over)
    bits += _twos(round(airdraught * 100), 13)
    bits += _twos(round(airgap * 100), 13)
    bits += _twos(gaptrend, 2)
    bits += _twos(round(fairgap * 100), 13)
    bits += _twos(fday, 5) + _twos(fhour, 5) + _twos(fminute, 6)
    bits += '0' * 28
    return bits


class MessageType8Dac1Fid26Tests(unittest.TestCase):
    """IMO289 Environmental. DAC=1, FID=26."""

    def test_site_location_and_wind_reports(self):
        """Two records of different sensor types decode independently."""
        bits = _env_header(mmsi=366999707)
        bits += _env_site_location(lon=-70.5, lat=42.3, alt=150, owner=4,
                                   timeout=2, day=15, hour=12, minute=30, site=5)
        bits += _env_wind(wspeed=12, wgust=18, wdir=270, wgustdir=280,
                          sensortype=1, fwspeed=10, fwgust=15, fwdir=275,
                          fday=16, fhour=14, fminute=0, duration=60,
                          day=16, hour=13, minute=45, site=9)
        self.assertEqual(len(bits), 56 + 2 * 112)

        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid26)
        self.assertEqual(decoded.mmsi, 366999707)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 26)

        reports = decoded.reports
        self.assertEqual(len(reports), 2)

        site = reports[0]
        self.assertEqual(site['sensor'], 0)
        self.assertEqual(site['sensor_str'], 'site_location')
        self.assertEqual(site['day'], 15)
        self.assertEqual(site['hour'], 12)
        self.assertEqual(site['minute'], 30)
        self.assertEqual(site['site'], 5)
        self.assertEqual(site['lon'], -70.5)
        self.assertEqual(site['lat'], 42.3)
        self.assertEqual(site['alt'], 15.0)
        self.assertEqual(site['owner'], 4)
        self.assertEqual(site['timeout'], 2)

        wind = reports[1]
        self.assertEqual(wind['sensor'], 2)
        self.assertEqual(wind['sensor_str'], 'wind')
        self.assertEqual(wind['wspeed'], 12)
        self.assertEqual(wind['wgust'], 18)
        self.assertEqual(wind['wdir'], 270)
        self.assertEqual(wind['wgustdir'], 280)
        self.assertEqual(wind['sensortype'], 1)
        self.assertEqual(wind['fwspeed'], 10)
        self.assertEqual(wind['fwgust'], 15)
        self.assertEqual(wind['fwdir'], 275)
        self.assertEqual(wind['fday'], 16)
        self.assertEqual(wind['fhour'], 14)
        self.assertEqual(wind['fminute'], 0)
        self.assertEqual(wind['duration'], 60)

    def test_station_id_report(self):
        """Station ID is 14 six-bit characters filling the whole payload."""
        bits = _env_header() + _env_station_id(name='BUOY42', day=1, hour=0, minute=0, site=1)
        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid26)
        report = decoded.reports[0]
        self.assertEqual(report['sensor'], 1)
        self.assertEqual(report['sensor_str'], 'station_id')
        self.assertEqual(report['name'], 'BUOY42')

    def test_water_level_report(self):
        """Signed level in 0.01m steps, plus a forecast level/time."""
        bits = _env_header() + _env_water_level(
            absolute=True, level=1.23, leveltrend=1, datum=6, sensortype=2,
            fabsolute=False, flevel=-4.56, fday=2, fhour=3, fminute=4, duration=30,
        )
        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid26)
        report = decoded.reports[0]
        self.assertEqual(report['sensor'], 3)
        self.assertEqual(report['sensor_str'], 'water_level')
        self.assertTrue(report['absolute'])
        self.assertEqual(report['level'], 1.23)
        self.assertEqual(report['leveltrend'], 1)
        self.assertEqual(report['datum'], 6)
        self.assertEqual(report['sensortype'], 2)
        self.assertFalse(report['fabsolute'])
        self.assertEqual(report['flevel'], -4.56)
        self.assertEqual(report['fday'], 2)
        self.assertEqual(report['fhour'], 3)
        self.assertEqual(report['fminute'], 4)
        self.assertEqual(report['duration'], 30)

    def test_airgap_report(self):
        """Air draught/air gap in 0.01m steps, with a forecast time."""
        bits = _env_header() + _env_airgap(
            airdraught=25.50, airgap=30.10, gaptrend=1, fairgap=29.90,
            fday=5, fhour=6, fminute=7,
        )
        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid26)
        report = decoded.reports[0]
        self.assertEqual(report['sensor'], 10)
        self.assertEqual(report['sensor_str'], 'airgap')
        self.assertEqual(report['airdraught'], 25.50)
        self.assertEqual(report['airgap'], 30.10)
        self.assertEqual(report['gaptrend'], 1)
        self.assertEqual(report['fairgap'], 29.90)
        self.assertEqual(report['fday'], 5)
        self.assertEqual(report['fhour'], 6)
        self.assertEqual(report['fminute'], 7)

    def test_reserved_and_unknown_sensor_types_kept_raw(self):
        """Type 11 (reserved) and other out-of-range codes are kept raw."""
        for sensor in (11, 12, 15):
            bits = _env_header() + _env_record_header(sensor) + _twos(999, 85)
            decoded = decode(*_to_sentences(bits))
            assert isinstance(decoded, MessageType8Dac1Fid26)
            report = decoded.reports[0]
            self.assertEqual(report['sensor'], sensor)
            self.assertEqual(report['sensor_str'], 'reserved')
            self.assertEqual(report['data'], 999)

    def test_single_and_maximum_report_counts(self):
        """1 report is the minimum (168 bits) and 5 the maximum (560 bits)."""
        bits = _env_header() + _env_station_id(name='A')
        self.assertEqual(len(bits), 168)
        decoded = decode(*_to_sentences(bits))
        assert isinstance(decoded, MessageType8Dac1Fid26)
        self.assertEqual(len(decoded.reports), 1)

        bits = _env_header()
        for i in range(5):
            bits += _env_site_location(lon=1.0 * i, lat=2.0 * i, site=i)
        self.assertEqual(len(bits), 56 + 5 * 112)
        decoded = decode(*_to_sentences(bits))
        assert isinstance(decoded, MessageType8Dac1Fid26)
        self.assertEqual(len(decoded.reports), 5)
        self.assertEqual(decoded.reports[4]['lon'], 4.0)
        self.assertEqual(decoded.reports[4]['lat'], 8.0)
        self.assertEqual(decoded.reports[4]['site'], 4)

    def test_empty_reports_region_yields_no_reports(self):
        """A header-only message decodes without raising."""
        decoded = MessageType8Dac1Fid26.create(mmsi='219000001')
        self.assertEqual(decoded.reports, [])

    def test_encode_decode_round_trip(self):
        """Build a message with create()/encode_msg() and read it back."""
        # Sensor records are packed the same way sub-areas are: raw bits to bytes.
        bits = _env_wind(wspeed=8, wgust=11, wdir=90, wgustdir=95, day=3, hour=4, minute=5, site=2)
        padded = bits + '0' * (-len(bits) % 8)
        reports_data = int(padded, 2).to_bytes(len(padded) // 8, 'big')

        encoded = encode_msg(MessageType8Dac1Fid26.create(
            mmsi='219000001',
            reports_data=reports_data,
        ))
        decoded = decode(*encoded)

        assert isinstance(decoded, MessageType8Dac1Fid26)
        self.assertEqual(decoded.mmsi, 219000001)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 26)
        report = decoded.reports[0]
        self.assertEqual(report['sensor_str'], 'wind')
        self.assertEqual(report['wspeed'], 8)
        self.assertEqual(report['wgust'], 11)
        self.assertEqual(report['wdir'], 90)
        self.assertEqual(report['wgustdir'], 95)

    def test_dispatch_is_registered_not_default(self):
        """DAC=1/FID=26 must route to the structured class, not the fallback."""
        decoded = MessageType8Dac1Fid26.create(mmsi='219000001')
        self.assertNotIsInstance(decoded, MessageType8Default)


def _route_header(**over) -> str:
    """Pack the fixed 117-bit Route Information header (IMO289 DAC=1/FID=27)."""
    bits = _twos(8, 6)                                  # Message Type
    bits += _twos(over.get('repeat', 0), 2)             # Repeat Indicator
    bits += _twos(over.get('mmsi', 366999707), 30)      # Source MMSI
    bits += '00'                                        # Spare
    bits += _twos(1, 10)                                # DAC
    bits += _twos(27, 6)                                # FID
    bits += _twos(over.get('linkage', 5), 10)           # Message Linkage ID
    bits += _twos(over.get('sender', 0), 3)             # Sender Class
    bits += _twos(over.get('rtype', 2), 5)              # Route Type
    bits += _twos(over.get('month', 6), 4)              # Start month (UTC)
    bits += _twos(over.get('day', 15), 5)               # Start day (UTC)
    bits += _twos(over.get('hour', 10), 5)              # Start hour (UTC)
    bits += _twos(over.get('minute', 30), 6)            # Start minute (UTC)
    bits += _twos(over.get('duration', 120), 18)        # Duration
    bits += _twos(over.get('waycount', 0), 5)           # Waypoint count
    return bits


def _route_waypoint(lon: float, lat: float) -> str:
    """Pack a single 55-bit (lon, lat) waypoint."""
    return _twos(round(lon * 600000), 28) + _twos(round(lat * 600000), 27)


class MessageType8Dac1Fid27Tests(unittest.TestCase):
    """IMO289 Route Information (broadcast). DAC=1, FID=27."""

    def test_bit_layout_matches_spec(self):
        """Hand-pack the header plus three waypoints and decode them back."""
        bits = _route_header(
            linkage=99, sender=1, rtype=4, month=11, day=22, hour=8,
            minute=45, duration=600, waycount=3,
        )
        bits += _route_waypoint(-70.5, 42.3)
        bits += _route_waypoint(-70.6, 42.4)
        bits += _route_waypoint(-70.7, 42.5)
        # 117-bit header + 3 waypoints of 55 bits
        self.assertEqual(len(bits), 117 + 3 * 55)

        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid27)
        self.assertEqual(decoded.msg_type, 8)
        self.assertEqual(decoded.mmsi, 366999707)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 27)
        self.assertEqual(decoded.linkage, 99)
        self.assertEqual(decoded.sender, 1)
        self.assertEqual(decoded.rtype, 4)
        self.assertEqual(decoded.month, 11)
        self.assertEqual(decoded.day, 22)
        self.assertEqual(decoded.hour, 8)
        self.assertEqual(decoded.minute, 45)
        self.assertEqual(decoded.duration, 600)
        self.assertEqual(decoded.waycount, 3)

        waypoints = decoded.waypoints
        self.assertEqual(len(waypoints), 3)
        self.assertEqual(waypoints[0], {'lon': -70.5, 'lat': 42.3})
        self.assertEqual(waypoints[1], {'lon': -70.6, 'lat': 42.4})
        self.assertEqual(waypoints[2], {'lon': -70.7, 'lat': 42.5})

    def test_defaults_and_na_sentinels(self):
        """The N/A defaults from the spec table survive a round trip."""
        bits = _route_header(
            sender=0,
            rtype=0,       # Undefined (default)
            month=0,       # N/A
            day=0,         # N/A
            hour=24,       # N/A
            minute=60,     # N/A
            duration=262143,  # N/A (default)
            waycount=0,
        )
        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid27)
        self.assertEqual(decoded.sender, 0)
        self.assertEqual(decoded.rtype, 0)
        self.assertEqual(decoded.month, 0)
        self.assertEqual(decoded.day, 0)
        self.assertEqual(decoded.hour, 24)
        self.assertEqual(decoded.minute, 60)
        self.assertEqual(decoded.duration, 262143)
        self.assertEqual(decoded.waycount, 0)
        self.assertEqual(decoded.waypoints, [])

    def test_cancel_route_via_duration_zero(self):
        """Duration 0 is the documented 'cancel route' form."""
        bits = _route_header(linkage=7, duration=0, waycount=0)
        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid27)
        self.assertEqual(decoded.linkage, 7)
        self.assertEqual(decoded.duration, 0)

    def test_single_and_maximum_waypoint_counts(self):
        """1 waypoint is the minimum (172 bits) and 16 the maximum (997 bits)."""
        bits = _route_header(waycount=1) + _route_waypoint(0.0, 0.0)
        self.assertEqual(len(bits), 172)
        decoded = decode(*_to_sentences(bits))
        assert isinstance(decoded, MessageType8Dac1Fid27)
        self.assertEqual(len(decoded.waypoints), 1)

        bits = _route_header(waycount=16)
        for i in range(16):
            bits += _route_waypoint(1.0 * i, 2.0 * i)
        self.assertEqual(len(bits), 997)
        decoded = decode(*_to_sentences(bits))
        assert isinstance(decoded, MessageType8Dac1Fid27)
        self.assertEqual(len(decoded.waypoints), 16)
        self.assertEqual(decoded.waypoints[15], {'lon': 15.0, 'lat': 30.0})

    def test_waycount_clamped_to_available_data(self):
        """A waycount that overstates the data doesn't fabricate waypoints."""
        bits = _route_header(waycount=5) + _route_waypoint(1.0, 2.0)
        decoded = decode(*_to_sentences(bits))
        assert isinstance(decoded, MessageType8Dac1Fid27)
        self.assertEqual(decoded.waycount, 5)
        self.assertEqual(len(decoded.waypoints), 1)

    def test_negative_and_extreme_coordinates(self):
        """Positions are signed 1/10000-minute values."""
        bits = _route_header(waycount=2)
        bits += _route_waypoint(-179.99998, -89.99998)
        bits += _route_waypoint(179.99998, 89.99998)
        decoded = decode(*_to_sentences(bits))

        assert isinstance(decoded, MessageType8Dac1Fid27)
        self.assertEqual(decoded.waypoints[0], {'lon': -179.99998, 'lat': -89.99998})
        self.assertEqual(decoded.waypoints[1], {'lon': 179.99998, 'lat': 89.99998})

    def test_encode_decode_round_trip(self):
        """Build a message with create()/encode_msg() and read it back."""
        wp_bits = _route_waypoint(11.5, 55.25) + _route_waypoint(11.6, 55.30)
        padded = wp_bits + '0' * (-len(wp_bits) % 8)
        waypoints_data = int(padded, 2).to_bytes(len(padded) // 8, 'big')

        encoded = encode_msg(MessageType8Dac1Fid27.create(
            mmsi='219000001',
            linkage=3,
            sender=1,
            rtype=2,
            month=5,
            day=17,
            hour=9,
            minute=0,
            duration=90,
            waycount=2,
            waypoints_data=waypoints_data,
        ))
        decoded = decode(*encoded)

        assert isinstance(decoded, MessageType8Dac1Fid27)
        self.assertEqual(decoded.mmsi, 219000001)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 27)
        self.assertEqual(decoded.linkage, 3)
        self.assertEqual(decoded.sender, 1)
        self.assertEqual(decoded.rtype, 2)
        self.assertEqual(decoded.duration, 90)
        self.assertEqual(decoded.waycount, 2)
        self.assertEqual(len(decoded.waypoints), 2)
        self.assertEqual(decoded.waypoints[0], {'lon': 11.5, 'lat': 55.25})
        self.assertEqual(decoded.waypoints[1], {'lon': 11.6, 'lat': 55.3})

    def test_encode_dict_round_trip(self):
        """The (dac, fid) pair routes through encode_dict as well."""
        wp_bits = _route_waypoint(-70.5, 42.3)
        padded = wp_bits + '0' * (-len(wp_bits) % 8)
        waypoints_data = int(padded, 2).to_bytes(len(padded) // 8, 'big')

        encoded = encode_dict({
            'msg_type': 8,
            'mmsi': '219000001',
            'dac': 1,
            'fid': 27,
            'rtype': 4,  # Recommended route through ice
            'waycount': 1,
            'waypoints_data': waypoints_data,
        })
        decoded = decode(*encoded)

        assert isinstance(decoded, MessageType8Dac1Fid27)
        self.assertEqual(decoded.rtype, 4)
        self.assertEqual(decoded.waypoints, [{'lon': -70.5, 'lat': 42.3}])

    def test_empty_waypoints_region_yields_no_waypoints(self):
        """A header-only message decodes without raising."""
        decoded = MessageType8Dac1Fid27.create(mmsi='219000001')
        self.assertEqual(decoded.waypoints, [])

    def test_dispatch_is_registered_not_default(self):
        """DAC=1/FID=27 must route to the structured class, not the fallback."""
        decoded = MessageType8Dac1Fid27.create(mmsi='219000001')
        self.assertNotIsInstance(decoded, MessageType8Default)


class MessageType8Dac1Fid29Tests(unittest.TestCase):
    def test_text_description_decode(self):
        bits = _twos(8, 6)                                      # Message Type
        bits += _twos(0, 2)                                     # Repeat Indicator
        bits += _twos(123456789, 30)                            # Source MMSI
        bits += '00'                                            # Spare
        bits += _twos(1, 10)                                    # DAC
        bits += _twos(29, 6)                                    # FID
        bits += _twos(333, 10)                                 # Message Linkage ID
        description = "Lorem ipsum dolor sit amet consectetur adipiscing elit".upper()
        bits += _sixbit(description, len(description))

        decoded = decode(*_to_sentences(bits))

        self.assertEqual(decoded.mmsi, 123456789)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 29)
        self.assertEqual(decoded.linkage, 333)
        self.assertEqual(decoded.description, description)

    def test_text_description_encode(self):
        msg = MessageType8Dac1Fid29.create(
            mmsi=123456789,
            dac=1,
            fid=29,
            linkage=333,
            description="Hello, world!!",
        )

        encoded = encode_msg(msg)

        self.assertEqual(encoded, ['!AIVDO,1,1,,A,81mg=5@0GE=85<<?dPG?B<4QQ,0*54'])

        decoded = decode(*encoded)

        self.assertEqual(decoded.mmsi, 123456789)
        self.assertEqual(decoded.dac, 1)
        self.assertEqual(decoded.fid, 29)
        self.assertEqual(decoded.linkage, 333)
        self.assertEqual(decoded.description, "Hello, world!!".upper())

    def test_dispatch_is_registered_not_default(self):
        """DAC=1/FID=29 must route to the structured class, not the fallback."""
        decoded = MessageType8Dac1Fid29.create(mmsi='219000001')
        self.assertNotIsInstance(decoded, MessageType8Default)


if __name__ == "__main__":
    unittest.main()

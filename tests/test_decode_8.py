import unittest

from pyais import decode
from pyais.encode import encode_dict, encode_msg
from pyais.messages import (
    MessageType8Dac1Fid0,
    MessageType8Dac1Fid11,
    MessageType8Dac1Fid16,
    MessageType8Dac1Fid17,
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
            "accuracy": True, "airtemp": -102.4, "cdepth2": 31, "cdepth3": 31,
            "cdir": 360, "cdir2": 360, "cdir3": 360, "cspeed": 25.5,
            "cspeed2": 25.5, "cspeed3": 25.5, "dac": 1, "day": 19,
            "dewpoint": 50.1, "fid": 11, "hour": 14, "humidity": 101, "ice": 3,
            "lat": 59.66375, "leveltrend": 3, "lon": 18.931983, "minute": 12,
            "mmsi": 2655619, "msg_type": 8, "preciptype": 7, "pressure": 1310,
            "pressuretend": 3, "repeat": 1, "salinity": 51.0, "seastate": 13,
            "swelldir": 360, "swellheight": 25.5, "swellperiod": 63,
            "visgreater": True, "visibility": 1.1, "waterlevel": 30.01,
            "watertemp": 50.1, "wavedir": 360, "waveheight": 25.5,
            "waveperiod": 63, "wdir": 360, "wgust": 127, "wgustdir": 360,
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

    def test_dac_1_fid_31_encode(self):
        encoded = encode_dict({
            "accuracy": True, "airtemp": -102.4, "cdepth2": 31, "cdepth3": 31,
            "cdir": 360, "cdir2": 360, "cdir3": 360, "cspeed": 25.5,
            "cspeed2": 25.5, "cspeed3": 25.5, "dac": 1, "day": 19,
            "dewpoint": 50.1, "fid": 31, "hour": 14, "humidity": 101, "ice": 3,
            "lat": 59.66375, "leveltrend": 3, "lon": 18.931983, "minute": 12,
            "mmsi": 2655619, "msg_type": 8, "preciptype": 7, "pressure": 1310,
            "pressuretend": 3, "repeat": 1, "salinity": 51.0, "seastate": 13,
            "swelldir": 360, "swellheight": 25.5, "swellperiod": 63,
            "visgreater": True, "visibility": 1.1, "waterlevel": 30.01,
            "watertemp": 50.1, "wavedir": 360, "waveheight": 25.5,
            "waveperiod": 63, "wdir": 360, "wgust": 127, "wgustdir": 360,
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


if __name__ == "__main__":
    unittest.main()

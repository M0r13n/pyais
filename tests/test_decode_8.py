import unittest

from pyais import decode
from pyais.encode import encode_dict, encode_msg
from pyais.messages import (
    MessageType8Dac1Fid0,
    MessageType8Dac1Fid11,
    MessageType8Dac1Fid16,
    MessageType8Dac1Fid17,
    MessageType8Dac1Fid19,
    MessageType8Dac1Fid20,
    MessageType8Dac1Fid21,
    MessageType8Dac1Fid22,
    MessageType8Dac1Fid23,
    MessageType8Dac1Fid24,
    MessageType8Dac1Fid25,
    MessageType8Dac1Fid26,
    MessageType8Dac1Fid27,
    MessageType8Dac1Fid29,
    MessageType8Dac1Fid31,
)


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

    def test_dac_1_fid_16_encode(self):
        encoded = encode_msg(MessageType8Dac1Fid16.create(
            mmsi=11223344,
            lon=18.1234,
            lat=50.4321,
            course=245,
            second=33,
            speed=123,
        ))
        self.assertEqual(
            encoded[0],
            "!AIVDO,1,1,,A,80:e1<00D000000002pd1PQ;mSmQNh,4*37"
        )

    def test_dac_1_fid_16_decode(self):
        decoded = decode(b"!AIVDO,1,1,,A,80:e1<00D000000002pd1PQ;mSmQNh,4*37")
        assert isinstance(decoded, MessageType8Dac1Fid16)
        self.assertEqual(decoded.mmsi, 11223344)
        self.assertEqual(decoded.lon, 18.1234)
        self.assertEqual(decoded.lat, 50.4321)
        self.assertEqual(decoded.course, 245)
        self.assertEqual(decoded.second, 33)
        self.assertEqual(decoded.speed, 123)

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

    def test_dac_1_fid_19_encode(self): pass
    def test_dac_1_fid_19_decode(self): pass

    def test_dac_1_fid_20_encode(self): pass
    def test_dac_1_fid_20_decode(self): pass

    def test_dac_1_fid_21_encode(self): pass
    def test_dac_1_fid_21_decode(self): pass

    def test_dac_1_fid_22_encode(self): pass
    def test_dac_1_fid_22_decode(self): pass

    def test_dac_1_fid_23_encode(self): pass
    def test_dac_1_fid_23_decode(self): pass

    def test_dac_1_fid_24_encode(self): pass
    def test_dac_1_fid_24_decode(self): pass

    def test_dac_1_fid_25_encode(self): pass
    def test_dac_1_fid_25_decode(self): pass

    def test_dac_1_fid_26_encode(self): pass
    def test_dac_1_fid_26_decode(self): pass

    def test_dac_1_fid_27_encode(self): pass
    def test_dac_1_fid_27_decode(self): pass

    def test_dac_1_fid_29_encode(self): pass
    def test_dac_1_fid_29_decode(self): pass

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


if __name__ == "__main__":
    unittest.main()

import pathlib
import unittest
from unittest.case import skip
from pyais.stream import FileReaderStream, should_parse
from pyais.messages import NMEAMessage


class TestFileReaderStream(unittest.TestCase):
    FILENAME = "tests/ais_test_messages"

    def test_reader(self):
        with FileReaderStream(self.FILENAME) as stream:
            messages = [msg for msg in stream]

        assert len(messages) == 7
        for msg in messages:
            assert type(msg) == NMEAMessage
            assert msg.is_valid
            assert msg.decode().content is not None

    def test_reader_with_open(self):
        with FileReaderStream(self.FILENAME) as stream:
            msg = next(stream)
            assert type(msg) == NMEAMessage
            assert msg.is_valid
            assert msg.decode().content is not None

    def test_invalid_filename(self):
        with self.assertRaises(FileNotFoundError):
            FileReaderStream("doesnotexist")

    @skip("This takes too long for now")
    def test_large_file(self):
        # The ais sample data is downloaded from https://www.aishub.net/ais-dispatcher
        par_dir = pathlib.Path(__file__).parent.absolute()
        large_file = par_dir.joinpath("nmea-sample")
        for msg in FileReaderStream(large_file):
            msg.decode()

    def test_marine_traffic_sample(self):
        """Test some messages from https://help.marinetraffic.com/hc/en-us
        /articles/215626187-I-am-an-AIS-data-contributor-Can-you-share-more-data-with-me-"""

        par_dir = pathlib.Path(__file__).parent.absolute()
        nmea_file = par_dir.joinpath("nmea_data_sample.txt")

        with FileReaderStream(nmea_file) as stream:
            for msg in stream:
                assert msg.decode()

    def test_should_parse(self):
        self.assertFalse(should_parse(b""))
        self.assertFalse(should_parse(b"#"))
        self.assertFalse(should_parse(b"$"))
        self.assertFalse(should_parse(b"!"))
        self.assertFalse(should_parse(b"Foo"))
        self.assertFalse(should_parse(b"!Baz"))
        self.assertFalse(should_parse(b"$fooBar"))
        self.assertFalse(should_parse(b"Foo,Bar,Baz,Foo,Bar,Baz"))
        self.assertFalse(should_parse(b"Foo,Bar,Baz,Foo,Bar,Baz,Foo"))
        self.assertFalse(should_parse(b"$Foo,Bar,Baz,Foo,Bar,Baz,Foo,"))
        self.assertFalse(should_parse(b"!Foo,Bar,Baz,Foo,Bar,Baz,Foo,"))

        self.assertTrue(should_parse(b"!,,,,,,"))
        self.assertTrue(should_parse(b"!AIVDM,1,1,,B,,0*25"))
        self.assertTrue(should_parse(b"$AIVDM,1,1,,B,,0*25"))
        self.assertTrue(should_parse(b"$Foo,Bar,Baz,Foo,Bar,Baz,Foo"))
        self.assertTrue(should_parse(b"!AIVDM,1,1,,B,33K:7p001k1e5@TE?8rTH3BH011@,0*59"))
        self.assertTrue(should_parse(b"$AIVDM,1,1,,B,33K:7p001k1e5@TE?8rTH3BH011@,0*59"))
        self.assertTrue(should_parse(b"!AIVDM,2,1,9,B,53nFBv01SJ<thHp6220H4heHTf2222222222221?50:454o<`9QSlUDp,0*09"))
        self.assertTrue(should_parse(b"$AIVDM,2,1,9,B,53nFBv01SJ<thHp6220H4heHTf2222222222221?50:454o<`9QSlUDp,0*09"))

    def test_mixed_content(self):
        """Test that the file reader handles mixed content. That means, that is is able to handle
        text files, that contain both AIS messages and non AIS messages."""
        par_dir = pathlib.Path(__file__).parent.absolute()
        mixed_content_file = par_dir.joinpath("messages.ais")
        self.assertEqual(len(list(iter(FileReaderStream(mixed_content_file)))), 6)

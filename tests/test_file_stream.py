import unittest
from pyais.stream import FileReaderStream
from pyais.messages import NMEAMessage


class TestFileReaderStream(unittest.TestCase):
    FILENAME = "tests/ais_test_messages"

    def test_reader(self):
        messages = [msg for msg in FileReaderStream(self.FILENAME)]
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
        with self.assertRaises(ValueError):
            FileReaderStream("doesnotexist")

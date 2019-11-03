import unittest
from pyais.stream import FileReaderStream
from pyais.messages import NMEAMessage


class TestFileReaderStream(unittest.TestCase):

    def test_reader(self):
        filename = "tests/ais_test_messages"
        messages = [msg for msg in FileReaderStream(filename)]
        assert len(messages) == 6
        for msg in messages:
            assert type(msg) == NMEAMessage
            assert msg.is_valid
            assert msg.decode().content is not None

    def test_invalid_filename(self):
        with self.assertRaises(ValueError):
            FileReaderStream("doesnotexist")

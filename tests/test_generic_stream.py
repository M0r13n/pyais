import unittest
from typing import List

from pyais.stream import BinaryIOStream


class MockFile:

    def __init__(self, buffer: List[bytes]):
        self.buffer: List[bytes] = buffer

    def close(self) -> None:
        pass

    def readline(self) -> bytes:
        """
        Read a single line of a file. Empty string if file is empty.
        """
        if not len(self.buffer):
            return b""
        return self.buffer.pop(0)

    def readlines(self) -> List[bytes]:
        """
        Read until EOF using readline() and return a list containing the lines thus read.
        """
        l = []
        while x := self.readline():
            l.append(x)
        return l


class TestGenericStream(unittest.TestCase):

    def test_empty_stream(self):
        """
        If the stream does not contain any data, nothing should happen.
        """
        mock_file = MockFile([b""])
        for msg in BinaryIOStream(mock_file):
            # This should never happen
            self.assertFalse(True)

    def test_garbage_stream(self):
        """
        If the file contains invalid data, nothing should happen, until the first valid message comes by.
        """
        valid: bytes = b"!AIVDM,1,1,,B,B43JRq00LhTWc5VejDI>wwWUoP06,0*29"
        mock_file = MockFile([b"Foo", b"Bar", b"1337", valid])
        for msg in BinaryIOStream(mock_file):
            self.assertEqual(msg.raw, valid)

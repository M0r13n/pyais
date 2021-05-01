import types
import unittest
from typing import List

from pyais import NMEAMessage
from pyais.stream import BinaryIOStream, IterMessages


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
        buf = []
        line = self.readline()
        while line:
            buf.append(line)
            line = self.readline()
        return buf


class TestGenericStream(unittest.TestCase):

    def test_empty_stream(self):
        """
        If the stream does not contain any data, nothing should happen.
        """
        mock_file = MockFile([b""])
        for _ in BinaryIOStream(mock_file):
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

    def test_invalid_msg(self):
        mock_file = MockFile([
            b"AIVDM,1,1,,B,B43JRq00LhTWc5VejDI>wwWUoP06,0*29",
            b"$AIVDM,1,1,,B,B43JRq00LhTWc5VejDI>wwWUoP06,0*29",
            b"!GPSD,1,1,,B,B43JRq00LhTWc5dsfsdfdssdsccccccccccccccdfdsdsfdsfsdfVejDI>wwWUoP06,0*29",
        ])
        for msg in BinaryIOStream(mock_file):
            self.assertIsNotNone(msg.decode())


class TestIterMessages(unittest.TestCase):

    def test_init_from_bytes_transforms_bytes_to_list(self):
        iterable = IterMessages(b"AIVDM,1,1,,B,B43JRq00LhTWc5VejDI>wwWUoP06,0*29")
        self.assertEqual(iterable.messages, [b"AIVDM,1,1,,B,B43JRq00LhTWc5VejDI>wwWUoP06,0*29"])

    def test_init_from_bytes_with_multiple_messages(self):
        iterable = IterMessages([b"A", b"B", b"C"])
        self.assertEqual(iterable.messages, [b"A", b"B", b"C"])

    def test_init_from_str(self):
        iterable = IterMessages.from_strings("AIVDM,1,1,,B,B43JRq00LhTWc5VejDI>wwWUoP06,0*29")
        self.assertEqual(iterable.messages, [b"AIVDM,1,1,,B,B43JRq00LhTWc5VejDI>wwWUoP06,0*29"])

        iterable = IterMessages.from_strings(["A", "B", "C"])
        self.assertEqual(iterable.messages, [b"A", b"B", b"C"])

    def test_init_from_str_throws_error_if_invalid(self):
        with self.assertRaises(UnicodeEncodeError):
            IterMessages.from_strings("öäü", encoding="ascii")

    def test_init_from_ignores_error_if_enabled(self):
        IterMessages.from_strings("öäü", ignore_encoding_errors=True, encoding="ascii")

    def test_iter_is_generator(self):
        iterable = IterMessages.from_strings(["A", "B", "C"])
        self.assertIsInstance(iter(iterable), types.GeneratorType)

    def test_iter_messages_handles_single_message(self):
        for msg in IterMessages(b"AIVDM,1,1,,B,B43JRq00LhTWc5VejDI>wwWUoP06,0*29"):
            self.assertIsInstance(msg, NMEAMessage)
            self.assertIsNotNone(msg.decode())

    def test_iter_messages_does_assemble_multiline_messages(self):
        messages = [
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
            b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
            b'!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
            b'!AIVDM,2,2,9,A,F@V@00000000000,2*3D',
        ]

        decoded = [msg.decode() for msg in IterMessages(messages)]

        self.assertEqual(2, len(decoded))
        self.assertTrue(all(d["mmsi"] == "210035000" for d in decoded))
        self.assertTrue(all(d["shipname"] == "NORDIC HAMBURG" for d in decoded))

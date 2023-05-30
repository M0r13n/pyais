import unittest

from pyais.stream import SocketStream


class MockReceiver:

    def __init__(self, contents) -> None:
        self.contents = contents

    def recv(self):
        try:
            return self.contents.pop(0)
        except IndexError:
            return b''


class SocketStreamingTestCase(unittest.TestCase):

    def test_that_all_lines_are_returned(self):
        # HAVING a socket using LF as line breaks
        stream = SocketStream(None)

        # WHEN receiving two complete lines
        receiver = MockReceiver([b'Hello\nWorld\n'])
        stream.recv = receiver.recv

        # THEN both lines are returned
        result = list(stream.read())
        expected = [b'Hello\n', b'World\n']
        self.assertEqual(result, expected)

    def test_that_all_lines_are_returned_for_incomplete_lines(self):
        # HAVING a socket using LF as line breaks
        stream = SocketStream(None)

        # WHEN receiving an incomplete line
        receiver = MockReceiver([b'Hello\nWor', b'ld\n'])
        stream.recv = receiver.recv

        # THEN the last incomplete line is correctly assembled
        result = list(stream.read())
        expected = [b'Hello\n', b'World\n']
        self.assertEqual(result, expected)

    def test_that_all_lines_are_returned_when_using_crlf(self):
        # HAVING a socket using CRLF as line breaks
        stream = SocketStream(None)

        # WHEN receiving an incomplete line
        receiver = MockReceiver([b'Hello\r\nWor', b'ld\r\n'])
        stream.recv = receiver.recv

        # THEN the last incomplete line is correctly assembled
        result = list(stream.read())
        expected = [b'Hello\r\n', b'World\r\n']
        self.assertEqual(result, expected)

    def test_that_a_single_line_is_returned_as_is(self):
        # HAVING a socket
        stream = SocketStream(None)

        # WHEN receiving a single line
        receiver = MockReceiver([b'FooBar2000\n'])
        stream.recv = receiver.recv

        # THEN the the exact same line is returned
        result = list(stream.read())
        expected = [b'FooBar2000\n', ]
        self.assertEqual(result, expected)

    def test_that_many_lines_are_returned(self):
        # HAVING a socket
        stream = SocketStream(None)

        # WHEN receiving 1000 lines
        receiver = MockReceiver([b'FooBar2000\n', ] * 1000)
        stream.recv = receiver.recv

        # THEN all these lines are returned
        result = list(stream.read())
        expected = [b'FooBar2000\n', ] * 1000
        self.assertEqual(result, expected)

    def test_that_no_partial_artifacts_are_added_after_a_complete_line(self):
        # HAVING a socket
        stream = SocketStream(None)

        # WHEN receiving a partial line and a complete line afterwards
        receiver = MockReceiver([b'Hello\nWor', b'ld\n', b'FooBar\n'])
        stream.recv = receiver.recv

        # THEN the partial line is not prepended to the next line
        result = list(stream.read())
        expected = [b'Hello\n', b'World\n', b'FooBar\n']
        self.assertEqual(result, expected)

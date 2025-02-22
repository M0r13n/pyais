import pathlib
import unittest

from pyais.queue import NMEAQueue
from pyais.stream import FileReaderStream


class QueueTestCase(unittest.TestCase):

    def test_against_file_reader_stream(self):
        # HAVING a file with all sorts of NMEA messages as well as other kinds of messages
        filename = pathlib.Path(__file__).parent.joinpath('mixed.txt')

        # WHEN streaming NMEA/AIS messages from this files using FileReaderStream
        expected = []
        with FileReaderStream(filename) as stream:
            for msg in stream:
                expected.append(msg)

        # WHEN reading the same file putting the lines into a NMEAQueue
        q = NMEAQueue()
        actual = []
        with open(filename, 'rb') as fd:
            for line in fd.readlines():
                q.put_line(line)
                if x := q.get_or_none():
                    actual.append(x)

        # THEN both methods of reading a file return the exact same result
        self.assertEqual(len(expected), len(actual), 'expected list differs from actual list')
        self.assertEqual(expected, actual, 'expected list differs from actual list')

        for a, b, in zip(expected, actual):
            self.assertEqual(a, b)
            self.assertEqual(a.wrapper_msg, b.wrapper_msg)
            if a.tag_block or b.tag_block:
                a.tag_block.init()
                b.tag_block.init()
                self.assertEqual(a.tag_block.text, b.tag_block.text)


if __name__ == '__main__':
    unittest.main()

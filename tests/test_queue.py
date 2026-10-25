import pathlib
import unittest

from pyais.queue import NMEAQueue
from pyais.stream import FileReaderStream, IterMessages, NMEAAssembler


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

    def test_that_put_raises_value_error(self):
        q = NMEAQueue()

        with self.assertRaises(ValueError):
            q.put(b"line")

    def test_manually(self):

        q = NMEAQueue()
        assert q.qsize() == 0  # Initially empty

        # Raw text.
        q.put_line(b'Hello there!')
        assert q.qsize() == 0  # Still empty
        assert q.get_or_none() is None

        # Put a multi-line message into the queue
        q.put_line(b'!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C')
        assert q.qsize() == 0  # Still empty
        q.put_line(b'!AIVDM,2,2,1,A,88888888880,2*25')
        assert q.qsize() == 1  # Returns 1
        assert q.get_or_none() is not None
        assert q.qsize() == 0  # Empty again

        # A multi-line message with tag blocks
        q.put_line(b'\\g:1-2-73874*A\\!AIVDM,1,1,,A,15MrVH0000KH<:V:NtBLoqFP2H9:,0*2F')
        q.put_line(b'\\g:2-2-73874,n:157037*A\\!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B')
        assert q.qsize() == 2
        assert q.get_or_none() is not None
        assert q.qsize() == 1
        assert q.get_or_none() is not None
        assert q.qsize() == 0

        q.put_line(b'!AIVDM,1,1,,A,169a:nP01g`hm4pB7:E0;@0L088i,0*5E')
        q.put_line(b'!AIVDM,1,1,,A,169a:nP01g`hm4pB7:E0;@0L088i,0*5E')
        q.put_line(b'!AIVDM,1,1,,A,169a:nP01g`hm4pB7:E0;@0L088i,0*5E')
        assert q.qsize() == 3

    # Two different multipart messages that share the same sequence ID.
    SHIP_1 = [
        b'!AIVDO,2,1,0,A,55?MbV02;H;s<HtKP00EHE:0@T4@Dn1QQQQQQP16L961O5Gf0NSQEp6ClRp6,0*70',
        b'!AIVDO,2,2,0,A,66666660000,2*20',
    ]
    SHIP_2 = [
        b'!AIVDO,2,1,0,A,55?MbV02;H;s<HtKP018m>15DDDr0l59V1UUUUU6L961O5Gf0NS3kQ3k`6FF,0*7C',
        b'!AIVDO,2,2,0,A,FFFFFFF@000,2*20',
    ]

    def test_lost_first_fragment_does_not_corrupt_next_message(self):
        # Fragment 1 of SHIP_1 never arrives
        lines = [self.SHIP_1[1], self.SHIP_2[0], self.SHIP_2[1]]

        q = NMEAQueue()
        for line in lines:
            q.put_line(line)

        assert q.qsize() == 1
        decoded = q.get_or_none().decode().asdict()
        self.assertEqual(decoded['shipname'], 'RMS QUEEN MARY YYYYY')
        self.assertEqual(decoded['destination'], 'LONDON YYYYYYYYYY')

        # The orphaned fragment was dropped, nothing is left pending
        self.assertEqual(q.assembler.buffer, {})

    def test_fragments_fed_in_separate_calls(self):
        q = NMEAQueue()

        q.put_line(self.SHIP_2[0])
        assert q.qsize() == 0

        q.put_line(self.SHIP_2[1])
        assert q.qsize() == 1
        self.assertEqual(q.get_or_none().decode().shipname, 'RMS QUEEN MARY YYYYY')


class AssemblerTestCase(unittest.TestCase):

    def test_feed_returns_message_only_when_complete(self):
        assembler = NMEAAssembler()
        assert assembler.feed(QueueTestCase.SHIP_2[0]) is None
        msg = assembler.feed(QueueTestCase.SHIP_2[1])
        assert msg is not None
        self.assertEqual(msg.decode().shipname, 'RMS QUEEN MARY YYYYY')

    def test_feed_ignores_invalid_lines(self):
        assembler = NMEAAssembler()
        assert assembler.feed(b'Hello there!') is None
        assert assembler.feed(b'!AIVDM,1') is None

    def test_reset_discards_pending_fragments(self):
        assembler = NMEAAssembler()
        assembler.feed(QueueTestCase.SHIP_2[0])
        assembler.reset()
        assert assembler.feed(QueueTestCase.SHIP_2[1]) is None

    def test_stream_keeps_fragments_between_next_calls(self):
        stream = IterMessages(QueueTestCase.SHIP_2)
        lines = iter(QueueTestCase.SHIP_2)
        stream.messages = [next(lines)]
        with self.assertRaises(StopIteration):
            next(stream)
        stream.messages = [next(lines)]
        self.assertEqual(next(stream).decode().shipname, 'RMS QUEEN MARY YYYYY')


if __name__ == '__main__':
    unittest.main()

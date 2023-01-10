import unittest
import textwrap
from pyais.exceptions import TagBlockNotInitializedException, UnknownMessageException
from pyais.messages import AISSentence, NMEASentenceFactory, TagBlock

from pyais.stream import IterMessages


class TagBlockTestCase(unittest.TestCase):

    def test_tag_block_with_line_count(self):
        raw = b'\\n:3140,s:FooBar,c:1428451253*1C\\!BSVDM,1,1,,A,13nN34?000QFpgRWnQLLSPpF00SO,0*06'
        msg = NMEASentenceFactory.produce(raw)
        tb = msg.tag_block
        tb.init()

        self.assertEqual(tb.receiver_timestamp, '1428451253')
        self.assertEqual(tb.source_station, 'FooBar')
        self.assertEqual(tb.destination_station, None)
        self.assertEqual(tb.line_count, '3140')
        self.assertEqual(tb.relative_time, None)
        self.assertEqual(tb.text, None)

    def test_tag_block_with_multiple_unknown_fields(self):
        raw = b'\\s:rORBCOMM000,q:u,c:1426032001,T:2015-03-11 00.00.01,i:<T>A:12344 F:+30000</T>*07\\!BSVDM,1,1,,A,13nN34?000QFpgRWnQLLSPpF00SO,0*06'
        msg = NMEASentenceFactory.produce(raw)
        tb = msg.tag_block
        tb.init()

        self.assertTrue(tb.is_valid)
        self.assertEqual(tb.receiver_timestamp, '1426032001')
        self.assertEqual(tb.source_station, 'rORBCOMM000')
        self.assertEqual(tb.destination_station, None)
        self.assertEqual(tb.line_count, None)
        self.assertEqual(tb.relative_time, None)
        self.assertEqual(tb.text, None)

    def test_multiple_messages(self):
        text = textwrap.dedent("""
        \\s:2573535,c:1671533231*08\\!BSVDM,2,2,8,B,00000000000,2*36
        \\s:2573535,c:1671533231*08\\!BSVDM,1,1,,A,13nN34?000QFpgRWnQLLSPpF00SO,0*06
        \\s:2573545,c:1671533231*0F\\!BSVDM,1,1,,B,ENjV3A?0`bPQbV::a2hI00000000gtJdD2Uih1088;v010,4*55
        \\s:APIDSSRC1,g:1-2-05649,n:08851,c:0002780328*04\\!ARVDM,1,1,,B,15AQoR?P?wSS`@h@@bg>4?w`0HNP,0*39
        \\s:APIDSSRC1,g:2-2-05649,n:08852,c:0002780328*04\\$ARVSI,1234567899,,041848.95096061,0427,-098,03*62
        \\s:APIDSSRC1,g:1-2-05628,n:08794,c:0002780323*0E\\!ARVDM,1,1,,A,1815=pSP00SSJK8@<qUf4?wN2<26,0*41
        \\s:APIDSSRC1,g:2-2-05628,n:08795,c:0002780323*0C\\$ARVSI,1234567899,,041843.99999999,0272,-097,19*6F
        """)

        messages = [line.encode() for line in text.split() if line]

        with IterMessages(messages) as s:
            for msg in s:
                self.assertIsNotNone(msg.tag_block)
                self.assertFalse(msg.tag_block.initialized)
                msg.tag_block.init()
                self.assertTrue(msg.tag_block.initialized)
                self.assertIsNotNone(msg.tag_block.receiver_timestamp)

                self.assertIsNotNone(msg.decode())

    def test_that_the_factory_removes_the_leading_tag_block(self):
        raw = b'\\s:2573535,c:1671533231*08\\!BSVDM,2,2,8,B,00000000000,2*36'
        msg = NMEASentenceFactory.produce(raw)

        self.assertIsInstance(msg, AISSentence)
        self.assertIsInstance(msg.tag_block, TagBlock)

    def test_that_the_factory_pre_processes_correctly(self):
        raw = b'\\s:2573535,c:1671533231*08\\!BSVDM,2,2,8,B,00000000000,2*36'
        raw, tb = NMEASentenceFactory._pre_process(raw)
        self.assertEqual((raw, tb), (b'!BSVDM,2,2,8,B,00000000000,2*36', b's:2573535,c:1671533231*08'))

        raw = b'!BSVDM,2,2,8,B,00000000000,2*36'
        raw, tb = NMEASentenceFactory._pre_process(raw)
        self.assertEqual((raw, tb), (b'!BSVDM,2,2,8,B,00000000000,2*36', None))

        raw = b'\\s:2573535,c:1671533231*08\\'
        raw, tb = NMEASentenceFactory._pre_process(raw)
        self.assertEqual((raw, tb), (b'', b's:2573535,c:1671533231*08'))

    def test_that_the_factory_is_gentle_with_malformed_tag_blocks(self):
        # Checksum is missing
        raw = b'\\s:2573535,c:1671533231\\!BSVDM,2,2,8,B,00000000000,2*36'
        msg = NMEASentenceFactory.produce(raw)
        self.assertTrue(msg.tag_block.raw)

        # No content
        raw = b'\\!BSVDM,2,2,8,B,00000000000,2*36'
        msg = NMEASentenceFactory.produce(raw)
        self.assertIsNone(msg.tag_block)

        # I case of duplicate \ signs a UnknownMessageException should be raised
        with self.assertRaises(UnknownMessageException):
            raw = b'\\s:2573535,\\c:1671533231\\!BSVDM,2,2,8,B,00000000000,2*36'
            msg = NMEASentenceFactory.produce(raw)
            self.assertTrue(msg.tag_block.raw)

    def test_that_a_tag_block_is_lazily_evaluated(self):
        tb = TagBlock(b's:APIDSSRC1,g:2-2-05628,n:08795,c:0002780323*0C')

        self.assertEqual(tb.initialized, False)

        with self.assertRaises(TagBlockNotInitializedException):
            tb.receiver_timestamp
        with self.assertRaises(TagBlockNotInitializedException):
            tb.destination_station
        with self.assertRaises(TagBlockNotInitializedException):
            tb.line_count
        with self.assertRaises(TagBlockNotInitializedException):
            tb.source_station
        with self.assertRaises(TagBlockNotInitializedException):
            tb.relative_time
        with self.assertRaises(TagBlockNotInitializedException):
            tb.text
        with self.assertRaises(TagBlockNotInitializedException):
            tb.is_valid

        tb.init()

        self.assertEqual(tb.initialized, True)
        assert tb.receiver_timestamp
        assert tb.destination_station is None
        assert tb.line_count
        assert tb.source_station
        assert tb.relative_time is None
        assert tb.text is None
        assert tb.is_valid

    def test_that_unknown_tag_blocks_are_ignored(self):
        tb = TagBlock(b's:APIDSSRC1,g:2-2-05628,n:08795,c:0002780323,x:123445,y:23456*0C')
        tb.init()
        assert tb.receiver_timestamp
        assert tb.destination_station is None
        assert tb.line_count
        assert tb.source_station
        assert tb.relative_time is None
        assert tb.text is None

    def test_that_unknown_tag_blocks_can_exported_as_dicts(self):
        tb = TagBlock(b's:APIDSSRC1,g:2-2-05628,n:08795,c:0002780323,x:123445,y:23456*0C')
        tb.init()

        self.assertEqual(
            tb.asdict(),
            {
                'raw': b's:APIDSSRC1,g:2-2-05628,n:08795,c:0002780323,x:123445,y:23456*0C',
                'receiver_timestamp': '0002780323',
                'source_station': 'APIDSSRC1',
                'destination_station': None,
                'line_count': '08795',
                'relative_time': None,
                'text': None
            }
        )

import unittest
import textwrap
from pyais.decode import decode_nmea_and_ais
from pyais.exceptions import TagBlockNotInitializedException, UnknownMessageException
from pyais.messages import AISSentence, NMEASentenceFactory, TagBlock

from pyais.stream import IterMessages, TagBlockQueue
from pyais.util import checksum


class TagBlockQueueTestCase(unittest.TestCase):

    def test_put_single_w_group(self):
        tbq = TagBlockQueue()

        raw = b'\\g:1-1-4512,s:FooBar,c:1428451253*50\\!AIVDM,1,1,,A,13nN34?000QFpgRWnQLLSPpF00SO,0*1C'
        sentence = NMEASentenceFactory.produce(raw)
        tbq.put_sentence(sentence)

        result = tbq.get_nowait()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], sentence)

    def test_put_single_wo_group(self):
        tbq = TagBlockQueue()

        raw = b'!AIVDM,1,1,,A,13nN34?000QFpgRWnQLLSPpF00SO,0*1C'
        sentence = NMEASentenceFactory.produce(raw)
        tbq.put_sentence(sentence)

        result = tbq.get_nowait()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], sentence)

    def test_put_multiple_w_groups(self):
        RAWS = [
            b'\\g:1-3-4512,s:FooBar,c:1428451253*50\\!AIVDM,1,1,,A,13nN34?000QFpgRWnQLLSPpF00SO,0*1C',
            b'\\g:3-3-4512,s:FooBar,c:1428451253*50\\!AIVDM,1,3,,A,13nN34?000QFpgRWnQLLSPpF00SO,0*1C',
            b'\\g:1-3-1234*30\\!AIVDM,1,1,,A,13nN34?000QFpgRWnQLLSPpF00SO,0*1C',
            b'\\g:2-3-4512*30\\!AIVDM,1,2,,A,13nN34?000QFpgRWnQLLSPpF00SO,0*1C',
            b'\\g:1-1-1337,s:FooBar,c:1428451253*50\\!AIVDM,1,2,,A,13nN34?000QFpgRWnQLLSPpF00SO,0*1C',
            b'\\g:1-42-4242,s:FooBar,c:1428451253*50\\!AIVDM,1,1,,A,13nN34?000QFpgRWnQLLSPpF00SO,0*1C',
        ]
        tbq = TagBlockQueue()

        for raw in RAWS:
            tbq.put_sentence(NMEASentenceFactory.produce(raw))

        result = tbq.get_nowait()
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].frag_num, 1)
        self.assertEqual(result[1].frag_num, 3)
        self.assertEqual(result[2].frag_num, 2)

        result = tbq.get_nowait()
        self.assertEqual(len(result), 1)


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

    def test_tag_block_with_group(self):
        raw = b'\\g:1-2-4512,s:FooBar,c:1428451253*50\\!AIVDM,1,1,,A,13nN34?000QFpgRWnQLLSPpF00SO,0*1C'
        msg = NMEASentenceFactory.produce(raw)
        tb = msg.tag_block
        tb.init()

        self.assertEqual(tb.receiver_timestamp, '1428451253')
        self.assertIsNotNone(tb.group)
        self.assertEqual(tb.group.sentence_num, 1)
        self.assertEqual(tb.group.sentence_tot, 2)
        self.assertEqual(tb.group.group_id, 4512)

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

    def test_spire_maritime_format(self):
        """https://documentation.spire.com/tcp-stream-v2/the-nmea-message-encoding-format/"""
        text = textwrap.dedent("""
        \\c:1503079517*55\\!AIVDM,1,1,,B,C6:b0Kh09b3t1K4ChsS2FK008NL>`2CT@2N000000000S4h8S400,0*50
        \\c:1503079517*53\\!AIVDM,1,1,,B,16:Vk1h00g8O=vRBDhNp0nKp0000,0*40
        \\c:1503079517*53\\!AIVDM,1,1,,B,18155hh00u0DEU`N1F@Bg22R06@D,0*60
        \\c:1503079517*53\\!AIVDM,1,1,,A,83aGFQ@j2ddtMH1b@g?b`7mL0,0*55
        \\c:1503079517*53\\!AIVDM,2,1,9,A,53m@FJ400000hT5<0008E8q@TpF000000000000T2P3425rg0:53kThQDQh0,0*48
        \\c:1503079517*53\\!AIVDM,2,2,9,A,00000000000,2*2D
        \\c:1503079517*52\\!AIVDM,1,1,,A,13oP50Oi420UAtPgp@UPrP1d01,0*1A
        \\c:1503079517*52\\!AIVDM,1,1,,B,B3mISo000H;wsB8SetMnww`5oP06,0*7C
        \\c:1503079517*53\\!AIVDM,2,1,0,B,53aIjwh000010CSK7R04lu8F222222222222221?9@<297?o060@C51D`888,0*1B
        """)

        messages = [line.encode() for line in text.split() if line]

        with IterMessages(messages) as s:
            for msg in s:
                msg.tag_block.init()
                decoded = msg.decode()
                self.assertIsNotNone(decoded.mmsi)
                self.assertEqual(msg.tag_block.receiver_timestamp, '1503079517')

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

    def test_create_from_tag_block(self):
        # Having a NMEA message with a tag block
        msg = b'\\n:157036,s:r003669945,c:12415440354*A\\!AIVDM,1,1,,B,15N4cJ005Jrek0H@9nDW5608EP,013'

        # While decoding the NMEA layer including the tag block
        nmea, _ = decode_nmea_and_ais(msg)
        assert nmea.tag_block
        nmea.tag_block.init()

        # When creating a tag block instance based on the original tag block
        created = TagBlock.create(**nmea.tag_block.asdict())

        # Then the tag block fields are correctly encoded
        self.assertIn(b'c:12415440354', created)
        self.assertIn(b's:r003669945', created)
        self.assertIn(b'n:157036', created)

    def test_create_manually(self):
        # When creating a tag block using key word arguments
        created = TagBlock.create(
            receiver_timestamp=12415440354,
            source_station='foobar',
            line_count=157036,
        )

        # The fields are correctly encoded
        self.assertIn(b'c:12415440354', created)
        self.assertIn(b's:foobar', created)
        self.assertIn(b'n:157036', created)

    def test_create_with_bogus_key_word_args(self):
        # When creating a tag block using key word arguments including some bogus arguments
        created = TagBlock.create(
            receiver_timestamp=12415440354,
            source_station='foobar',
            line_count=157036,
            foo='bar',
            blah=None
        )

        # The fields are correctly encoded
        self.assertIn(b'c:12415440354', created)
        self.assertIn(b's:foobar', created)
        self.assertIn(b'n:157036', created)

        # And all other fielda are ignored
        self.assertEqual(b'c:12415440354,s:foobar,n:157036*64', created)

    def test_create_checksum_valid(self):
        # When creating a tag block using key word arguments
        created = TagBlock.create(
            receiver_timestamp=12415440354,
            source_station='foobar',
            line_count=157036,
        )

        # Then the computed checksum is valid
        payload, actual = created.split(b'*')
        expected = checksum(payload)
        self.assertEqual(int(actual, 16), expected)


if __name__ == '__main__':
    unittest.main()

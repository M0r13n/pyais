import pathlib
import time
import unittest
from unittest.case import skip

from pyais.exceptions import UnknownMessageException, MissingPayloadException
from pyais.messages import GatehouseSentence, NMEAMessage
from pyais.stream import FileReaderStream, IterMessages


class TestFileReaderStream(unittest.TestCase):
    FILENAME = str(pathlib.Path(__file__).parent.joinpath("ais_test_messages").absolute())

    def test_nmea_sorter_sorted(self):
        msgs = [
            b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23",
            b"!AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F",
            b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B",
            b"!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C",
            b"!AIVDM,2,2,1,A,88888888880,2*25",
            b"!AIVDM,1,1,,B,23?up2001gGRju>Ap:;R2APP08:c,0*0E",
            b"!BSVDM,1,1,,A,15Mj23`PB`o=Of>KjvnJg8PT0L2R,0*7E",
            b"!SAVDM,1,1,,B,35Mj2p001qo@5tVKLBWmIDJT01:@,0*33",
            b"!AIVDM,1,1,,A,B5NWV1P0<vSE=I3QdK4bGwoUoP06,0*4F",
            b"!SAVDM,1,1,,A,403Owi1utn1W0qMtr2AKStg020S:,0*4B",
            b"!SAVDM,2,1,4,A,55Mub7P00001L@;SO7TI8DDltqB222222222220O0000067<0620@jhQDTVG,0*43",
            b"!SAVDM,2,2,4,A,30H88888880,2*49",
        ]
        sorter = IterMessages(msgs)
        output = []
        for msg in sorter:
            output += msg.raw.splitlines()

        self.assertEqual(output, msgs)

    def test_nmea_sorter_unsorted(self):
        msgs = [
            b"!AIVDM,2,2,1,A,88888888880,2*25",
            b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23",
            b"!AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F",
            b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B",
            b"!SAVDM,2,1,4,A,55Mub7P00001L@;SO7TI8DDltqB222222222220O0000067<0620@jhQDTVG,0*43",
            b"!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C",
            b"!AIVDM,1,1,,B,23?up2001gGRju>Ap:;R2APP08:c,0*0E",
            b"!BSVDM,1,1,,A,15Mj23`PB`o=Of>KjvnJg8PT0L2R,0*7E",
            b"!SAVDM,2,2,4,A,30H88888880,2*49",
            b"!SAVDM,1,1,,B,35Mj2p001qo@5tVKLBWmIDJT01:@,0*33",
            b"!AIVDM,1,1,,A,B5NWV1P0<vSE=I3QdK4bGwoUoP06,0*4F",
            b"!SAVDM,1,1,,A,403Owi1utn1W0qMtr2AKStg020S:,0*4B",
        ]
        sorter = IterMessages(msgs)
        output = []
        for msg in sorter:
            output += msg.raw.splitlines()
        self.assertEqual(output, [
            b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23",
            b"!AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F",
            b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B",
            b"!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C",
            b"!AIVDM,2,2,1,A,88888888880,2*25",
            b"!AIVDM,1,1,,B,23?up2001gGRju>Ap:;R2APP08:c,0*0E",
            b"!BSVDM,1,1,,A,15Mj23`PB`o=Of>KjvnJg8PT0L2R,0*7E",
            b'!SAVDM,2,1,4,A,55Mub7P00001L@;SO7TI8DDltqB222222222220O0000067<0620@jhQDTVG,0*43',
            b'!SAVDM,2,2,4,A,30H88888880,2*49',
            b'!SAVDM,1,1,,B,35Mj2p001qo@5tVKLBWmIDJT01:@,0*33',
            b'!AIVDM,1,1,,A,B5NWV1P0<vSE=I3QdK4bGwoUoP06,0*4F',
            b'!SAVDM,1,1,,A,403Owi1utn1W0qMtr2AKStg020S:,0*4B'
        ])

    def test_sort_with_different_msg_ids(self):
        msgs = [
            b"!AIVDM,2,2,9,B,888888888888880,2*2E",
            b"!AIVDM,2,1,9,B,53nFBv01SJ<thHp6220H4heHTf2222222222221?50:454o<`9QSlUDp,0*09",
            b'!SAVDM,2,1,4,A,55Mub7P00001L@;SO7TI8DDltqB222222222220O0000067<0620@jhQDTVG,0*43',
            b'!SAVDM,1,1,,B,35Mj2p001qo@5tVKLBWmIDJT01:@,0*33',
            b"!AIVDM,2,2,8,A,88888888880,2*2C",
            b"!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C",
            b"!AIVDM,2,1,8,A,56;OaD02B8EL990b221`P4v1T4pN0HDpN2222216HHN>B6U30A2hCDhD`888,0*4D",
            b'!SAVDM,2,2,4,A,30H88888880,2*49',
            b"!AIVDM,2,2,1,A,88888888880,2*25",
            b"!AIVDM,4,4,1,A,88888888880,2*25",
            b"!AIVDM,4,3,1,A,88888888880,2*25",
            b"!AIVDM,4,2,1,A,88888888880,2*25",
            b"!AIVDM,4,1,1,A,88888888880,2*25",
        ]

        expected = [
            b"!AIVDM,2,1,9,B,53nFBv01SJ<thHp6220H4heHTf2222222222221?50:454o<`9QSlUDp,0*09",
            b"!AIVDM,2,2,9,B,888888888888880,2*2E",
            b'!SAVDM,1,1,,B,35Mj2p001qo@5tVKLBWmIDJT01:@,0*33',
            b"!AIVDM,2,1,8,A,56;OaD02B8EL990b221`P4v1T4pN0HDpN2222216HHN>B6U30A2hCDhD`888,0*4D",
            b"!AIVDM,2,2,8,A,88888888880,2*2C",
            b'!SAVDM,2,1,4,A,55Mub7P00001L@;SO7TI8DDltqB222222222220O0000067<0620@jhQDTVG,0*43',
            b'!SAVDM,2,2,4,A,30H88888880,2*49',
            b"!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C",
            b"!AIVDM,2,2,1,A,88888888880,2*25",
            b"!AIVDM,4,1,1,A,88888888880,2*25",
            b"!AIVDM,4,2,1,A,88888888880,2*25",
            b"!AIVDM,4,3,1,A,88888888880,2*25",
            b"!AIVDM,4,4,1,A,88888888880,2*25",
        ]

        sorter = IterMessages(msgs)
        output = []
        for msg in sorter:
            output += msg.raw.splitlines()

        self.assertEqual(expected, output)

    def test_nmea_sort_index_error(self):
        msgs = [
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
            b'!AIVDM,9,2,2,A,F@V@00000000000,2*3D',
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
            b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
        ]
        expected = [
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
            b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
        ]

        sorter = IterMessages(msgs)
        output = []
        for msg in sorter:
            output += msg.raw.splitlines()

        self.assertEqual(expected, output)

    def test_nmea_sort_invalid_frag_cnt(self):
        msgs = [b"!AIVDM,256,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23", ]
        self.assertEqual(len(list(IterMessages(msgs))), 0)

    def test_reader(self):
        with FileReaderStream(self.FILENAME) as stream:
            messages = [msg for msg in stream]

        self.assertEqual(len(messages), 7)
        for msg in messages:
            assert isinstance(msg, NMEAMessage)
            assert msg.is_valid
            assert msg.decode() is not None

    def test_reader_with_open(self):
        with FileReaderStream(self.FILENAME) as stream:
            msg = next(stream)
            assert isinstance(msg, NMEAMessage)
            assert msg.is_valid
            assert msg.decode() is not None

    def test_invalid_filename(self):
        with self.assertRaises(FileNotFoundError):
            FileReaderStream("doesnotexist")

    @skip("Takes too long")
    def test_large_file(self):
        start = time.time()
        # The ais sample data is downloaded from https://www.aishub.net/ais-dispatcher
        par_dir = pathlib.Path(__file__).parent.absolute()
        large_file = par_dir.joinpath("nmea-sample")
        errors = 0
        with FileReaderStream(large_file) as stream:
            for i, msg in enumerate(stream):
                try:
                    msg.decode()
                except UnknownMessageException:
                    errors += 1
                    continue

        print(f"Decoding {i + 1} messages took:", time.time() - start)
        print("ERRORS", errors)

        assert errors == 2

    def test_marine_traffic_sample(self):
        """Test some messages from https://help.marinetraffic.com/hc/en-us
        /articles/215626187-I-am-an-AIS-data-contributor-Can-you-share-more-data-with-me-"""

        par_dir = pathlib.Path(__file__).parent.absolute()
        nmea_file = par_dir.joinpath("nmea_data_sample.txt")

        with FileReaderStream(nmea_file) as stream:
            for msg in stream:
                try:
                    assert msg.decode()
                except MissingPayloadException:
                    assert msg.raw.startswith(b'!AIVDM,1,1,,')

    def test_mixed_content(self):
        """Test that the file reader handles mixed content. That means, that is is able to handle
        text files, that contain both AIS messages and non AIS messages."""
        par_dir = pathlib.Path(__file__).parent.absolute()
        mixed_content_file = par_dir.joinpath("messages.ais")
        with FileReaderStream(mixed_content_file) as stream:
            self.assertEqual(len(list(iter(stream))), 6)

    def test_timestamp_messages(self):
        par_dir = pathlib.Path(__file__).parent.absolute()
        nmea_file = par_dir.joinpath("timestamped.ais")

        with FileReaderStream(nmea_file) as stream:
            for i, msg in enumerate(stream):
                assert msg.decode()
                if i == 0:
                    assert isinstance(msg.wrapper_msg, GatehouseSentence)
                    assert str(msg.wrapper_msg.timestamp) == '2008-05-09 00:00:00.010000'
                elif i == 2:
                    assert isinstance(msg.wrapper_msg, GatehouseSentence)
                    assert str(msg.wrapper_msg.timestamp) == '2009-05-09 00:00:00.010000'
                else:
                    assert msg.wrapper_msg is None

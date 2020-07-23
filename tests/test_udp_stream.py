import pathlib
from unittest.case import skip
from pyais.util import FixedSizeDict
import unittest
from pyais.stream import OutOfOrderByteStream
from pyais.exceptions import UnknownMessageException


class TestOutOfOrder(unittest.TestCase):
    def test_fixed_sized_dict(self):
        N = 10000
        queue = FixedSizeDict(N + 1)
        for i in range(N):
            queue[i] = i

        # no keys were delted
        assert len(queue) == N
        assert queue.popitem(last=False)[0] == 0
        assert queue.popitem(last=True)[0] == N - 1

        # add another
        queue[N + 1] = 35
        queue[N + 2] = 35
        queue[N + 3] = 35
        # now 1/5th of keys is delted
        assert len(queue) == N - (N // 5) + 1
        # make sure only the oldest ones were deleted
        assert queue.popitem(last=False)[0] == (N // 5) + 1

    def test_out_of_order(self):
        messages = [
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
            b'!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
            b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
            b'!AIVDM,2,2,9,A,F@V@00000000000,2*3D',
        ]
        counter = 0
        for msg in OutOfOrderByteStream(messages):
            msg.decode()
            counter += 1
        assert counter == 2

    def test_out_fo_order_in_order(self):
        # in order messages do not cause problems
        messages = [
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
            b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
            b'!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
            b'!AIVDM,2,2,9,A,F@V@00000000000,2*3D',
        ]
        counter = 0
        for msg in OutOfOrderByteStream(messages):
            msg.decode()
            counter += 1
        assert counter == 2

    def test_split_nmea_header_method(self):
        stream = OutOfOrderByteStream([])
        msg = b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07'
        stream._split_nmea_header(msg)
        assert stream.seq_id == 1
        assert stream.fragment_offset == 0
        assert stream.fragment_count == 2

        # sequence id could be large
        msg = b'!AIVDM,2,1,145859,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07'
        stream._split_nmea_header(msg)
        assert stream.seq_id == 145859

    def test_index_error(self):
        messages = [
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
            b'!AIVDM,2,9,2,A,F@V@00000000000,2*3D',
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
            b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
        ]
        counter = 0
        for msg in OutOfOrderByteStream(messages):
            msg.decode()
            counter += 1

        # only one message was yielded
        assert counter == 1

    def test_delete_after_yield(self):
        messages = [
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
            b"!AIVDM,2,1,7,A,543ri001fIOiEa4<0010u84@4000000000000016;hD854o506SRBkk0FAEP,0*07",
            b'!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
            b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
            b"!AIVDM,2,2,7,A,00000000000,2*23",
            b'!AIVDM,2,2,9,A,F@V@00000000000,2*3D',
        ]
        stream = OutOfOrderByteStream(messages)
        iter_steam = iter(stream)

        # assure that messages are deleted after they are yielded
        assert next(iter_steam).seq_id == b'1'
        assert len(stream.queue) == 2
        assert next(iter_steam).seq_id == b'7'
        assert len(stream.queue) == 1

    def test_three(self):
        messages = [
            b"AIVDM,3,1,5,A,36KVnDh02wawaHPDA8T8h6tT8000t=AV=maD7?>BWiKIE@TR<2QfvaAF1ST4H31B,0*35",
            b"!AIVDM,3,2,5,A,8IBP:UFW<M0FVWS0DPK19@nh4UdS:OufWUIfPF5l1U9LILBn@9@F:41Q@U1EEOE3,0*1D",
            b"!AIVDM,3,3,5,A,j,0*79"
        ]
        stream = OutOfOrderByteStream(messages)
        iter_steam = iter(stream)
        assert next(iter_steam).decode()

    @skip("This takes a while")
    def test_can_decode_large_file(self):
        par_dir = pathlib.Path(__file__).parent.absolute()
        large_file = open(par_dir.joinpath("nmea-sample"), "rb")
        lines = [line for line in large_file.readlines() if line]
        counter = 0

        for msg in OutOfOrderByteStream(lines):
            try:
                assert msg.decode(silent=False)
            except UnknownMessageException:
                pass
            counter += 1
        assert counter == 122933

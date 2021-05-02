import socket
import threading
import time
import typing
import unittest

from pyais.stream import OutOfOrderByteStream, UDPStream
from pyais.util import FixedSizeDict
from tests.utils.skip import is_linux
from tests.utils.timeout import time_limit

MESSAGES = [
    b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
    b"!AIVDM,2,1,7,A,543ri001fIOiEa4<0010u84@4000000000000016;hD854o506SRBkk0FAEP,0*07",
    b'!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
    b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
    b"!AIVDM,2,2,7,A,00000000000,2*23",
    b'!AIVDM,2,2,9,A,F@V@00000000000,2*3D',
]


class MockUDPServer(object):

    def __init__(self, host, port) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = host
        self.port = port

    def send(self):
        time.sleep(0.1)
        for msg in MESSAGES:
            self.sock.sendto(msg + b"\r\n", (self.host, self.port))

        self.sock.close()


class TestOutOfOrderByteStream(OutOfOrderByteStream):
    """
    Subclass OutOfOrderByteStream to test itÄs message assembly logic without real sockets
    """

    def __init__(self, iterable: typing.Iterable[bytes]) -> None:
        # just accept some messages which then will be used as input
        self.iterable: typing.Iterable[bytes] = iterable
        super().__init__(None)

    def read(self) -> typing.Generator[bytes, None, None]:
        yield from (msg for msg in self.iterable)


class TestOutOfOrder(unittest.TestCase):
    def _spawn_test_server(self):
        self.server = MockUDPServer('127.0.0.1', 9999)
        self.server_thread = threading.Thread(target=self.server.send)
        self.server_thread.start()

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

    @unittest.skipIf(not is_linux(), "Skipping because Signal is not available on non unix systems!")
    def test_stream(self):
        # Test the UDP stream with real data
        with time_limit(1):  # make sure the function cannot run forever
            self._spawn_test_server()
            host = "127.0.0.1"
            port = 9999
            counter = 0
            with UDPStream(host, port) as stream:
                for msg in stream:
                    assert msg.decode()
                    counter += 1

                    if counter == 3:
                        break

            self.server_thread.join()

    def test_out_of_order(self):
        messages = [
            b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
            b'!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
            b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
            b'!AIVDM,2,2,9,A,F@V@00000000000,2*3D',
        ]
        counter = 0
        for msg in TestOutOfOrderByteStream(messages):
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
        for msg in TestOutOfOrderByteStream(messages):
            msg.decode()
            counter += 1
        assert counter == 2

    def test_split_nmea_header_method(self):
        stream = TestOutOfOrderByteStream([])
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
        for msg in TestOutOfOrderByteStream(messages):
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
        stream = TestOutOfOrderByteStream(messages)
        iter_steam = iter(stream)

        # assure that messages are deleted after they are yielded
        assert next(iter_steam).message_id == 1
        assert len(stream._queue) == 2
        assert next(iter_steam).message_id == 7
        assert len(stream._queue) == 1

    def test_three(self):
        messages = [
            b"!AIVDM,3,1,5,A,36KVnDh02wawaHPDA8T8h6tT8000t=AV=maD7?>BWiKIE@TR<2QfvaAF1ST4H31B,0*35",
            b"!AIVDM,3,2,5,A,8IBP:UFW<M0FVWS0DPK19@nh4UdS:OufWUIfPF5l1U9LILBn@9@F:41Q@U1EEOE3,0*1D",
            b"!AIVDM,3,3,5,A,j,0*79"
        ]
        stream = TestOutOfOrderByteStream(messages)
        iter_steam = iter(stream)
        assert next(iter_steam).decode()

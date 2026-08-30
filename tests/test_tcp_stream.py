import socket
from tests.utils.timeout import time_limit
from tests.utils.skip import is_linux
import threading
import unittest
from pyais.stream import SocketStream, TCPConnection

MESSAGES = [
    b"!AIVDM,1,1,,B,133S0:0P00PCsJ:MECBR0gv:0D8N,0*7F",
    b"!AIVDM,1,1,,A,4h2=a@Quho;O306WMpMIK<Q00826,0*42",
    b"!AIVDM,1,1,,A,402M3b@000Htt0K0Q0R3T<700t24,0*52",
    b"!AIVDM,1,1,,A,1>qc9ww000OkfS@MMI5004R60<0B,0*31",
    b"!AIVDM,1,1,,A,13P<GAh01pwM`GPDdu>T8SDV0@2c,0*7D",
    b"!AIVDM,1,1,,A,133ma5P0000Cj9lMG484pbN60D<P,0*42",
    b"!AIVDM,1,1,,B,13aBKV5P0qPFeWJMakbGjgv820SM,0*6E",
    b"!AIVDM,1,1,,A,15Mvsu000aqSG3RF;B?A@0v4082c,0*60",
    b"!AIVDM,1,1,,A,13aI9EwP?w<tSF0l4Q@>4?wvPl6=,0*38",
    b"!AIVDM,1,1,,A,15NJIs0P0?JeI0RGBjbCCwv:282W,0*2E",
    b"!AIVDM,1,1,,A,15Mw<ePP00ISvvpA8Hi<Mwv6082J,0*45",
    b"!AIVDM,1,1,,A,15MooR0P0SJe;2>GC2pdQOv:282b,0*0C",
]


def tcp_mock_server(host, port) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(1)

    try:
        while True:
            # wait for a connection
            conn, _ = sock.accept()
            if conn:
                # send all at once and then close
                for msg in MESSAGES:
                    conn.send(msg + b"\r\n")
                break
    finally:
        sock.close()


class TestTCPStream(unittest.TestCase):

    def _spawn_test_server(self):
        self.server_thread = threading.Thread(target=tcp_mock_server, args=("0.0.0.0", 55555))
        self.server_thread.start()

    def test_default_buf_size(self):
        self.assertEqual(TCPConnection.BUF_SIZE, 4096)

    def test_invalid_endpoint(self):
        with self.assertRaises(ConnectionRefusedError):
            TCPConnection("0.0.0.0", 55555)

    @unittest.skipIf(not is_linux(), "Skipping because Signal is not available on non unix systems!")
    @unittest.skipIf(True, "Skip for now, because there is a Threading problem")
    def test_tcp_stream(self):
        # limit execution time to 1 second in case of potential deadlocks -> prevent test from running forever
        with time_limit(2):
            self._spawn_test_server()

            with TCPConnection("0.0.0.0", 55555) as stream:
                for i, msg in enumerate(stream):
                    assert msg.decode()
                    # make sure all messages were received
                    if i == len(MESSAGES) - 1:
                        break

        self.server_thread.join()

    def test_many_small_chunks(self):
        """A user reported a bug where multipart messages were not processed when messages
        span more than a single recv() call.

        Issue: https://github.com/M0r13n/pyais/issues/213

        This was caused by prematurely yielding/dropping incomplete fragments.
        """
        class TestStream(SocketStream):

            msg = b"!AIVDM,2,1,7,B,54eJaT81vuKh<L=P000LDu8LF1:10D58dE<0000k48j976=d003UEBh00000,0*4A\r\n!AIVDM,2,2,7,B,00000000000,2*20\r\n"

            def __init__(self, *args, chunk_size=1, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                self.parts = [self.msg[i: i + chunk_size] for i in range(0, len(self.msg), chunk_size)]

            def recv(self) -> bytes:
                return self.parts.pop(0) if self.parts else b''

        for chunk_size in (1, 2, 3, 5, 7, len(TestStream.msg)):
            received = []
            for msg in TestStream(None, chunk_size=chunk_size):
                received.append(msg)

            self.assertEqual(len(received), 1)
            self.assertEqual(
                received[0].raw,
                b'!AIVDM,2,1,7,B,54eJaT81vuKh<L=P000LDu8LF1:10D58dE<0000k48j976=d003UEBh00000,0*4A\n!AIVDM,2,2,7,B,00000000000,2*20'
            )

    def test_unbounded_partial_growth(self):
        """Ensure that partial messages can not grow unboundedly."""
        class TestStream(SocketStream):

            msg = b"!AIVDM,2,1,7,B,54eJaT81vuKh<L=P000LDu8LF1:10D58dE<0000k48j976=d003UEBh00000,0*4A\r\n!AIVDM,2,2,7,B,00000000000,2*20\r\n"

            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                self.chunks = [b"A" * (self.MAX_PARTIAL_SIZE + 1), b"AAA\n" + self.msg]

            def recv(self) -> bytes:
                if self.chunks:
                    return self.chunks.pop(0)
                return b""

        received = []
        for msg in TestStream(None):
            received.append(msg)

        self.assertEqual(len(received), 1)
        self.assertEqual(
            received[0].raw,
            b'!AIVDM,2,1,7,B,54eJaT81vuKh<L=P000LDu8LF1:10D58dE<0000k48j976=d003UEBh00000,0*4A\n!AIVDM,2,2,7,B,00000000000,2*20'
        )

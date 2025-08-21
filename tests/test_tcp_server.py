import socket
import threading
import unittest
from unittest.mock import patch
from collections import deque

from pyais.stream import ClientConnection, TCPServer
from tests.utils.timeout import time_limit


class TestMessageProcessing(unittest.TestCase):
    """Test message processing functionality"""

    def setUp(self):
        """Set up server for message processing tests"""
        with patch('socket.socket'), patch('selectors.DefaultSelector'):

            self.server = TCPServer('127.0.0.1', 8080)
            self.server._message_queue = deque()

    def tearDown(self):
        self.server.close()
        return super().tearDown()

    def test_process_client_data_complete_messages(self):
        """Test processing complete messages"""
        client_data = ClientConnection(addr=('127.0.0.1', 12345))
        new_data = b'message1\nmessage2\nmessage3\n'

        self.server._process_client_data(client_data, new_data)

        # Should have 3 complete messages in queue
        self.assertEqual(len(self.server._message_queue), 3)
        self.assertEqual(self.server._message_queue.popleft(), b'message1\n')
        self.assertEqual(self.server._message_queue.popleft(), b'message2\n')
        self.assertEqual(self.server._message_queue.popleft(), b'message3\n')

        # No partial buffer should remain
        self.assertEqual(client_data.partial_buffer, b'')

    def test_process_client_data_partial_message(self):
        """Test processing data with partial message"""
        client_data = ClientConnection(addr=('127.0.0.1', 12345))
        new_data = b'message1\nmessage2\npartial'

        self.server._process_client_data(client_data, new_data)

        # Should have 2 complete messages in queue
        self.assertEqual(len(self.server._message_queue), 2)
        self.assertEqual(self.server._message_queue.popleft(), b'message1\n')
        self.assertEqual(self.server._message_queue.popleft(), b'message2\n')

        # Partial message should be in buffer
        self.assertEqual(client_data.partial_buffer, b'partial')

    def test_process_client_data_continuing_partial(self):
        """Test processing data that continues a partial message"""
        client_data = ClientConnection(
            addr=('127.0.0.1', 12345),
            partial_buffer=b'partial_start'
        )
        new_data = b'_end\nnew_message\n'

        self.server._process_client_data(client_data, new_data)

        # Should have 2 complete messages
        self.assertEqual(len(self.server._message_queue), 2)
        self.assertEqual(self.server._message_queue.popleft(), b'partial_start_end\n')
        self.assertEqual(self.server._message_queue.popleft(), b'new_message\n')

        # No partial buffer should remain
        self.assertEqual(client_data.partial_buffer, b'')

    def test_process_client_data_empty_data(self):
        """Test processing empty data"""
        client_data = ClientConnection(addr=('127.0.0.1', 12345))

        self.server._process_client_data(client_data, b'')

        # Should have no messages and no changes
        self.assertEqual(len(self.server._message_queue), 0)
        self.assertEqual(client_data.partial_buffer, b'')

    def test_process_client_data_only_newlines(self):
        """Test processing data with only newlines"""
        client_data = ClientConnection(addr=('127.0.0.1', 12345))
        new_data = b'\n\n\n'

        self.server._process_client_data(client_data, new_data)

        # Should have 3 empty line messages
        self.assertEqual(len(self.server._message_queue), 3)
        for _ in range(3):
            self.assertEqual(self.server._message_queue.popleft(), b'\n')

    def test_process_client_data_no_newlines(self):
        """Test processing data with no newlines"""
        client_data = ClientConnection(addr=('127.0.0.1', 12345))
        new_data = b'no newlines here'

        self.server._process_client_data(client_data, new_data)

        # Should have no complete messages
        self.assertEqual(len(self.server._message_queue), 0)
        # All data should be in partial buffer
        self.assertEqual(client_data.partial_buffer, b'no newlines here')


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


def tcp_mock_client(host, port) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    try:
        # send all at once and then close
        for msg in MESSAGES:
            sock.send(msg + b"\r\n")
    finally:
        sock.close()


class TestIntegration(unittest.TestCase):
    """Integration tests for TCPServer"""

    def _spawn_test_client(self):
        self.client_thread = threading.Thread(target=tcp_mock_client, args=("0.0.0.0", 55555))
        self.client_thread.start()

    def test_full_message_flow(self):
        """Test complete message processing flow"""
        # limit execution time to 1 second in case of potential deadlocks -> prevent test from running forever
        with time_limit(2):
            with TCPServer("0.0.0.0", 55555) as server:
                self._spawn_test_client()

                received = []
                for i, msg in enumerate(server):
                    received.append(msg.decode())
                    if i == 11:
                        break

        self.assertEqual(received[0].mmsi, 205045800)
        self.assertEqual(received[1].mmsi, 2320706)
        self.assertEqual(received[2].mmsi, 2573225)
        self.assertEqual(received[3].mmsi, 999999999)
        self.assertEqual(received[4].mmsi, 235083591)
        self.assertEqual(received[5].mmsi, 205351190)
        self.assertEqual(received[6].mmsi, 244620184)
        self.assertEqual(received[7].mmsi, 366984180)
        self.assertEqual(received[8].mmsi, 244730199)
        self.assertEqual(received[9].mmsi, 367434220)
        self.assertEqual(received[10].mmsi, 366988470)
        self.assertEqual(received[11].mmsi, 366868360)

        self.client_thread.join()


if __name__ == '__main__':
    # Run specific test categories
    unittest.main(verbosity=2)

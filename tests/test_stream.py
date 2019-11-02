import unittest
from pyais.messages import NMEAMessage
from pyais.stream import TCPStream, FileReaderStream
import socket
import threading


class MockSocket:
    """
    Mock socket that mimics a valid NMEA Stream Server
    """

    def __init__(self, messages, host="127.0.0.1", port=12345):
        self.messages = messages
        self.host = host
        self.port = port
        self.sock = None

    def start_sending(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        # wait for connection
        self.sock.listen()
        conn, addr = self.sock.accept()
        with conn:
            # send messages
            for msg in self.messages:
                conn.sendall(msg + b"\r\n")
            # wait for the client to close the connection
        self.sock.close()


def start_mock_server(messages, port):
    mock = MockSocket(messages, port=port)
    mock.start_sending()


class TestTCPStream(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_server_thread = None

    def tearDown(self) -> None:
        """
        Await open threads
        """
        if self.mock_server_thread:
            self.mock_server_thread.join()

    def test_default_buf_size(self):
        with TCPStream() as stream:
            assert stream.BUF_SIZE == 4096

    def test_socket(self):
        messages = [
            b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C",
            b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05",
            b"!AIVDM,1,1,,A,15NJQiPOl=G?m:bE`Gpt<aun00S8,0*56"
        ]
        self.mock_server_thread = threading.Thread(target=start_mock_server, args=(messages, 12345))
        self.mock_server_thread.start()

        with TCPStream("127.0.0.1", 12345) as stream:
            received = list(stream._iter_messages())

        assert received == messages

    def test_assemble_messages(self):
        messages = [
            b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08",
            b"!AIVDM,2,2,4,A,000000000000000,2*20",
            b"!AIVDM,2,1,9,B,53nFBv01SJ<thHp6220H4heHTf2222222222221?50:454o<`9QSlUDp,0*09",
            b"!AIVDM,2,2,9,B,888888888888880,2*2E",
            b"!AIVDM,2,1,6,B,56:fS:D0000000000008v0<QD4r0`T4v3400000t0`D147?ps1P00000,0*3D",
            b"!AIVDM,2,2,6,B,000000000000008,2*29"
        ]

        self.mock_server_thread = threading.Thread(target=start_mock_server, args=(messages, 12346))
        self.mock_server_thread.start()

        with TCPStream("127.0.0.1", 12346) as stream:
            received = list(stream)

        assert len(received) == 3
        for msg in received:
            assert isinstance(msg, NMEAMessage)
            assert msg.is_multi

    def test_invalid_endpoint(self):
        with self.assertRaises(ValueError):
            TCPStream("127.0.0.1", 55555)


class TestFileReaderStream(unittest.TestCase):

    def test_reader(self):
        filename = "tests/ais_test_messages"
        messages = [msg for msg in FileReaderStream(filename)]
        assert len(messages) == 6
        for msg in messages:
            assert type(msg) == NMEAMessage
            assert msg.is_valid
            assert msg.decode().content is not None

    def test_invalid_filename(self):
        with self.assertRaises(ValueError):
            FileReaderStream("does not exist")

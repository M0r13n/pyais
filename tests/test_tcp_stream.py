import unittest
from pyais.messages import NMEAMessage, AISMessage
from pyais.stream import TCPStream


class TestTCPStream(unittest.TestCase):
    def test_default_buf_size(self):
        self.assertEqual(TCPStream.BUF_SIZE, 4096)

    def test_socket_with_real_data(self):
        for i, msg in enumerate(TCPStream('ais.exploratorium.edu')):
            if i >= 10:
                break

            self.assertTrue(isinstance(msg, NMEAMessage))
            self.assertTrue(isinstance(msg.decode(), AISMessage))

    def test_invalid_endpoint(self):
        with self.assertRaises(ValueError):
            TCPStream("127.0.0.1", 55555)

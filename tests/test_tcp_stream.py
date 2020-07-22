import unittest
from pyais.stream import TCPStream


class TestTCPStream(unittest.TestCase):
    def test_default_buf_size(self):
        self.assertEqual(TCPStream.BUF_SIZE, 4096)

    def test_invalid_endpoint(self):
        with self.assertRaises(ConnectionRefusedError):
            TCPStream("127.0.0.1", 55555)

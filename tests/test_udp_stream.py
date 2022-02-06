import socket
import threading
import time
import unittest

from pyais.stream import UDPReceiver
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


class TestOutOfOrder(unittest.TestCase):
    def _spawn_test_server(self):
        self.server = MockUDPServer('127.0.0.1', 9999)
        self.server_thread = threading.Thread(target=self.server.send)
        self.server_thread.start()

    @unittest.skipIf(not is_linux(), "Skipping because Signal is not available on non unix systems!")
    def test_stream(self):
        # Test the UDP stream with real data
        with time_limit(1):  # make sure the function cannot run forever
            self._spawn_test_server()
            host = "127.0.0.1"
            port = 9999
            counter = 0
            with UDPReceiver(host, port) as stream:
                for msg in stream:
                    assert msg.decode()
                    counter += 1

                    if counter == 3:
                        break

            self.server_thread.join()

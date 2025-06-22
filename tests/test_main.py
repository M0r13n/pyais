from io import StringIO
import sys
import unittest

from pyais.main import decode_single, decode_from_file, create_parser, decode_from_socket


class TestMainApp(unittest.TestCase):

    def test_decode_single(self):
        class DemoNamespace:
            messages = ["!AIVDM,1,1,,B,91b55wi;hbOS@OdQAC062Ch2089h,0*30"]
            out_file = StringIO()
            json = False

        assert decode_single(DemoNamespace()) == 0

    def test_decode_single_multi(self):
        class DemoNamespace:
            messages = [
                '!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
                '!AIVDM,2,2,1,A,F@V@00000000000,2*35',
                '!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
                '!AIVDM,2,2,9,A,F@V@00000000000,2*3D',
            ]
            out_file = StringIO()
            json = False

        assert decode_single(DemoNamespace()) == 0

    def test_decode_from_file(self):
        class DemoNamespace:
            in_file = open("tests/ais_test_messages", "rb")
            out_file = StringIO()
            json = False

        assert decode_from_file(DemoNamespace()) == 0

    def test_parser(self):
        parser = create_parser()

        # By default the program should read from stdin (which is None)
        ns = parser.parse_args([])
        assert ns.func == decode_from_file
        assert ns.in_file is None

        # But this can be overwritten to any file that exists
        ns = parser.parse_args(["-f", "tests/ais_test_messages"])
        assert ns.func == decode_from_file
        assert ns.in_file.name == "tests/ais_test_messages"
        ns.in_file.close()

        # If the file does not exist an error is thrown
        with self.assertRaises(SystemExit):
            parser.parse_args(["-f", "invalid"])

        # Additionally it is possible to decode messages passed as a list
        ns = parser.parse_args(["single", "123345"])
        assert ns.func == decode_single
        assert ns.messages == ["123345"]

        # In fact the user can pass as many messages as he likes
        ns = parser.parse_args(["single", "A", "B", "C", "and more"])
        assert ns.func == decode_single
        assert ns.messages == ["A", "B", "C", "and more"]

        # But if the user passes no messages an error is thrown
        with self.assertRaises(SystemExit):
            parser.parse_args(["single"])

        # But is also possible to connect to a UDP socket - which is default for socket
        ns = parser.parse_args(["socket", "localhost", "12345"])
        assert ns.func == decode_from_socket
        assert ns.destination == "localhost"
        assert ns.port == 12345
        assert ns.type == "udp"

        # Or a TCP socket
        ns = parser.parse_args(["socket", "localhost", "12345", "--type", "tcp"])
        assert ns.func == decode_from_socket
        assert ns.destination == "localhost"
        assert ns.port == 12345
        assert ns.type == "tcp"

        # But it can not be nothing else
        with self.assertRaises(SystemExit):
            parser.parse_args(["socket", "localhost", "12345", "--type", "something else"])

        # The output is written to STDOUT by default for every mode
        ns = parser.parse_args([])
        assert ns.out_file == sys.stdout
        ns = parser.parse_args(["socket", "localhost", "12345", "--type", "tcp"])
        assert ns.out_file == sys.stdout
        ns = parser.parse_args(["single", "123345"])
        assert ns.out_file == sys.stdout

        # But can be redirected to any file
        ns = parser.parse_args(["-o", "/tmp/foo.bar"])
        assert ns.out_file.name == "/tmp/foo.bar"
        ns.out_file.close()

        ns = parser.parse_args(["-o", "/tmp/foo.bar", "socket", "localhost", "12345", "--type", "tcp"])
        assert ns.out_file.name == "/tmp/foo.bar"
        ns.out_file.close()

        ns = parser.parse_args(["-o", "/tmp/foo.bar", "single", "123345"])
        assert ns.out_file.name == "/tmp/foo.bar"
        ns.out_file.close()

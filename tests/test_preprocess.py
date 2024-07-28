import pathlib
import re
import textwrap
import unittest
from unittest.mock import patch

from pyais.stream import FileReaderStream, PreprocessorProtocol, TCPConnection, UDPReceiver


# This serves as an example for a custom format.
# Taken from: https://github.com/M0r13n/pyais/issues/144
FILE_CONTENT = textwrap.dedent("""
    [2024-07-19 08:45:27.141] !AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23
    [2024-07-19 08:45:30.074] !AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F
    [2024-07-19 08:45:35.007] !AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B
    [2024-07-19 08:45:35.301] !AIVDM,1,1,,B,13eaJF0P00Qd388Eew6aagvH85Ip,0*45
    [2024-07-19 08:45:40.021] !AIVDM,1,1,,A,14eGrSPP00ncMJTO5C6aBwvP2D0?,0*7A
    [2024-07-19 09:00:00.001] !AIVDO,2,1,,A,8=?eN>0000:C=4B1KTTsgLoUelGetEo0FoWr8jo=?045TNv5Tge6sAUl4MKWo,0*5F
    [2024-07-19 09:00:00.002] !AIVDO,2,2,,A,vhOL9NIPln:BsP0=BLOiiCbE7;SKsSJfALeATapHfdm6Tl,2*79
    [2024-07-19 08:45:40.074] !AIVDM,1,1,,A,15MrVH0000KH<:V:NtBLoqFP2H9:,0*2F
""")


class Preprocessor(PreprocessorProtocol):
    """Dummy Preprocessor that handles the format defined above"""

    def __init__(self) -> None:
        self.last_meta = None

    def process(self, line: bytes):
        nmea_message = re.search(b".* (.*)", line).group(1)
        self.last_meta = re.search(b"(.*) .*", line).group(1)
        return nmea_message

    def get_meta(self):
        return self.last_meta


class PreprocessFileStreamTestCase(unittest.TestCase):
    """Test case for file stream preprocessing."""

    TEST_READER_FILE = pathlib.Path(__file__).parent.joinpath('preprocess.ais')

    @classmethod
    def setUpClass(cls):
        # Create a test file to read
        with open(cls.TEST_READER_FILE, 'w') as fd:
            fd.write(FILE_CONTENT)

    @classmethod
    def tearDownClass(cls):
        # Remove the test file again
        cls.TEST_READER_FILE.unlink(missing_ok=True)

    def test_that_custom_format_can_be_parsed(self):
        results, preprocessor = [], Preprocessor()

        with FileReaderStream(self.TEST_READER_FILE, preprocessor=preprocessor) as stream:
            for msg in stream:
                decoded = msg.decode()
                results.append((decoded, preprocessor.get_meta()))

        self.assertEqual(len(results), 7)
        self.assertEqual(results[0][0].mmsi, 227006760)
        self.assertEqual(results[0][1], b"[2024-07-19 08:45:27.141]")
        self.assertEqual(results[1][0].mmsi, 205448890)
        self.assertEqual(results[1][1], b"[2024-07-19 08:45:30.074]")
        self.assertEqual(results[2][0].mmsi, 786434)
        self.assertEqual(results[2][1], b"[2024-07-19 08:45:35.007]")
        self.assertEqual(results[3][0].mmsi, 249191000)
        self.assertEqual(results[3][1], b"[2024-07-19 08:45:35.301]")
        self.assertEqual(results[4][0].mmsi, 316013198)
        self.assertEqual(results[4][1], b"[2024-07-19 08:45:40.021]")
        self.assertEqual(results[5][0].mmsi, 888888888)
        self.assertEqual(results[5][1], b"[2024-07-19 09:00:00.002]")
        self.assertEqual(results[6][0].mmsi, 366913120)
        self.assertEqual(results[6][1], b"[2024-07-19 08:45:40.074]")


class PreprocessUDPTestCase(unittest.TestCase):
    """Test case for UDP preprocessing."""

    @patch('pyais.stream.socket')
    def test_that_custom_format_can_be_parsed(self, _):
        results, preprocessor = [], Preprocessor()

        with UDPReceiver('0.0.0.0', 1234, preprocessor=preprocessor) as stream:
            stream.recv = lambda: FILE_CONTENT.encode()

            for i, msg in enumerate(stream):
                decoded = msg.decode()
                results.append((decoded, preprocessor.get_meta()))

                if i >= 6:
                    break

        self.assertEqual(len(results), 7)
        self.assertEqual(results[0][0].mmsi, 227006760)
        self.assertEqual(results[0][1], b"[2024-07-19 08:45:27.141]")
        self.assertEqual(results[1][0].mmsi, 205448890)
        self.assertEqual(results[1][1], b"[2024-07-19 08:45:30.074]")
        self.assertEqual(results[2][0].mmsi, 786434)
        self.assertEqual(results[2][1], b"[2024-07-19 08:45:35.007]")
        self.assertEqual(results[3][0].mmsi, 249191000)
        self.assertEqual(results[3][1], b"[2024-07-19 08:45:35.301]")
        self.assertEqual(results[4][0].mmsi, 316013198)
        self.assertEqual(results[4][1], b"[2024-07-19 08:45:40.021]")
        self.assertEqual(results[5][0].mmsi, 888888888)
        self.assertEqual(results[5][1], b"[2024-07-19 09:00:00.002]")
        self.assertEqual(results[6][0].mmsi, 366913120)
        self.assertEqual(results[6][1], b"[2024-07-19 08:45:40.074]")


class PreprocessTCPTestCase(unittest.TestCase):
    """Test case for TCP preprocessing."""

    @patch('pyais.stream.socket')
    def test_that_custom_format_can_be_parsed(self, _):
        results, preprocessor = [], Preprocessor()

        with TCPConnection('0.0.0.0', 1234, preprocessor=preprocessor) as stream:
            stream.recv = lambda: FILE_CONTENT.encode()

            for i, msg in enumerate(stream):
                decoded = msg.decode()
                results.append((decoded, preprocessor.get_meta()))

                if i >= 6:
                    break

        self.assertEqual(len(results), 7)
        self.assertEqual(results[0][0].mmsi, 227006760)
        self.assertEqual(results[0][1], b"[2024-07-19 08:45:27.141]")
        self.assertEqual(results[1][0].mmsi, 205448890)
        self.assertEqual(results[1][1], b"[2024-07-19 08:45:30.074]")
        self.assertEqual(results[2][0].mmsi, 786434)
        self.assertEqual(results[2][1], b"[2024-07-19 08:45:35.007]")
        self.assertEqual(results[3][0].mmsi, 249191000)
        self.assertEqual(results[3][1], b"[2024-07-19 08:45:35.301]")
        self.assertEqual(results[4][0].mmsi, 316013198)
        self.assertEqual(results[4][1], b"[2024-07-19 08:45:40.021]")
        self.assertEqual(results[5][0].mmsi, 888888888)
        self.assertEqual(results[5][1], b"[2024-07-19 09:00:00.002]")
        self.assertEqual(results[6][0].mmsi, 366913120)
        self.assertEqual(results[6][1], b"[2024-07-19 08:45:40.074]")


if __name__ == '__main__':
    unittest.main()

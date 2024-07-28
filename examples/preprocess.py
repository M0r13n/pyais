import pathlib
import re
import textwrap

from pyais.stream import FileReaderStream, PreprocessorProtocol

filename = pathlib.Path(__file__).parent.joinpath('preprocess.ais')

# Create a sample file
with open(filename, 'w') as fd:
    fd.write(textwrap.dedent("""
        [2024-07-19 08:45:27.141] !AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23
        [2024-07-19 08:45:30.074] !AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F
        [2024-07-19 08:45:35.007] !AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B
        [2024-07-19 08:45:35.301] !AIVDM,1,1,,B,13eaJF0P00Qd388Eew6aagvH85Ip,0*45
        [2024-07-19 08:45:40.021] !AIVDM,1,1,,A,14eGrSPP00ncMJTO5C6aBwvP2D0?,0*7A
        [2024-07-19 09:00:00.001] !AIVDO,2,1,,A,8=?eN>0000:C=4B1KTTsgLoUelGetEo0FoWr8jo=?045TNv5Tge6sAUl4MKWo,0*5F
        [2024-07-19 09:00:00.002] !AIVDO,2,2,,A,vhOL9NIPln:BsP0=BLOiiCbE7;SKsSJfALeATapHfdm6Tl,2*79
        [2024-07-19 08:45:40.074] !AIVDM,1,1,,A,15MrVH0000KH<:V:NtBLoqFP2H9:,0*2F
    """))


class Preprocessor(PreprocessorProtocol):
    """A custom preprocessor class that implements the PreprocessorProtocol.
    This class implements the parsing of a custom meta data format [2024-07-19 08:45:40.074]."""

    def __init__(self) -> None:
        self.last_meta = None

    def process(self, line: bytes):
        nmea_message = re.search(b".* (.*)", line).group(1)
        self.last_meta = re.search(b"(.*) .*", line).group(1)
        return nmea_message

    def get_meta(self):
        return self.last_meta


preprocessor = Preprocessor()

with FileReaderStream(str(filename), preprocessor=preprocessor) as stream:
    for msg in stream:
        decoded = msg.decode()
        print(decoded, preprocessor.get_meta())

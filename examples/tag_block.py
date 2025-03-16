"""How to work with optional tag blocks?"""
import pathlib
from pyais.decode import decode_nmea_and_ais
from pyais.messages import TagBlock
from pyais.stream import FileReaderStream

# Tag blocks for single messages
msg = b'\\g:1-2-73874,n:157036,s:r003669945,c:12415440354*A\\!AIVDM,1,1,,B,15N4cJ005Jrek0H@9nDW5608EP,013'

# The regular `decode()` function only returns decoded AIS messages.
# Thus, use `decode_nmea_and_ais` to get both: the NMEA sentence and the AIS payload
nmea, ais = decode_nmea_and_ais(msg)
if nmea.tag_block:
    # not all messages contain a tag block
    # also it is evaluated lazily
    nmea.tag_block.init()

print(nmea)
print(nmea.tag_block.asdict())

# Tag blocks for streams
# All streaming interfaces support tag blocks

filename = pathlib.Path(__file__).parent.joinpath('sample.ais')

with FileReaderStream(filename) as stream:
    for nmea in stream:
        if nmea.tag_block:
            # again: not all messages have a tag block
            nmea.tag_block.init()
            print(nmea.tag_block.asdict())

        decoded = nmea.decode()

# You can also create tag blocks as either bytes or strings
tb_bytes = TagBlock.create(
    receiver_timestamp=12415440354,
    source_station='foobar',
    line_count=157036
)

tb_str = TagBlock.create_str(
    receiver_timestamp=12415440354,
    source_station='foobar',
    line_count=157036
)

print(tb_bytes, tb_str, sep='\n')

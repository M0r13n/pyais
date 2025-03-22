"""
The following example shows how to read and parse AIS messages from a file.

When reading a file, the following things are important to know:

- lines that begin with a `#` are ignored
- invalid messages are skipped
- invalid lines are skipped
"""
import pathlib

from pyais.stream import FileReaderStream

filename = pathlib.Path(__file__).parent.joinpath('sample.ais')

with FileReaderStream(str(filename)) as stream:
    for nmea_msg in stream:
        # Assemble the NMEA message layer and decode AIS payload
        ais_data = nmea_msg.decode()

        # multi-line NMEA sentences
        print(f"NMEA message is multi part: {'yes' if nmea_msg.is_multi else 'no'} ")

        # tag blocks
        if nmea_msg.tag_block:
            nmea_msg.tag_block.init()
            tb_dict = nmea_msg.tag_block.asdict()
            print(f"source_station: {tb_dict.get('source_station', 'n.a.')}")

        #  gatehouse wrappers
        if nmea_msg.wrapper_msg is not None:  # <= optional gatehouse wrapper
            print('Gatehouse')
            print('Country', nmea_msg.wrapper_msg.country)
            print('Online', nmea_msg.wrapper_msg.online_data)
            print('PSS', nmea_msg.wrapper_msg.pss)
            print('Region', nmea_msg.wrapper_msg.region)
            print('Timestamp', nmea_msg.wrapper_msg.timestamp)

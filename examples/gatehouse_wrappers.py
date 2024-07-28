# Some AIS messages have so-called Gatehouse wrappers.
# These encapsulating messages contain extra information, such as time and checksums.
# These look roughly like this: $PGHP,1,2020,12,31,23,59,58,239,0,0,0,1,2C*5B

import pathlib

from pyais.stream import FileReaderStream

filename = pathlib.Path(__file__).parent.joinpath('gatehouse.nmea')

with FileReaderStream(str(filename)) as stream:
    for msg in stream:
        print('*' * 80)
        if msg.wrapper_msg is not None:  # <= optional gatehouse wrapper
            print('Country', msg.wrapper_msg.country)
            print('Online', msg.wrapper_msg.online_data)
            print('PSS', msg.wrapper_msg.pss)
            print('Region', msg.wrapper_msg.region)
            print('Timestamp', msg.wrapper_msg.timestamp)
        decoded = msg.decode()
        print(decoded)

from pyais.exceptions import UnknownMessageException
from pyais import FileReaderStream
from collections import defaultdict
import time
import pathlib
import ais.stream
import json
import ais.compatibility.gpsd

file = pathlib.Path(__file__).parent.joinpath('../tests/nmea-sample')
stats = defaultdict(lambda: 0)
start = time.time()

with open(file) as inf:
    for i, msg in enumerate(ais.stream.decode(inf)):
        stats[msg['id']] += 1


print(stats)
print(f'Decoded {i} NMEA AIS messages in {time.time() - start: .2f}s')

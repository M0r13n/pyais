import pathlib
import time
from collections import defaultdict
from pyais import FileReaderStream
from pyais.exceptions import UnknownMessageException

file = pathlib.Path(__file__).parent.joinpath('../tests/nmea-sample')


def bench():
    stats = defaultdict(lambda: 0)
    start = time.time()

    for i, msg in enumerate(FileReaderStream(file), 1):
        try:
            decoded = msg.decode()
            stats[decoded.msg_type] += 1
        except UnknownMessageException:
            stats['errors'] += 1

    print(stats)
    print(f'Decoded {i} NMEA AIS messages in {time.time() - start: .2f}s')


for round in range(5):
    print(f'Round #{round}')
    bench()

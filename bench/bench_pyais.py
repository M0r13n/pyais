#!/usr/bin/env python3
import pathlib
import time
from collections import defaultdict
from pyais import FileReaderStream
from pyais.exceptions import UnknownMessageException

file = pathlib.Path(__file__).parent.joinpath('../tests/nmea-sample')
file_long = pathlib.Path('/tmp/' + file.name + '-long')
file_long.write_bytes(b"")


for _ in range(30):
    with open(file_long, 'ab') as fd:
        fd.write(file.read_bytes())


def bench() -> None:
    stats = defaultdict(lambda: 0)
    start = time.time()

    for i, msg in enumerate(FileReaderStream(file_long), 1):
        try:
            decoded = msg.decode()
            stats[decoded.msg_type] += 1
        except UnknownMessageException:
            stats['errors'] += 1

    print(stats)
    tot_time = time.time() - start
    print(f'Decoded {i} NMEA AIS messages in {tot_time: .2f}s ({i / tot_time:,.0f} msgs/s)')


for round in range(5):
    print(f'Round #{round}')
    bench()

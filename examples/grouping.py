import queue
from pyais.stream import FileReaderStream, TagBlockQueue
import pathlib

filename = pathlib.Path(__file__).parent.joinpath('sample.ais')


with FileReaderStream(str(filename), tbq=TagBlockQueue()) as stream:
    tbq = stream.tbq

    for msg in stream:
        try:
            print(tbq.get_nowait())
        except queue.Empty:
            pass

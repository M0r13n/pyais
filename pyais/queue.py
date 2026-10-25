import queue
import threading
import typing

from pyais.messages import AISSentence, NMEASentence
from pyais.stream import NMEAAssembler, TagBlockQueue


class NMEAQueue(queue.Queue[AISSentence]):
    """Assembles complete NMEA sentences.

    Single-line sentences are added to the queue directly. Multi-line sentences
    are buffered until all fragments are available, after which they are added to the queue.

    Assembly is delegated to NMEAAssembler, the same logic the stream classes use.
    put_line() may be called from several producer threads."""

    def __init__(self, maxsize: int = 0, tbq: typing.Optional[TagBlockQueue] = None) -> None:
        super().__init__(maxsize)
        self.assembler = NMEAAssembler(tbq)
        # The assembler keeps state between lines and is not thread-safe.
        self._feed_lock = threading.Lock()

    def put(self, item: object, block: bool = True, timeout: typing.Optional[float] = None) -> None:
        """This method only exists to please mypy. Use put_line instead."""
        raise ValueError('do not call NMEAQueue.put() directly. Use NMEAQueue.put_line() instead!')

    def put_line(self, line: bytes, block: bool = True, timeout: typing.Optional[float] = None) -> None:
        """Put a line of raw bytes, as part of an NMEA sentence, into the queue."""
        with self._feed_lock:
            msg = self.assembler.feed(line)
        # Enqueue outside the lock: a full queue may block here.
        if msg is not None:
            super().put(msg, block, timeout)

    def get_or_none(self) -> typing.Optional[NMEASentence]:
        """Non-blocking helper method to retrieve the last message, if one is available"""
        try:
            return self.get(block=False)
        except queue.Empty:
            return None

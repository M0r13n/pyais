
import queue
import typing

from pyais.exceptions import InvalidNMEAMessageException, NonPrintableCharacterException, UnknownMessageException
from pyais.messages import AISSentence, GatehouseSentence, NMEASentence, NMEASentenceFactory
from pyais.stream import TagBlockQueue


class NMEAQueue(queue.Queue[AISSentence]):
    """Assembles complete NMEA sentences.

    Single-line sentences are added to the queue directly. Multi-line sentences
    are buffered until all fragments are available, after which they are added to the queue."""

    def __init__(self, maxsize: int = 0, tbq: typing.Optional[TagBlockQueue] = None) -> None:
        super().__init__(maxsize)
        self.tbq = tbq
        self.buffer: typing.Dict[typing.Tuple[int, str], typing.List[typing.Optional[AISSentence]]] = {}
        self.last_wrapper: typing.Optional[GatehouseSentence] = None

    def __add_to_tbq(self, sentence: NMEASentence) -> None:
        if not self.tbq:
            # Tag Block Queue not defined. Do nothing.
            return
        self.tbq.put_sentence(sentence)

    def put(self, item: object, block: bool = True, timeout: typing.Optional[float] = None) -> None:
        """This method only exists to please mypy. Use put_line instead."""
        raise ValueError('do not call NMEAQueue.put() directly. Use NMEAQueue.put_line() instead!')

    def put_line(self, line: bytes, block: bool = True, timeout: typing.Optional[float] = None) -> None:
        """Put a line of raw bytes, as part of an NMEA sentence, into the queue."""
        try:
            sentence = NMEASentenceFactory.produce(line)
            self.__add_to_tbq(sentence)
            if sentence.TYPE == GatehouseSentence.TYPE:
                # Remember gatehouse wrappers for the next AIS message
                sentence = typing.cast(GatehouseSentence, sentence)
                self.last_wrapper = sentence
                return None
        except (InvalidNMEAMessageException, NonPrintableCharacterException, UnknownMessageException, IndexError):
            # Be gentle and just skip invalid messages
            return None

        if not sentence.TYPE == AISSentence.TYPE:
            return None

        sentence = typing.cast(AISSentence, sentence)

        if sentence.is_single:
            if self.last_wrapper:
                # Check if there was a wrapper message right before this line
                sentence.wrapper_msg = self.last_wrapper
                self.last_wrapper = None
            super().put(sentence, block, timeout)
        else:
            # Instead of None use -1 as a seq_id
            seq_id = sentence.seq_id
            if seq_id is None:
                seq_id = -1

            # seq_id and channel make a unique stream
            slot = (seq_id, sentence.channel)

            if slot not in self.buffer:
                # Create a new array in the buffer that has enough space for all fragments
                self.buffer[slot] = [None, ] * max(sentence.fragment_count, 0xff)

            self.buffer[slot][sentence.frag_num - 1] = sentence
            msg_parts = self.buffer[slot][0:sentence.fragment_count]

            # Check if all fragments are found
            not_none_parts = [m for m in msg_parts if m is not None]
            if len(not_none_parts) == sentence.fragment_count:
                # Assemble the full message and clear the buffer
                full = AISSentence.assemble_from_iterable(not_none_parts)
                del self.buffer[slot]
                super().put(full, block, timeout)

    def get_or_none(self) -> typing.Optional[NMEASentence]:
        """Non-blocking helper method to retrieve the last message, if one is available"""
        try:
            return self.get(block=False)
        except queue.Empty:
            return None

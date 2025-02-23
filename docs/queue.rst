NMEAQueue: Assembling Complete NMEA Sentences
=============================================

The ``NMEAQueue`` class provides a robust mechanism for assembling and managing NMEA sentences, including both single-line and multi-line messages. It is designed to handle AIS messages and integrates with ``TagBlockQueue`` for processing tag blocks.

Features
--------
- **Single-Line Sentence Handling**: Single-line NMEA sentences are added directly to the queue.
- **Multi-Line Sentence Assembly**: Multi-line sentences are buffered until all fragments are available, after which they are assembled and added to the queue.
- **Gatehouse Wrappers**: Supports gatehouse wrappers for AIS messages, associating them with the next AIS message in the sequence.
- **Graceful Error Handling**: Invalid or malformed sentences are skipped without interrupting the processing flow.
- **Integration with TagBlockQueue**: If a ``TagBlockQueue`` instance is provided, sentences are added to it for tag block processing.

Constructor
-----------
.. code-block:: python

    NMEAQueue(maxsize: int = 0, tbq: typing.Optional[TagBlockQueue] = None)

- ``maxsize``: The maximum size of the queue. Defaults to 0 (unlimited).
- ``tbq``: An optional ``TagBlockQueue`` instance for handling tag blocks.

Methods
-------
- ``put_line(line: bytes, block: bool = True, timeout: typing.Optional[float] = None)``: Adds a line of raw bytes to the queue. This method processes the line, handles multi-line assembly, and integrates with ``TagBlockQueue`` if provided.
- ``get_or_none() -> typing.Optional[NMEASentence]``: Retrieves the last message from the queue in a non-blocking manner. Returns ``None`` if the queue is empty.

Example Usage
-------------
.. code-block:: python

    from pyais.stream import TagBlockQueue
    from my_module import NMEAQueue

    # Initialize a TagBlockQueue
    tbq = TagBlockQueue()

    # Create an NMEAQueue instance
    queue = NMEAQueue(tbq=tbq)

    # Add a line of raw bytes to the queue
    queue.put_line(b"!AIVDM,1,1,,A,15N:;R0P00PD;88MD5NS8v2P00,0*3C")

    # Retrieve the assembled sentence
    sentence = queue.get_or_none()
    if sentence:
        print(sentence)

Notes
-----
- **Error Handling**: The ``put_line`` method skips invalid messages (e.g., malformed sentences or those with non-printable characters) without raising exceptions.
- **Buffering**: Multi-line sentences are buffered using a unique key based on the sequence ID and channel. Once all fragments are received, the sentence is assembled and added to the queue.

This class simplifies the process of handling NMEA sentences, making it easier to work with AIS data streams in real-time applications.

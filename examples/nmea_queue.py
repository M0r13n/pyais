import pathlib
from pyais.queue import NMEAQueue


if __name__ == '__main__':

    # Example 1: use a queue to read NMEA/AIS messages from a file
    filename = pathlib.Path(__file__).parent.joinpath('../tests/mixed.txt')

    q = NMEAQueue()

    with open(filename, 'rb') as fd:
        for line in fd.readlines():
            q.put_line(line)

            if x := q.get_or_none():
                print(x.decode())
            else:
                print(line)

    # Example 2: put lines into the queue manually

    q = NMEAQueue()
    q.qsize()  # Initially empty

    # Raw text.
    q.put_line(b'Hello there!')
    q.qsize()  # Still empty

    # Put a multi-line message into the queue
    q.put_line(b'!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C')
    q.put_line(b'!AIVDM,2,2,1,A,88888888880,2*25')
    q.qsize()  # Returns 1
    q.get_or_none()
    q.qsize()  # Empty again

    # A multi-line message with tag blocks
    q.put_line(b'\\g:1-2-73874*A\\!AIVDM,1,1,,A,15MrVH0000KH<:V:NtBLoqFP2H9:,0*2F')
    q.put_line(b'\\g:2-2-73874,n:157037*A\\!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B')
    q.get_or_none()

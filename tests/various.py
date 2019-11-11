"""
This are some debugging or performance methods and are not valid testcases.
"""
from pyais import NMEAMessage
from pyais import TCPStream, FileReaderStream
import timeit
import time
import random

MESSAGES = [
    NMEAMessage(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C"),
    NMEAMessage(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05"),
    NMEAMessage(b"!AIVDM,1,1,,A,15NJQiPOl=G?m:bE`Gpt<aun00S8,0*56"),
    NMEAMessage(b"!AIVDM,1,1,,B,15NPOOPP00o?bIjE`UEv4?wF2HIU,0*31"),
    NMEAMessage(b"!AIVDM,1,1,,A,35NVm2gP00o@5k:EbbPJnwwN25e3,0*35"),
    NMEAMessage(b"!AIVDM,1,1,,A,B52KlJP00=l4be5ItJ6r3wVUWP06,0*7C"),
    NMEAMessage(b"!AIVDM,2,1,1,B,53ku:202=kul=4TS@00<tq@V0<uE84LD00000017R@sEE6TE0GUDk1hP,0*57"),
    NMEAMessage(b"!AIVDM,2,1,2,B,55Mwm;P00001L@?;SKE8uT4j0lDh8uE8pD00000l0`A276S<07gUDp3Q,0*0D"),
    NMEAMessage.assemble_from_iterable(messages=[
        NMEAMessage(b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08"),
        NMEAMessage(b"!AIVDM,2,2,4,A,000000000000000,2*20")
    ])
]


def performance():
    def test():
        MESSAGES[random.randint(0, 8)].decode()

    iterations = 8000
    for i in range(5):
        elapsed_time = timeit.timeit(test, number=iterations)  # now < 0.3 seconds
        print(f"Decoding #{iterations} takes {elapsed_time} seconds in run #{i}")


def large_file_test():
    # The ais sample data is downloaded from https://www.aishub.net/ais-dispatcher
    start = time.time()
    ll = [msg.decode().content for msg in FileReaderStream("nmea-sample")]
    end = time.time()

    print(f"Decoding {len(ll)} messages took {end - start} seconds")
    print(ll[:100])


def live_demo():
    for msg in TCPStream('ais.exploratorium.edu'):
        print(msg.ais_id, msg.raw)


def error_test():
    counter = 0
    for msg in TCPStream('ais.exploratorium.edu'):
        counter += 1
        if counter % 100 == 0:
            print(f"Decoded #{counter} real world AIS messages without error")
        try:
            if not msg.is_valid:
                print("Found an invalid message: " + msg.raw)
            decoded = msg.decode()
            if not decoded:
                print("Could not decode message: ", msg.raw)
        except Exception as problem:
            print(f"Raised an exception ({str(problem)}) when trying to decode: {msg}")


for msg in TCPStream('ais.exploratorium.edu'):
    print(msg.decode().to_json())

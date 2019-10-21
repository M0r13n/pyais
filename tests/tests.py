from pyais.message import decode, NMEAMessage
from pyais.util import decode_into_bit_array
import timeit
import random
import functools

MESSAGES = [
    NMEAMessage(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C"),
    NMEAMessage(b"!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05"),
    NMEAMessage(b"!AIVDM,1,1,,A,15NJQiPOl=G?m:bE`Gpt<aun00S8,0*56"),
    NMEAMessage(b"!AIVDM,1,1,,B,15NPOOPP00o?bIjE`UEv4?wF2HIU,0*31"),
    NMEAMessage(b"!AIVDM,1,1,,A,35NVm2gP00o@5k:EbbPJnwwN25e3,0*35"),
    NMEAMessage(b"!AIVDM,1,1,,A,B52KlJP00=l4be5ItJ6r3wVUWP06,0*7C"),
    NMEAMessage(b"!AIVDM,2,1,1,B,53ku:202=kul=4TS@00<tq@V0<uE84LD00000017R@sEE6TE0GUDk1hP,0*57"),
    NMEAMessage(b"!AIVDM,2,1,2,B,55Mwm;P00001L@?;SKE8uT4j0lDh8uE8pD00000l0`A276S<07gUDp3Q,0*0D")
]


# Old or different methods for comparisons
def decode_into_bin_str(data) -> str:
    """
    Decode AIS message into a binary string
    :param data: AIS message encoded with AIS-ASCII-6
    :return: a binary string of 0's and 1's, e.g. 011100 011111 100001
    """
    binary_string = ''

    for c in data:
        if c < 0x30 or c > 0x77 or 0x57 < c < 0x6:
            raise ValueError("Invalid character")

        c -= 0x30 if (c < 0x60) else 0x38
        c &= 0x3F
        binary_string += f'{c:06b}'

    return binary_string


def decode_into_bytes(data):
    """
    Decode AIS message into a continuous block of bytes
    :param data: AIS message encoded with AIS-ASCII-6
    :return: An array of bytes

    Example:
    Let data be [63, 62, 61, 60]
    __111111 = 63
    __111110 = 62
    __111101 = 61
    __111100 = 60
    11111111 | 11101111 | 01111100
    """
    byte_arr = bytearray()

    for i, c in enumerate(data):
        if c < 0x30 or c > 0x77 or 0x57 < c < 0x6:
            raise ValueError("Invalid character")

        # Convert 8 bit binary to 6 bit binary
        c -= 0x30 if (c < 0x60) else 0x38
        c &= 0x3F

        # Only add the last 6 bits of each character
        if (i % 4) == 0:
            byte_arr.append(c << 2)

        elif (i % 4) == 1:
            byte_arr[-1] |= c >> 4
            byte_arr.append((c & 15) << 4)

        elif (i % 4) == 2:
            byte_arr[-1] |= c >> 2
            byte_arr.append((c & 3) << 6)

        elif (i % 4) == 3:
            byte_arr[-1] |= c

    return byte_arr


def compare_data_decoding():
    data = b"15M67FC000G?ufbE`FepT@3n00Sa"
    n = 25000

    # Decode socket data into :str:
    t = timeit.Timer(functools.partial(decode_into_bin_str, data))
    elapsed_time = t.timeit(n)
    print(f"Decoding #{n} messages into str takes  {elapsed_time} seconds")

    # Decode socket data into :bytes:
    t = timeit.Timer(functools.partial(decode_into_bytes, data))
    elapsed_time = t.timeit(n)
    print(f"Decoding #{n} messages into bytes takes  {elapsed_time} seconds")

    # Decode socket data into :bytes: and then convert them into a bitarray
    t = timeit.Timer(functools.partial(decode_into_bit_array, data))
    elapsed_time = t.timeit(n)
    print(f"Decoding #{n} messages into bitarray takes  {elapsed_time} seconds")

    # Result: They are all equally efficient, but differ in readability


def time():
    def test():
        decode(MESSAGES[random.randint(0, 7)])

    iterations = 8000
    elapsed_time = timeit.timeit(test, number=iterations)  # now 0.66934167 seconds
    print(f"Decoding #{iterations} takes {elapsed_time} seconds")


def is_correct():
    assert decode(MESSAGES[0]) == {'type': 1, 'repeat': 0, 'mmsi': 366053209,
                                   'status': (3, 'Restricted manoeuverability'), 'turn': 0, 'speed': 0, 'accuracy': 0,
                                   'lon': -122.34161833333333, 'lat': 37.80211833333333, 'course': 219.3, 'heading': 1,
                                   'second': 59, 'maneuver': (0, 'Not available'), 'raim': False, 'radio': 2281}

    assert decode(MESSAGES[1]) == {'type': 1, 'repeat': 0, 'mmsi': 367380120, 'status': (0, 'Under way using engine'),
                                   'turn': -128, 'speed': 1, 'accuracy': 0, 'lon': -122.40433333333333,
                                   'lat': 37.80694833333333, 'course': 245.20000000000002, 'heading': 511, 'second': 59,
                                   'maneuver': (0, 'Not available'), 'raim': True, 'radio': 34958}

    assert decode(MESSAGES[2]) == {'type': 1, 'repeat': 0, 'mmsi': 367436230, 'status': (0, 'Under way using engine'),
                                   'turn': 127, 'speed': 269, 'accuracy': 0, 'lon': -122.370845,
                                   'lat': 37.802618333333335, 'course': 312.20000000000005, 'heading': 318,
                                   'second': 59, 'maneuver': (0, 'Not available'), 'raim': False, 'radio': 2248}

    assert decode(MESSAGES[3]) == {'type': 1, 'repeat': 0, 'mmsi': 367533950, 'status': (0, 'Under way using engine'),
                                   'turn': -128, 'speed': 0, 'accuracy': 1, 'lon': -122.407585,
                                   'lat': 37.80835833333333, 'course': 360.0, 'heading': 511, 'second': 43,
                                   'maneuver': (0, 'Not available'), 'raim': True, 'radio': 99941}

    assert decode(MESSAGES[4]) == {'type': 3, 'repeat': 0, 'mmsi': 367637770, 'status': (15, 'Undefined'), 'turn': -128,
                                   'speed': 0, 'accuracy': 1, 'lon': -122.31407166666666, 'lat': 37.865175,
                                   'course': 277.90000000000003, 'heading': 511, 'second': 47,
                                   'maneuver': (0, 'Not available'), 'raim': True, 'radio': 23363}

    assert decode(MESSAGES[5]) == {'type': 18, 'repeat': 0, 'mmsi': 338097258, 'speed': 0, 'accuracy': False,
                                   'lon': -122.27014333333334, 'lat': 37.786295, 'course': 297.6, 'heading': 511,
                                   'second': 13, 'regional': 0, 'cs': True, 'display': False, 'dsc': True, 'band': True,
                                   'msg22': False, 'assigned': False, 'raim': True, 'radio': 917510}


def live_demo():
    from pyais.net import Stream

    for msg in Stream():
        print(decode(msg))


is_correct()
time()
live_demo()

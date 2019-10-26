from pyais.messages import NMEAMessage
from pyais.util import decode_into_bit_array
from pyais.constants import *
from pyais.ais_types import *
from bitarray import bitarray
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
    NMEAMessage(b"!AIVDM,2,1,2,B,55Mwm;P00001L@?;SKE8uT4j0lDh8uE8pD00000l0`A276S<07gUDp3Q,0*0D"),
    NMEAMessage.assemble_from_iterable(messages=[
        NMEAMessage(b"!AIVDM,2,1,4,A,55O0W7`00001L@gCWGA2uItLth@DqtL5@F22220j1h742t0Ht0000000,0*08"),
        NMEAMessage(b"!AIVDM,2,2,4,A,000000000000000,2*20")
    ])
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
        MESSAGES[random.randint(0, 8)].decode()

    iterations = 8000
    for i in range(5):
        elapsed_time = timeit.timeit(test, number=iterations)  # now < 0.3 seconds
        print(f"Decoding #{iterations} takes {elapsed_time} seconds in run #{i}")


def test_msg_type_5():
    msg = NMEAMessage(b"!AIVDM,2,1,3,A,55MuUD02;EFUL@CO;W@lU=<U=<U10V1HuT4LE:1DC@T>B4kC0DliSp=t,0*14").decode()

    assert msg['mmsi'] == 366962000
    assert msg['imo'] == 9131369
    assert msg['repeat'] == 0
    assert msg['to_bow'] == 154
    # assert msg['to_stern'] == 36

    assert msg['to_starboard'] == 18
    assert msg['to_port'] == 14
    assert msg['callsign'] == "WDD7294"
    assert msg['shipname'] == "MISSISSIPPI VOYAGER"
    assert msg['draught'] == 8.3
    assert msg['destination'] == "SFO 70"
    # assert msg['shiptype'] == "Tanker, Hazardous category D"
    assert not msg['dte']


def test_msg_type_8():
    msg = NMEAMessage(b"!AIVDM,1,1,,A,85Mwp`1Kf3aCnsNvBWLi=wQuNhA5t43N`5nCuI=p<IBfVqnMgPGs,0*47").decode()

    assert msg.nmea.is_valid
    assert msg['repeat'] == 0
    assert msg.msg_type == AISType.BINARY_BROADCAST
    assert msg['mmsi'] == 366999712
    assert msg['dac'] == 366
    assert msg['fid'] == 56
    assert msg['data'] == bitarray(
        "0011101001010011110110111011011110111110010010100111011100110001001101111111100001111101011110110000010001000"
        "1011111000001000000110111101010000001011101100100111111010110010011011110000011000110010100101011101001101110"
        "01110110011101101111100000010111111011")


def is_correct():
    test_msg_type_5()
    test_msg_type_8()
    assert MESSAGES[0].decode().content == {'type': 1, 'repeat': 0, 'mmsi': 366053209,
                                            'status': NavigationStatus.RestrictedManoeuverability, 'turn': 0,
                                            'speed': 0,
                                            'accuracy': 0,
                                            'lon': -122.34161833333333, 'lat': 37.80211833333333, 'course': 219.3,
                                            'heading': 1,
                                            'second': 59, 'maneuver': ManeuverIndicator.NotAvailable, 'raim': False,
                                            'radio': 2281}

    assert MESSAGES[1].decode().content == {'type': 1, 'repeat': 0, 'mmsi': 367380120,
                                            'status': NavigationStatus.UnderWayUsingEngine,
                                            'turn': -128, 'speed': 1, 'accuracy': 0, 'lon': -122.40433333333333,
                                            'lat': 37.80694833333333, 'course': 245.20000000000002, 'heading': 511,
                                            'second': 59,
                                            'maneuver': ManeuverIndicator.NotAvailable, 'raim': True, 'radio': 34958}

    assert MESSAGES[2].decode().content == {'type': 1, 'repeat': 0, 'mmsi': 367436230,
                                            'status': NavigationStatus.UnderWayUsingEngine,
                                            'turn': 127, 'speed': 269, 'accuracy': 0, 'lon': -122.370845,
                                            'lat': 37.802618333333335, 'course': 312.20000000000005, 'heading': 318,
                                            'second': 59, 'maneuver': ManeuverIndicator.NotAvailable, 'raim': False,
                                            'radio': 2248}

    assert MESSAGES[3].decode().content == {'type': 1, 'repeat': 0, 'mmsi': 367533950,
                                            'status': NavigationStatus.UnderWayUsingEngine,
                                            'turn': -128, 'speed': 0, 'accuracy': 1, 'lon': -122.407585,
                                            'lat': 37.80835833333333, 'course': 360.0, 'heading': 511, 'second': 43,
                                            'maneuver': ManeuverIndicator.NotAvailable, 'raim': True, 'radio': 99941}

    assert MESSAGES[4].decode().content == {'type': 3, 'repeat': 0, 'mmsi': 367637770,
                                            'status': NavigationStatus.Undefined,
                                            'turn': -128,
                                            'speed': 0, 'accuracy': 1, 'lon': -122.31407166666666, 'lat': 37.865175,
                                            'course': 277.90000000000003, 'heading': 511, 'second': 47,
                                            'maneuver': ManeuverIndicator.NotAvailable, 'raim': True, 'radio': 23363}

    assert MESSAGES[5].decode().content == {'type': 18, 'repeat': 0, 'mmsi': 338097258, 'speed': 0, 'accuracy': False,
                                            'lon': -122.27014333333334, 'lat': 37.786295, 'course': 297.6,
                                            'heading': 511,
                                            'second': 13, 'regional': 0, 'cs': True, 'display': False, 'dsc': True,
                                            'band': True,
                                            'msg22': False, 'assigned': False, 'raim': True, 'radio': 917510}

    assert MESSAGES[8].decode().content == {'type': 5, 'repeat': 0, 'mmsi': 368060190, 'ais_version': 2, 'imo': 0,
                                            'callsign': 'WDK4954', 'shipname': 'P/V_GOLDEN_GATE',
                                            'shiptype': ShipType.PilotVessel,
                                            'to_bow': 14, 'to_stern': 14, 'to_port': 4, 'to_starboard': 2,
                                            'epfd': EpfdType.Undefined, 'month': 0, 'day': 0, 'hour': 24, 'minute': 60,
                                            'draught': 0.0, 'destination': '', 'dte': False}


def live_demo():
    from pyais.net import Stream

    for msg in Stream():
        print(msg.decode().content)


is_correct()
time()
live_demo()

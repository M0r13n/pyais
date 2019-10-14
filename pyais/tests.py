from .message import decode

MESSAGES = [
    "!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C",
    "!AIVDM,1,1,,B,15NG6V0P01G?cFhE`R2IU?wn28R>,0*05",
    "!AIVDM,1,1,,A,15NJQiPOl=G?m:bE`Gpt<aun00S8,0*56",
    "!AIVDM,1,1,,B,15NPOOPP00o?bIjE`UEv4?wF2HIU,0*31",
    "!AIVDM,1,1,,A,35NVm2gP00o@5k:EbbPJnwwN25e3,0*35",
    "!AIVDM,1,1,,A,B52KlJP00=l4be5ItJ6r3wVUWP06,0*7C",
    "!AIVDM,2,1,1,B,53ku:202=kul=4TS@00<tq@V0<uE84LD00000017R@sEE6TE0GUDk1hP,0*57",
    "!AIVDM,2,1,2,B,55Mwm;P00001L@?;SKE8uT4j0lDh8uE8pD00000l0`A276S<07gUDp3Q,0*0D"
]


def time():
    import timeit
    import random

    def test():
        decode(MESSAGES[random.randint(0, 7)])

    iterations = 8000
    elapsed_time = timeit.timeit(test, number=iterations)
    print(f"Decoding #{iterations} takes {elapsed_time} seconds")

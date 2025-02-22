import pathlib
from pyais.queue import NMEAQueue


if __name__ == '__main__':

    filename = pathlib.Path(__file__).parent.joinpath('../tests/mixed.txt')

    q = NMEAQueue()

    with open(filename, 'rb') as fd:
        for line in fd.readlines():
            q.put_line(line)

            if x := q.get_or_none():
                print(x.decode())
            else:
                print(line)

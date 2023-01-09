"""This example shows how to connect to an TCP socket and print the latest N tracks as a table:

            mmsi       callsign       shipname            lat            lon
1      257027910           N.A.           N.A.      69.495375      17.489677
2      992576193           N.A.           N.A.      60.745617         5.2672
3      257786700           N.A.           N.A.      70.326922      17.254655
4      259176000           N.A.           N.A.      68.913317       15.07084
5      257847600           N.A.           N.A.        59.4113      10.489632
6      257237420           N.A.           N.A.      69.757393      18.615823
7      257125750           N.A.           N.A.      70.602113      23.623225
8      257012430           N.A.       BREITIND           N.A.           N.A.
9      257115020           N.A.           N.A.      68.233547      14.576078
10     258022100           N.A.           N.A.        68.4707       15.22097
"""
import sys
import pyais

host = '153.44.253.27'
port = 5631


def pretty_print(tracks):
    headers = ['mmsi', 'callsign', 'shipname', 'lat', 'lon']
    rows = [[getattr(t, a) or 'N.A.' for a in headers] for t in tracks]
    row_format = "{:>15}" * (len(headers) + 1)
    sys.stdout.write(row_format.format("", *headers) + '\n')

    for i, row in enumerate(rows, start=1):
        sys.stdout.write(row_format.format(i, *row) + '\n')


def live_print(tracks):
    for _ in range(len(tracks) + 1):
        sys.stdout.write("\x1b[1A\x1b[2K")  # move up cursor and delete whole line
    pretty_print(tracks)


print('\n' * 11)
with pyais.AISTracker() as tracker:
    for msg in pyais.TCPConnection(host, port=port):
        tracker.update(msg)
        latest_tracks = tracker.n_latest_tracks(10)
        live_print(latest_tracks)

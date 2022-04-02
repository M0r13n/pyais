"""
The following example shows how you could write the decoded data to CSV.
You first need to decode the data into a dictionary and then write the
dictionary to a CSV file using a `DictWriter`.
"""
import csv

from pyais import decode

ais_msg = "!AIVDO,1,1,,,B>qc:003wk?8mP=18D3Q3wgTiT;T,0*13"
data_dict = decode(ais_msg).asdict()

with open('decoded_message.csv', 'w') as f:
    w = csv.DictWriter(f, data_dict.keys())
    w.writeheader()
    w.writerow(data_dict)

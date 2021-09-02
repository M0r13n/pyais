
#---------------------------------------- 210419 Decoder 0.4------------------ ----------------------------------------

## The goal of this code is to read raw AIS file data and to write files for each mmsi
## Uses C:\Users\Hugo\Desktop\210105 Monitraffic - QGIS Directory\Diretoria 0.3

## imports
import numpy as np
from pyais.messages import NMEAMessage
import datetime
import os


now = datetime.datetime.now()
print("Current date and time at start: ")
print(str(now))
print('')

files = os.listdir(r"C:\Users\Hugo\Desktop\Hugo - Py Directory\Diretoria 0.3\Dados Base - partidos")
for xx in files:
    #set the raw data file
    file_raw = r'C:\Users\Hugo\Desktop\Hugo - Py Directory\Diretoria 0.3\Dados Base - partidos' + '\\' + xx

    # Where the decoded messages are writen
    file_data_b = r'C:\Users\Hugo\Desktop\Hugo - Py Directory\Diretoria 0.3\Dados descodificados\Dados AIS  - MMSI='

    ## File reading and deprocessing
    file_raw = open(file_raw, "r")

    now = datetime.datetime.now()
    print("Current date and time at start of ", xx, " :")
    print(str(now))
    print('')

    Static_Data = np.array([])
    ts = int(0) #this will be the time stamp
    while(True):
        #read next line
        line = file_raw.readline()
        #check if line is not null
        if not line:
            break
        #you can access the line
        if line[10] == ';':
            # the first numbers correspond to a time stamp
            ts = line[0:10]
            x = line[11:]
            message = NMEAMessage.from_string(x)

        else:
            message = NMEAMessage.from_string(line)

        G = message.decode()
        if not G.content:
            pass
        else:
            # Set static data file
            sttd_file = r'C:\Users\Hugo\Desktop\Hugo - Py Directory\Diretoria 0.3\\Dados descodificados\\'
            sttd_file = sttd_file + 'Static Data.txt'
            sttd = open(sttd_file, 'a')
            if G.content['type'] == 1 or G.content['type'] == 2 or G.content['type'] == 3:

                # Write in file
                file_data = file_data_b + str(G.content['mmsi'])+'.txt'
                file_data = open(file_data, "a")

                file_data.write(ts)
                file_data.write('\t')
                file_data.write(str(G.content['type']))
                file_data.write('\t')
                file_data.write(str(G.content['repeat']))
                file_data.write('\t')
                file_data.write(str(G.content['mmsi']))
                file_data.write('\t')
                file_data.write(str(G.content['status']))
                file_data.write('\t')
                file_data.write(str(G.content['turn']))
                file_data.write('\t')
                file_data.write(str(G.content['speed']))
                file_data.write('\t')
                file_data.write(str(G.content['accuracy']))
                file_data.write('\t')
                file_data.write(str('{:.5f}'.format(G.content['lon'])))
                file_data.write('\t')
                file_data.write(str('{:.5f}'.format(G.content['lat'])))
                file_data.write('\t')
                file_data.write(str('{:.2f}'.format(G.content['course'])))
                file_data.write('\t')
                file_data.write(str('{:.2f}'.format(G.content['heading'])))
                file_data.write('\t')
                file_data.write('\n')

                file_data.close()

            elif G.content['type'] == 5:
                if Static_Data.size == 0:
                    Static_Data = np.array([str(G.content['mmsi']), str(G.content['shiptype'])])
                else:
                    tt = '0'

                    for y in Static_Data:
                        if G.content['mmsi'] == y[0]:
                            tt = '1'

                    if tt == '0':
                        Static_Data = np.concatenate((Static_Data, [str(G.content['mmsi']), str(G.content['shiptype'])]), axis = 0)


    now = datetime.datetime.now()
for y in Static_Data:
    sttd.write(str(y))
    sttd.write('\t')
sttd.write('\n')
print("Current date and time: ")
print(str(now))
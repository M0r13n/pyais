
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

    # Set static data file
    sttd_file = r'C:\Users\Hugo\Desktop\Hugo - Py Directory\Diretoria 0.3\\Dados descodificados\\'
    sttd_file = sttd_file + 'Static Data.txt'
    qq = 0  # para a primeira linha

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
                Data_Point = np.array([str(G.content['mmsi']), str(G.content['shiptype'])])
                if qq == 0:
                    qq = 1
                    with open(sttd_file, 'a') as sttd:
                        sttd.write(Data_Point[0])
                        sttd.write('\t')
                        sttd.write(Data_Point[1])

                        sttd.write('\n')
                else:
                    tt = '0'
                    sttd = open(sttd_file, 'r')
                    while (True):
                        # read next line
                        line = sttd.readline()
                        # check if line is not null
                        if not line or tt == '1':
                            break
                        # you can access the line
                        # Reset variables
                        acc = 0
                        a = 0
                        b = 0
                        c = 0
                        A = []
                        z = 0
                        for y in range(len(line)):
                            if line[y] == '\t':
                                b = y
                                A.append(line[a:b])
                                a = b + 1
                                c = c + 1
                        b = y
                        A.append(line[a:b])
                        a = b + 1
                        c = c + 1


                        if Data_Point[0] == A[0]:
                            tt = '1'


                    sttd.close()

                    if tt == '0':
                        with open(sttd_file, 'a') as sttd:
                            sttd.write(Data_Point[0])
                            sttd.write('\t')
                            sttd.write(Data_Point[1])
                            sttd.write('\n')


    now = datetime.datetime.now()

print("Current date and time: ")
print(str(now))
# ----------------------------------- 210714 Cleaner 0.1 ------------------------------------------

## Os objetivos deste código são:
#1. Limpar os ficheiros de AIS que vieram do 210714 Decoder 0.6


## Imports
import os
import math
import numpy as np

directoria = r'C:\\Users\\Hugo\\Desktop\\Hugo - Py Directory\\Diretoria 0.3\\Dados descodificados'
file_list = os.listdir(directoria)

# Apagar navios vazios
for x in file_list:
    if ('Dados AIS  - MMSI=' in x) or ('Voyage ' in x):
        # Ver se o ficheiro está vazio ou é navio de pesca
        # Se for apagamos
        if os.path.getsize(directoria + '\\' + x) <= 500:
            os.remove(directoria + '\\' + x)

# Apagar navios não mercantes
file_list = os.listdir(directoria)
for x in file_list:
    print(x)
    if ('Dados AIS  - MMSI=' in x) or ('Voyage ' in x):
        # Ver se o ficheiro está vazio ou é navio de pesca
        # Se for apagamos
        if os.path.getsize(directoria + '\\' + x) == 0:
            os.remove(directoria + '\\' + x)
        else:
            #retirar mmsi
            if 'Dados AIS  - MMSI=' in x:
                mmsi = x[-13:-4]
            fid = open(directoria + '\\'+'Static Data.txt')
            nn = '0'
            while True and nn == '0':
                # read next line
                line = fid.readline()
                # check if line is not null
                if not line:
                    break
                # you can access the line
                a = 0
                b = 0
                c = 0
                A = []
                for y in range(len(line)):
                    if line[y] == '\t':
                        b = y
                        A.append(line[a:b])
                        a = b + 1
                        c = c + 1
                if A[1] == mmsi:
                    nn = '1'


                # Se o navio for de pesca
                if mmsi == A[1]:

                    if str(A[4].lower()) == 'shiptype.sailing' or 'shiptype.dredgingorunderwaterops'\
                            or 'shiptype.fishing'\
                            or 'shiptype.porttender' or 'shiptype.searchandrescuevessel' or 'shiptype.tug'\
                            or 'shiptype.pilotvessel' or 'shiptype.towing' or 'shiptype.pleasurecraft'\
                            or 'shiptype.towing_lengthover200' or 'shiptype.divingops' or 'shiptype.militaryops'\
                            or 'shiptype.law_enforcement' or 'shiptype.medicaltransport' or 'shiptype.sparelocalvessel'\
                            or 'shiptype.othertype' or 'shiptype.notavailable' or 'shiptype.trug':
                        nn = '1'

                        os.remove(directoria + '\\' + x)
                if nn == '1':
                    break


#A = np.array(["time stamp", "type", "repeat", "mmsi", "status", "turn",
#              "speed", "accuracy", "lon", "lat", "course", "heading"])
#A = np.array(["", "", "", "", "", "",
#             "", "", "", "", "", ""])
A = []

file_list = os.listdir(directoria)
for x in file_list:
    print(x)
    if ('Dados AIS  - MMSI=' in x) or ('Voyage ' in x):
        print(x)
        # Limpeza geral
        fin = directoria + '\\' + x
        os.rename(fin, fin[:-4] + '_0.txt')
        fin = fin[:-4] + '_0.txt'
        fini =open(fin,  "r")

        B = []

        while (True):
            # read next line
            line = fini.readline()
            # check if line is not null
            if not line:
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


            if A[c-1] != []:
                # check if lon is out of bounds
                # check if lat is out of bounds
                # check if speed is out of bounds
                # check if course is out of bounds
                if float(A[8]) < -6.4\
                    and float(A[8]) > -11.24\
                    and float(A[9]) < 43.86 \
                    and float(A[9]) > 34.08\
                    and float(A[6]) <= 102.3\
                    and float(A[6]) >= 0\
                    and float(A[10]) <= 360\
                    and float(A[10]) >= 0:
                    acc = 1 # then it is accepted

#                if B != []:
#                    distance = np.sqrt( ( float(A[8]) - float(B[8]) )**2 + (float(A[9]) - float(B[9]))**2 )
#                    time = float(A[0]) - float(B[0])
#                    if float(B[6]) < 3 and distance < 3 * float(B[6]) * time +0.01:
#                        pass
#                    elif float(B[6]) >= 3 and distance < 2 * float(B[6]) * time :
#                        pass
#                    else:
#                        acc = 0
            print('-----')
            print(A)
            print(float(A[6]))
            print(float(A[8]))
            print(float(A[9]))
            print(float(A[10]))
            print(acc)
            if acc == 1:
                fout = directoria + '\\' + x
                fout = open(fout, "a")
                B = A
                for y in A:
                    fout.write(y)
                    fout.write('\t')
                fout.write('\n')
                fout.close()


        fini.close()
        os.remove(fin)


# Apagar navios vazios
file_list = os.listdir(directoria)
for x in file_list:
    print(x)
    if ('Dados AIS  - MMSI=' in x) or ('Voyage ' in x):
        # Ver se o ficheiro está vazio ou é navio de pesca
        # Se for apagamos
        if os.path.getsize(directoria + '\\' + x) <= 150:
            os.remove(directoria + '\\' + x)































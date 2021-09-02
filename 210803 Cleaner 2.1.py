# ----------------------------------- 210803 Cleaner 2.1 ------------------------------------------

## Os objetivos deste código são:
#Limpar os ficheiros de AIS que vieram do 210803 Decoder 0.8
# Apagar navios não mercantes

## Imports
import os
import math
import numpy as np

directoria = r'C:\\Users\\Hugo\\Desktop\\Hugo - Py Directory\\Diretoria 0.3\\Dados descodificados'
file_list = os.listdir(directoria)

# Apagar navios não mercantes
file_list = os.listdir(directoria)
for x in file_list:
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
                b = y
                A.append(line[a:b])
                a = b + 1
                c = c + 1

                if A[0] == mmsi:
                    nn = '1'
                    # Se o navio for de pesca

                    if str(A[1].lower()) == 'shiptype.sailing'\
                            or str(A[1].lower()) =='shiptype.dredgingorunderwaterops'\
                            or str(A[1].lower()) =='shiptype.fishing'\
                            or str(A[1].lower()) =='shiptype.porttender'\
                            or str(A[1].lower()) == 'shiptype.searchandrescuevessel'\
                            or str(A[1].lower()) =='shiptype.tug'\
                            or str(A[1].lower()) =='shiptype.pilotvessel'\
                            or str(A[1].lower()) == 'shiptype.towing'\
                            or str(A[1].lower()) == 'shiptype.pleasurecraft'\
                            or str(A[1].lower()) =='shiptype.towing_lengthover200'\
                            or str(A[1].lower()) == 'shiptype.divingops'\
                            or str(A[1].lower()) == 'shiptype.militaryops'\
                            or str(A[1].lower()) =='shiptype.law_enforcement'\
                            or str(A[1].lower()) == 'shiptype.medicaltransport' \
                            or str(A[1].lower()) == 'shiptype.sparelocalvessel'\
                            or str(A[1].lower()) =='shiptype.othertype'\
                            or str(A[1].lower()) == 'shiptype.trug'\
                            or str(A[1].lower()) =='shiptype.notavailable':
                        nn = '2'
                if nn == '1' or nn == '2':
                    break
            # nn == 0 -> vessel is not in Static_Data.txt
            # nn == 1 -> vessel is Static_Data
            # nn == 2 -> vessel is in Static_Data.txt as a non cargo type vessel
            if nn == '0' or nn == '2':
                os.remove(directoria + '\\' + x)





























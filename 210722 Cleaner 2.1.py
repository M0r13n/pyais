# ----------------------------------- 210719 2.0 ------------------------------------------

## Os objetivos deste código são:
#Limpar os ficheiros de AIS que vieram do 210714 Decoder 0.6
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
                    if str(A[4].lower()) == 'shiptype.sailing' or 'shiptype.dredgingorunderwaterops'\
                            or 'shiptype.fishing'\
                            or 'shiptype.porttender' or 'shiptype.searchandrescuevessel' or 'shiptype.tug'\
                            or 'shiptype.pilotvessel' or 'shiptype.towing' or 'shiptype.pleasurecraft'\
                            or 'shiptype.towing_lengthover200' or 'shiptype.divingops' or 'shiptype.militaryops'\
                            or 'shiptype.law_enforcement' or 'shiptype.medicaltransport' or 'shiptype.sparelocalvessel'\
                            or 'shiptype.trug': #or 'shiptype.othertype' #or 'shiptype.notavailable':
                        os.remove(directoria + '\\' + x)
                if nn == '1':
                    break



























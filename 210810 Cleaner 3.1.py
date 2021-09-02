# ----------------------------------- 210719 3.0 ------------------------------------------

## Os objetivos deste código são:
#Limpar os ficheiros de AIS que vieram do 210714 Decoder 0.6
# Apagar os sin ais AIS que estão fora da zona geográfica ou com velocidades ou angulos impossiveis

## Imports
import os
import math
import numpy as np

directoria = r'C:\\Users\\Hugo\\Desktop\\Hugo - Py Directory\\Diretoria 0.3\\Dados descodificados'
file_list = os.listdir(directoria)

for x in file_list:
    print(x)
    if 'Dados AIS  - MMSI=' in x:
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
                    and float(A[9]) < 42 \
                    and float(A[9]) > 35\
                    and float(A[6]) <= 102.3\
                    and float(A[6]) >= 0\
                    and float(A[10]) <= 360\
                    and float(A[10]) >= 0:
                    acc = 1 # then it is accepted
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

























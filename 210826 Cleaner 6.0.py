# ----------------------------------- 210826 Cleaner 6.0 ------------------------------------------

## Os objetivos deste código são:
#Limpar os ficheiros de AIS que vieram do 210714 Decoder 0.6
# apagar 4 em cada 5 viagens

## Imports
import os
import math
import numpy as np

directoria = r'C:\\Users\\Hugo\\Desktop\\Hugo - Py Directory\\Diretoria 0.3\\Dados descodificados'
file_list = os.listdir(directoria)
cont = 0

for x in file_list:
    if ('Voyage ' in x):
        cont = cont + 1

        if cont != 3:
            os.remove(directoria + '\\' + x)
        else:
            cont = 0
























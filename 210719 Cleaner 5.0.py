# ----------------------------------- 210719 Cleaner 5.0 ------------------------------------------

## Os objetivos deste código são:
#Limpar os ficheiros de AIS que vieram do 210714 Decoder 0.6
# apagar ficheiros demasiado pequenos

## Imports
import os
import math
import numpy as np

directoria = r'C:\\Users\\Hugo\\Desktop\\Hugo - Py Directory\\Diretoria 0.3\\Dados descodificados'
file_list = os.listdir(directoria)


for x in file_list:
    if ('Dados AIS  - MMSI=' in x) or ('Voyage ' in x):
        if os.path.getsize(directoria + '\\' + x) <= 1024: # smaller than 1 kB
            os.remove(directoria + '\\' + x)

























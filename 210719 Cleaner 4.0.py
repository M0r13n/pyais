# ----------------------------------- 210719 4.0 ------------------------------------------

## Os objetivos deste código são:
#1. Limpar os ficheiros de AIS que vieram do 210714 Decoder 0.6
# Apagar pontos desalinhados de viagens

## Imports
import os
import math
import numpy as np

directoria = r'C:\\Users\\Hugo\\Desktop\\Hugo - Py Directory\\Diretoria 0.3\\Dados descodificados'
file_list = os.listdir(directoria)


for x in file_list:
    print(x)
    if 'Voyage ' in x and os.path.getsize(directoria + '\\' + x) > 2048: # bigger than 2 kB
        # Ver se os pontos da rota estão desalinhados
        lista = [0]
        # três pontos são considerados o B, o C, e o D, por ordem cronológica
        B = []
        C = []
        D = []
        fid = open(directoria + '\\' + x,'r')
        nn = '0'
        while (True and nn == '0'):
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
            if B == []: #estamos a olhar para o 1º ponto (1ª linha do ficheiro)
                B = A
            elif C == []:#estamos a olhar para o 1º ponto (2ª linha do ficheiro)
                C = A

            else:#estamos a olhar para o nº ponto (nª linha do ficheiro)
                D = A
                # Nós avaliamos o C
                # se ele estiver desalinhado com o BD então é rejeitado
                dist_BD = math.sqrt((B[8] - D[9]) ** 2 + (B[9] - D[9]) ** 2)
                dist_BC = math.sqrt((B[8] - C[9]) ** 2 + (B[9] - C[9]) ** 2)
                dist_CD = math.sqrt((C[8] - D[9]) ** 2 + (C[9] - D[9]) ** 2)
                # ver se está alihado com o D e com o C
                if dist_BC > dist_BD or dist_CD > dist_BD:
                    lista = lista + [0]
                    C = D
                else:
                    lista = lista + [1]
                    B = C
                    C = D
        fid.close()

        fid = open(directoria + '\\' + x, 'r')
        fid2 = open(directoria + '\\'+ '__' + x, 'a')
        nn = 0
        while (True):
            # read next line
            line = fid.readline()
            # check if line is not null
            if not line:
                break

            if lista[nn] == 1:
                fid2.write(line)
        fid.close()
        fid2.close()
        os.rename(directoria + '\\'+ '__' + x, directoria + '\\' + x)
        os.remove(directoria + '\\'+ '__' + x)

























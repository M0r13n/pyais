# ----------------------------------- 210719 Voyager 0.0 ------------------------------------------

## Os objetivos deste código são:
# 1. separar mmsi em viagens

# Imports
import os

import datetime as datetime
import numpy as np
from matplotlib import pyplot as plt
import math

diretoria = r'C:\\Users\\Hugo\\Desktop\\Hugo - Py Directory\\Diretoria 0.3\\Dados descodificados'

# Menu
q = '1'


ident = 0
for file_name in os.listdir(diretoria):
    if ('Dados AIS  - MMSI=') in file_name:
        z = file_name
        print(z)
        Dados = []
        # Abrir o ficheiro com esse mmsi
        file = diretoria + '\\' + z
        B = []
        # ver se o ficheiro existe
        if os.path.isfile(file):
            fid = open(file, "r")
            num_rota = 0
            tempo_parado = 0
            tempo_entre_pontos = 0
            fim_de_rota = '0'
            file_route = diretoria + '\\' + 'Viagem No. ' + str(num_rota) + '.txt'
            file_route = open(file_route, 'a')
            vel_max = 0
            viagem_vazia = '1'
            while (True):
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
                # A = np.array(["time stamp", "type", "repeat", "mmsi", "status", "turn",
                #              "speed", "accuracy", "lon", "lat", "course", "heading"])
                # Nome do ficheiro onde ele escreve esta rota
                acc = 1
                if fim_de_rota == '1' and viagem_vazia == '0':
                    file_route.close()
                    num_rota = num_rota + 1
                    file_route = diretoria + '\\' + 'Viagem No. ' + str(num_rota) + '.txt'
                    file_route = open(file_route, 'a')
                    tempo_parado = 0
                    tempo_entre_pontos = 0
                    vel_max = 0
                    fim_de_rota = '0'
                    viagem_vazia = '1'
                elif fim_de_rota == '1' and viagem_vazia == '1':
                    tempo_parado = 0
                    tempo_entre_pontos = 0
                    vel_max = 0
                    fim_de_rota = '0'
                    acc = 0
                # B será o ponto anterior
                # vamos ver se este valor não é identico ao anterior
                #                if B != [] and abs(float(A[0]) - float(B[0])) <= 60 and A[4] == B[4] and\
                #                    abs(float(A[5]) - float(B[5])) < 2 and\
                #                    abs(float(A[6]) - float(B[6])) < 2 and\
                #                    abs(float(A[10]) - float(B[10])) < 2 and\
                #                    abs(float(A[11]) - float(B[11])) < 2:
                #                    acc = 0 # Not accepted it is too similar to the previous one
                # O ponto A será adicionado à rota atual a menos que:
                # Ou seja o ponto a partir do qual o navio está parado à 1 hora
                # Ou seja um ponto a mais de 1 hora do anterior
                if B == []:
                    pass
                else:
                    tempo_entre_pontos = abs(float(A[0]) - float(B[0]))
                    if float(A[6]) > vel_max:
                        vel_max = float(A[6])
                    # se a velocidade for nula (i.e menor que 1 nó) durante 1 hora, considera-se que o navio está atracado e que a rota terminou
                    if float(A[6]) <= 1 and float(B[6]) <= 1:
                        tempo_parado = tempo_parado + abs(float(A[0]) - float(B[0]))
                    else:  # reset do tempo parado
                        tempo_parado = 0
                    if vel_max <= 5:  # a velocidade máxima impede que os 1os n pontos de cada viagens sejam pontos em que o navio esteja parado
                        acc = 0
                    # se o tempo entre dois pontos for mais que 1 hora considera-se que são rotas diferentes
                    if tempo_parado >= 3600 or tempo_entre_pontos >= 3600:
                        fim_de_rota = '1'
                        acc = 0
                if acc == 1 and B != []:  # if it is accepted
                    # correção do timestamp para o formato que a Lee quer
                    #                    data = []
                    #                    data = str(datetime.datetime.fromtimestamp(int(A[0])).isoformat())
                    #                    file_route.write(data)
                    #                    file_route.write('\t')
                    #                    A = A[1:]
                    for y in B:
                        file_route.write(y)
                        file_route.write('\t')
                    file_route.write('\n')
                    viagem_vazia = '0'
                B = []
                B = A  # B será o valor anterior
            file_route.close()
            # Agora que ele fez as rotas vamos fazer umas modificações ao timestamp e ao titulo
            # procurar na diretoria
            for file_name in os.listdir(diretoria):
                # se o nome for viagem
                if ("Viagem" in file_name) and (os.path.getsize(diretoria + '\\' + file_name)!=0):
                    # cria ficheiro wooble
                    file_dummy_name = diretoria + '\\' + 'dummy' + '.txt'
                    file_dummy = open(file_dummy_name, 'a')
                    # lê linha a linha o ficheira
                    fid2 = open(diretoria + '\\' + file_name, "r")
                    time_stamp_menor = []
                    lat_menor = []
                    lon_menor = []
                    time_stamp_maior = []
                    lat_maior = []
                    lon_maior = []
                    mmsi = []
                    while (True):
                        # read next line
                        line_6 = fid2.readline()
                        # check if line is not null
                        if not line_6:
                            break
                        # you can access the line
                        a = 0
                        b = 0
                        c = 0
                        A = []
                        for y in range(len(line_6)):
                            if line_6[y] == '\t':
                                b = y
                                A.append(line_6[a:b])
                                a = b + 1
                                c = c + 1
                        b = y
                        A.append(line_6[a:b])
                        a = b + 1
                        c = c + 1
                        if len(A) == 15:
                            # Se o timestamp for menor guarda timestamp e posição
                            if time_stamp_menor == []:
                                time_stamp_menor = int(A[0])
                                lat_menor = float(A[9])
                                lon_menor = float(A[8])
                            elif float(time_stamp_menor) >= int(A[0]):
                                time_stamp_menor = int(A[0])
                                lat_menor = float(A[9])
                                lon_menor = float(A[8])
                            # Se o timestamp for maior guarda timestamp e posição
                            if time_stamp_maior == []:
                                time_stamp_maior = float(A[0])
                                lat_maior = float(A[9])
                                lon_maior = float(A[8])
                            elif float(time_stamp_maior) <= float(A[0]):
                                time_stamp_maior = float(A[0])
                                lat_maior = float(A[9])
                                lon_maior = float(A[8])
                            mmsi = str(A[3])
                            # escreve no Wooble a linha (convertendo o timestamp para o que a Lee quer
                            for y in A:
                                file_dummy.write(y)
                                file_dummy.write('\t')
                            file_dummy.write('\n')
                    file_dummy.close()
                    print('-----')
                    print(mmsi)
                    print(time_stamp_menor)
                    print(time_stamp_maior)
                    print(lon_menor)
                    print(lon_maior)
                    print(lat_menor)
                    print(lat_maior)
                    novo_nome = "{0:03}".format(ident) + ' ' + 'Voyage' + ' ' \
                                + str(mmsi) + ' ' \
                                + str(datetime.datetime.fromtimestamp(time_stamp_menor).isoformat()) + ' ' \
                                + str(datetime.datetime.fromtimestamp(time_stamp_maior).isoformat()) + ' ' \
                                + str(round(lon_menor, 2)) + ' ' \
                                + str(round(lon_maior, 2)) + ' ' \
                                + str(round(lat_menor, 2)) + ' ' \
                                + str(round(lat_maior, 2)) + '.txt'
                    ident = ident + 1
                    # O windows não aceita ':' ptt vamos substitui-os por -
                    novo_nome = novo_nome.replace(':', '-')
                    fid2.close()
                    novo_nome = diretoria + '\\' + novo_nome
                    os.rename(file_dummy_name, novo_nome)
            fid.close()
            for file_name in os.listdir(diretoria):
                # se o nome for viagem
                if "Viagem" in file_name:
                    file_name = diretoria + '\\' + file_name
                    os.remove(file_name)


# ----------------------------------- 210407 Monitraffic 0.7 ------------------------------------------

## Os objetivos deste código são:
# 1. Menu que permite ver os dados de um navio

# Imports
import os

import datetime as datetime
import numpy as np
from matplotlib import pyplot as plt
import math

diretoria = r'C:\\Users\\Hugo\\Desktop\\Hugo - Py Directory\\Diretoria 0.3\\Dados descodificados'

# Menu
q = '1'

while q != '0':
    print('Escolha uma Opção:')
    print('0 - Sair')
    print('1 - ver os dados de um navio')
    print('2 - Ver as velocidades de um mmsi')
    print('3 - extrair rotas de um mmsi')
    print('4 - extrair rotas de todos os mmsi')
    print('5 - ver dados de cluster')
    q = input()
    print(' ')

    if q == '1':  # Ver dados de um mmsi
        print('Insira o mmsi desejado')
        z = input()

        Dados = []
        # Abrir o ficheiro com esse mmsi

        file = diretoria + '\\' + z + '.txt'
        X = []
        Y = []
        YO = []

        # ver se o ficheiro existe
        if os.path.isfile(file):
            fid = open(file, "r")
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

                # A = np.array(["time stamp", "type", "repeat", "mmsi", "status", "turn",
                #              "speed", "accuracy", "lon", "lat", "course", "heading"])

                # Aplicar a formula da latitude crescida
                u = 1 / 297
                ex = np.sqrt(2 * u - u ** 2)
                lb = np.log(np.tan(math.radians((math.pi / 4) + (float(A[9]) / 2))))
                Y = Y + [lb]
                X = X + [float(A[8])]
                YO = YO + [float(A[9])]

            plt.plot(X, Y, 'ro')
            # Costa Portuguesa
            # Long
            PTX = [-8.875057, -8.644095, -9.082375, -9.362691, -9.488282, -9.256041, -9.207801, -8.902339,
                   -8.772101,
                   -8.880846,
                   -8.799692, -8.787735, -8.973873, -8.612259, -8.167375, -7.890768, -7.411114]
            # Lat
            PTY = [41.869127, 41.020368, 39.582658, 39.350094, 38.711115, 38.661503, 38.40021, 38.491050, 38.238827,
                   37.954860,
                   37.904757, 37.52054, 37.012282, 37.118971, 37.083724, 36.962354, 37.177740]
            # Lat Acr
            PTYA = []
            for x in PTY:
                u = 1 / 297
                ex = np.sqrt(2 * u - u ** 2)
                lb = np.log(np.tan(math.radians((math.pi / 4) + (float(x) / 2))))
                PTYA = PTYA + [lb]
            plt.plot(PTX, PTYA, 'g-')
            #        plt.show()
            plt.xlim([-13, -7.5])
            plt.ylim([-1.08, -0.92])
            plt.show()
        fid.close()

    elif q == '2':  # Ver velocidades de um mmsi
        print('Insira o mmsi desejado')
        z = input()
        Dados = []
        # Abrir o ficheiro com esse mmsi
        file = diretoria + '\\'  + z + '.txt'
        T = []  # vetor tempo
        V = []  # vetor velocidade
        # ver se o ficheiro existe
        if os.path.isfile(file):
            fid = open(file, "r")
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
                # A = np.array(["time stamp", "type", "repeat", "mmsi", "status", "turn",
                #              "speed", "accuracy", "lon", "lat", "course", "heading"])
                T = T + [int(A[0])]
                V = V + [float(A[6])]
            plt.plot(T, V, 'ro')

            plt.show()
        fid.close()

    elif q == '3':
        print('Insira o mmsi desejado')
        z = input()

        Dados = []
        # Abrir o ficheiro com esse mmsi
        file = diretoria + '\\'  + z + '.txt'
        B = []

        # ver se o ficheiro existe
        if os.path.isfile(file):
            fid = open(file, "r")
            num_rota = 0
            tempo_parado = 0
            tempo_entre_pontos = 0
            fim_de_rota = '0'
            file_route = diretoria + '\\'  + 'Viagem No. ' + str(num_rota) + '.txt'
            file_route = open(file_route, 'a')
            vel_max = 0
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

                # A = np.array(["time stamp", "type", "repeat", "mmsi", "status", "turn",
                #              "speed", "accuracy", "lon", "lat", "course", "heading"])

                # Nome do ficheiro onde ele escreve esta rota
                if fim_de_rota == '1' and os.stat(file_route.name).st_size != 0:
                    file_route.close()
                    num_rota = num_rota + 1
                    file_route = diretoria + '\\' + 'Viagem No. ' + str(num_rota) + '.txt'
                    file_route = open(file_route, 'a')
                    tempo_parado = 0
                    tempo_entre_pontos = 0
                    vel_max = 0

                acc = 1

                # B será o ponto anterior
                # vamos ver se este valor não é identico ao anterior

                #                if B != [] and abs(float(A[0]) - float(B[0])) <= 60 and A[4] == B[4] and\
                #                    abs(float(A[5]) - float(B[5])) < 2 and\
                #                    abs(float(A[6]) - float(B[6])) < 2 and\
                #                    abs(float(A[10]) - float(B[10])) < 2 and\
                #                    abs(float(A[11]) - float(B[11])) < 2:
                #                    acc = 0 # Not accepted it is too similar to the previous one

                if B != []:
                    tempo_entre_pontos = abs(float(A[0]) - float(B[0]))

                if float(A[6]) > vel_max:
                    vel_max = float(A[6])

                # se a velocidade for nula durante 1 minuto, considera-se que o navio está atracado e que a rota terminou
                if float(A[6]) <= 0.25 and B != [] and float(B[6]) <= 0.25:
                    tempo_parado = tempo_parado + abs(float(A[0]) - float(B[0]))
                    acc = 0
                else:  # reset do tempo parado
                    tempo_parado = 0

                if vel_max <= 5:
                    acc = 0

                # se o tempo entre dois pontos for mais que 1 hora considera-se que são rotas diferentes
                if tempo_parado >= 60 or tempo_entre_pontos >= 3600:
                    fim_de_rota = '1'
                else:
                    fim_de_rota = '0'

                B = []
                B = A  # B será o valor anterior

                if acc == 1:  # if it is accepted
                    # correção do timestamp para o formato que a Lee quer
                    #                    data = []
                    #                    data = str(datetime.datetime.fromtimestamp(int(A[0])).isoformat())
                    #                    file_route.write(data)
                    #                    file_route.write('\t')

                    #                    A = A[1:]

                    for y in A:
                        file_route.write(y)
                        file_route.write('\t')
                    file_route.write('\n')
            file_route.close()

            # Agora que ele fez as rotas vamos fazer umas modificações ao timestamp e ao titulo

            # procurar na diretoria
            for file_name in os.listdir(
                    diretoria):
                # se o nome for viagem
                if "Viagem" in file_name:
                    # cria ficheiro wooble
                    file_dummy_name = diretoria + '\\'  + 'dummy' + '.txt'
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
                        line = fid2.readline()
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
                        if len(A) == 12:
                            # Se o timestamp for menor guarda timestamp e posição
                            if time_stamp_menor == []:
                                time_stamp_menor = int(A[0])
                                lat_menor = float(A[9])
                                lon_menor = float(A[8])
                            elif float(time_stamp_menor) > int(A[0]):
                                time_stamp_menor = int(A[0])
                                lat_menor = float(A[9])
                                lon_menor = float(A[8])

                            # Se o timestamp for maior guarda timestamp e posição
                            if time_stamp_maior == []:
                                time_stamp_maior = float(A[0])
                                lat_maior = float(A[9])
                                lon_maior = float(A[8])
                            elif float(time_stamp_maior) < float(A[0]):
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



                    # Após ler renomeisa o Wooble
                    print(time_stamp_menor)
                    print(datetime.datetime.fromtimestamp(time_stamp_menor).isoformat())

                    novo_nome = 'Voyage' + ' ' \
                                + str(mmsi) + ' ' \
                                + str(datetime.datetime.fromtimestamp(time_stamp_menor).isoformat()) + ' ' \
                                + str(datetime.datetime.fromtimestamp(time_stamp_maior).isoformat()) + ' ' \
                                + str(round(lon_menor, 4)) + ' ' \
                                + str(round(lon_maior, 4)) + ' ' \
                                + str(round(lat_menor, 4)) + ' ' \
                                + str(round(lat_maior, 4)) + '.txt'

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
        #                    os.rename(file_dummy_name,
        #                              'C:\\Users\\Hugo\\Desktop\\210105 Monitraffic - QGIS Directory\\Diretoria 0.2\\Dados descodificados\\'
        #                              + 'Route' + ' '
        #                              + mmsi + ' '
        #                              + str(datetime.datetime.fromtimestamp(time_stamp_menor).isoformat()) + ' '
        #                              + str(datetime.datetime.fromtimestamp(time_stamp_maior).isoformat()) + ' '
        #                              + str(round(lon_menor, 2)) + ' '
        #                              + str(round(lat_maior, 2)) + ' '
        #                              + str(round(lat_menor, 2)) + ' '
        #                              + str(round(lat_maior, 2)) + '.txt')
        # e apaga o viagem [[[]]]
    elif q == '4':
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
                        # A = np.array(["time stamp", "type", "repeat", "mmsi", "status", "turn",
                        #              "speed", "accuracy", "lon", "lat", "course", "heading"])
                        # Nome do ficheiro onde ele escreve esta rota
                        if fim_de_rota == '1' and os.stat(file_route.name).st_size != 0:
                            file_route.close()
                            num_rota = num_rota + 1
                            file_route = diretoria + '\\'  + 'Viagem No. ' + str(num_rota) + '.txt'
                            file_route = open(file_route, 'a')
                            tempo_parado = 0
                            tempo_entre_pontos = 0
                            vel_max = 0
                        acc = 1
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
                                acc = 0
                            else:  # reset do tempo parado
                                tempo_parado = 0
                            if vel_max <= 5:
                                acc = 0
                            # se o tempo entre dois pontos for mais que 1 hora considera-se que são rotas diferentes
                            if tempo_parado >= 3600 or tempo_entre_pontos >= 3600:
                                fim_de_rota = '1'
                            else:
                                fim_de_rota = '0'
                        B = []
                        B = A  # B será o valor anterior
                        if acc == 1:  # if it is accepted
                            # correção do timestamp para o formato que a Lee quer
                            #                    data = []
                            #                    data = str(datetime.datetime.fromtimestamp(int(A[0])).isoformat())
                            #                    file_route.write(data)
                            #                    file_route.write('\t')
                            #                    A = A[1:]
                            for y in A:
                                file_route.write(y)
                                file_route.write('\t')
                            file_route.write('\n')
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
                                if len(A) == 12:
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
                            novo_nome = 'Voyage' + ' ' \
                                        + str(mmsi) + ' ' \
                                        + str(datetime.datetime.fromtimestamp(time_stamp_menor).isoformat()) + ' ' \
                                        + str(datetime.datetime.fromtimestamp(time_stamp_maior).isoformat()) + ' ' \
                                        + str(round(lon_menor, 2)) + ' ' \
                                        + str(round(lon_maior, 2)) + ' ' \
                                        + str(round(lat_menor, 2)) + ' ' \
                                        + str(round(lat_maior, 2)) + '.txt'
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
    elif q == '5':
        print('Insira o cluster desejado')
        zz = input()
        for file_name in os.listdir(diretoria):
            if ('Cluster ' + str(zz)) in file_name:
                z = file_name
                print(z)
                Dados = []
                # Abrir o ficheiro com esse mmsi
                file = diretoria + '\\'  + z
                B = []
                # ver se o ficheiro existe
                if os.path.isfile(file):
                    fid = open(file, "r")
                    X = []
                    Y = []
                    YO = []
                    ee = '1' #its first line
                    while (True):
                        # read next line
                        line = fid.readline()
                        # check if line is not null
                        if not line:
                            break
                        # you can access the line
                        if ee == '1':
                            ee = '0'
                        else:
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
                                    # 283,1216552625,1,0,205480000,NavigationStatus.UnderWayUsingEngine,-11,8.3,True,-7.44217,37.3135,183.0,181.0
                            # A = np.array(["time stamp", "type", "repeat", "mmsi", "status", "turn",
                            #              "speed", "accuracy", "lon", "lat", "course", "heading"])
                            # Nome do ficheiro onde ele escreve esta rota
                            u = 1 / 297
                            ex = np.sqrt(2 * u - u ** 2)
                            lb = np.log(np.tan(math.radians((math.pi / 4) + (float(A[9]) / 2))))
                            Y = Y + [lb]
                            X = X + [float(A[8])]
                            YO = YO + [float(A[9])]

                    fid.close()
                plt.plot(X, Y, 'r-')

        # Costa Portuguesa
        # Long
        PTX = [-8.875057, -8.644095, -9.082375, -9.362691, -9.488282, -9.256041, -9.207801, -8.902339,
               -8.772101,
               -8.880846,
               -8.799692, -8.787735, -8.973873, -8.612259, -8.167375, -7.890768, -7.411114]
        # Lat
        PTY = [41.869127, 41.020368, 39.582658, 39.350094, 38.711115, 38.661503, 38.40021, 38.491050, 38.238827,
               37.954860,
               37.904757, 37.52054, 37.012282, 37.118971, 37.083724, 36.962354, 37.177740]
        # Lat Acr
        PTYA = []
        for x in PTY:
            u = 1 / 297
            ex = np.sqrt(2 * u - u ** 2)
            lb = np.log(np.tan(math.radians((math.pi / 4) + (float(x) / 2))))
            PTYA = PTYA + [lb]
        plt.plot(PTX, PTYA, 'g-')
        #        plt.show()
        plt.xlim([-13, -7.5])
        plt.ylim([-1.08, -0.92])
        plt.show()
    else:
        print('Option failed')

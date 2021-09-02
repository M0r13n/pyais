# ----------------------------------- 210714 Clusterer 0.4 ------------------------------------------

#    Os objetivos deste código são:
# Pegar nos ficheiros de viagem produzidos pelo Monnitraffic 0.8 e agrupálos por par origem-destino

# Imports
import os
import datetime as datetime
import numpy as np
from matplotlib import pyplot as plt
import shutil


diretoria = 'C:\\Users\\Hugo\\Desktop\\Hugo - Py Directory\\Diretoria 0.3\\Dados descodificados\\'

# ----------------------------------- Origin Clustering ------------------------------------------

# Controladores do Clustering
N_min = int(2)
Epsilon = float(0.1)


# Retira as viagens na diretoria
# para todas as viagens

fv_original = diretoria + 'List of Voyages.txt'
fv_original2 = diretoria + 'List of Voyages2.txt'
fv_outlier_origem = diretoria + 'Origin Custer Outliers.txt'

fid = open(fv_original, 'a')
fid_outlier_origem = open(fv_outlier_origem, 'a')
ident = 0
n_viagens_sem_cluster = 0
for file_name in os.listdir(diretoria):
    if ('Voyage ' or 'simp_Voyage ') in file_name:
        # extrai do nome o ponto de inicio e o ponto de fim e atribui um identificador
        # atribui a um indicador cluster 0 para cluster origem e cluster destino
        # escreve esta info num novo ficheiro
        fid.write(file_name[:-4])
        #fid.write("{0:03}".format(ident) + ' ' + file_name[:-4])
        fid.write('\n')
        # contar o nr de viagens na variave - n_viagens_sem_cluster
        n_viagens_sem_cluster = n_viagens_sem_cluster + 1
        ident = ident + 1

fid.close()

# neste novo ficheiro de viagens - fv_original
# copiar fv_original2 =fv_original

shutil.copy(fv_original, fv_original2)


no_cluster = 0
while n_viagens_sem_cluster != 0:
    fid = open(fv_original, "r")
    is_first_line = '1'
    viagem = []
    nn = '1'
    print('nn = ', nn)
    print('n_viagens_sem_cluster = ', n_viagens_sem_cluster)
    print('line 57')
    while True and nn == '1':

        # read next line
        line = fid.readline()
        print(line)
        # check if line is not null
        if not line:
            break
        a = 0
        b = 0
        c = 0
        A = []
        for y in range(len(line)):
            if line[y] == ' ' or line[y] == '\t':
                b = y
                A.append(line[a:b])
                a = b + 1
                c = c + 1
        b = y
        A.append(line[a:b])
        a = b + 1
        c = c + 1

        # you can access the line - in var A
        # A = np.array(["mmsi",     "origin_timestamp",     "destiny_timestamp",
        #               "origin_lon",   "origin_lat",
        #               "destiny_lon",  "destiny_lat"])
        # Example : Voyage 263758000 2008-07-13T19-49-39 2008-07-13T20-38-05 -9.21 38.7 38.68 38.7

        # ler 1ª linha do fv_original esta será a viagem original
        if is_first_line == '1':
            is_first_line = '0'
            viagem = A
        # Vamos ver se esta viagem é outlier
        fid2 = open(fv_original2, "r")
        is_first_line = 1
        n_ligacoes = 0
        while True and n_ligacoes < N_min:
            # read next line
            line2 = fid2.readline()
            # check if line is not null
            if not line2:
                break
            a2 = 0
            b2 = 0
            c2 = 0
            A2 = []
            for y2 in range(len(line2)):
                if line2[y2] == ' ' or line2[y2] == '\t':
                    b2 = y2
                    A2.append(line2[a2:b2])
                    a2 = b2 + 1
                    c2 = c2 + 1
            b2 = y2
            A2.append(line2[a2:b2])
            a2 = b2 + 1
            c2 = c2 + 1
            # you can access the line - in var A2
            if viagem != A2:
                # ver se a viagem se liga a esta na
                distance = (float(viagem[5]) - float(A2[5])) ** 2 + (float(viagem[6]) - float(A2[6])) ** 2
                if distance <= Epsilon:
                    n_ligacoes = n_ligacoes + 1
        fid2.close()
        # Se ele for outlier vai para um ficheiro especifico
        if n_viagens_sem_cluster == 1:
            # Abre ficheiro de outlier e escreve lá esta viagem e termina o clustering de origem
            for y4 in viagem:
                fid_outlier_origem.write(y4)
                fid_outlier_origem.write('\t')
            fid_outlier_origem.write('\n')
            nn = '0' # fecha o ciclo de clustering
            n_viagens_sem_cluster = 0
        elif n_ligacoes < N_min:
            # Abre ficheiro de outlier e escreve lá esta viagem
            for y4 in viagem:
                fid_outlier_origem.write(y4)
                fid_outlier_origem.write('\t')
            fid_outlier_origem.write('\n')
            n_viagens_sem_cluster = n_viagens_sem_cluster -1
            # Agora há que apagar este outlier da lista de viagens

            # apagar o fv2
            os.remove(fv_original2)
            # reescrever no fv2 o fv_original menos esta viagem
            fid.close()
            fid2 = open(fv_original2,'a')
            fid = open(fv_original, 'r')
            rr = '0' # 1ª linha
            while True:
                # read next line
                line_r = fid.readline()
                # check if line is not null
                if not line_r:
                    break
                if rr == '0': # se é a primeira linha
                    rr = '1'
                else:
                    fid2.write(line_r)
                    #fid2.write('\n')
            fid2.close()
            fid.close()
            os.remove(fv_original)
            #copiar o (novo) fv_2 para o fv_original
            shutil.copy(fv_original2, fv_original)

        # Se ele não for outlier então há um cluster com este ponto
        elif n_ligacoes == N_min:
            # Criar ficheiro para este cluster
            no_cluster = no_cluster + 1
            cluster_file_name = diretoria + 'Origin Cluster No. ' + str(no_cluster) + ".txt "
            cluster_fid = open(cluster_file_name, "a+")
            n_viagens_em_cluster = 1
            n_viagens_cluster_analizadas = 0
            # escrever a viagem original
            for y3 in viagem:
                cluster_fid.write(y3)
                cluster_fid.write('\t')
            cluster_fid.write('\n')
            cluster_fid.close()
            # Vamos correr para todas as viagens do cluster
            while n_viagens_cluster_analizadas < n_viagens_em_cluster:
                n_linha = 0
                cluster_fid = open(cluster_file_name, "r+")
                cluster_file_name2 = diretoria + 'Cluster Dummy' + ".txt "
                shutil.copy(cluster_file_name, cluster_file_name2)
                cluster_fid2 = open(cluster_file_name2, "a+")
                mmm = 0
                print('linha 161')
                while True and mmm == 0:
                    # read next line
                    cluster_line = cluster_fid.readline()
                    n_linha = n_linha + 1
                    if not cluster_line:
                        break
                    if n_linha > n_viagens_cluster_analizadas:
                        # check if line is not null
                        a_cluster = 0
                        b_cluster = 0
                        c_cluster = 0
                        A_cluster = []
                        for y_cluster in range(len(cluster_line)):
                            if cluster_line[y_cluster] == '\t' or cluster_line[y_cluster] == ' ':
                                b_cluster = y_cluster
                                A_cluster.append(cluster_line[a_cluster:b_cluster])
                                a_cluster = b_cluster + 1
                                c_cluster = c_cluster + 1
                        b_cluster = y_cluster
                        A_cluster.append(cluster_line[a_cluster:b_cluster])
                        a_cluster = b_cluster + 1
                        c_cluster = c_cluster + 1
                        # you can access the line - in var A_cluster
                        # vamos correr o segundo ficheiro de viagens originais
                        fid2 = open(fv_original2, "r")
                        is_first_line = 1
                        n_ligacoes = 0
                        print('linha 189')
                        while True:
                            # read next line
                            line2 = fid2.readline()
                            # check if line is not null
                            if not line2:
                                break
                            a2 = 0
                            b2 = 0
                            c2 = 0
                            A2 = []
                            for y2 in range(len(line2)):
                                if line2[y2] == ' ' or line2[y2] == '\t':
                                    b2 = y2
                                    A2.append(line2[a2:b2])
                                    a2 = b2 + 1
                                    c2 = c2 + 1
                            b2 = y2
                            A2.append(line2[a2:b2])
                            a2 = b2 + 1
                            c2 = c2 + 1
                            # you can access the line - in var A2
                            # ver se a viagem se liga a esta ligada à viagem
                            distance = (float(A_cluster[5]) - float(A2[5])) ** 2 \
                                       + (float(A_cluster[6]) - float(A2[6])) ** 2
                            if distance <= Epsilon and distance != float(0):
                                # estão esta viagem faz parte do cluster
                                n_viagens_em_cluster = n_viagens_em_cluster + 1
                                # vamos escrever no ficheiro
                                for y2 in A2:
                                    cluster_fid2.write(y2)
                                    cluster_fid2.write('\t')
                                cluster_fid2.write('\n')
                        mmm = 1
                fid2.close()
                fid.close()
                cluster_fid.close()
                cluster_fid2.close()
                os.remove(cluster_file_name)
                shutil.copy(cluster_file_name2, cluster_file_name)
                os.remove(cluster_file_name2)
                # Agora o ficheiro de cluster tem viagens novas
                # Antes de deixarmos o codigo correr para ver no original as que estão perto destas novas
                # viagens, vamos apagar as viagens que foram adicionadas ao ficheiro de cluster nesta iteração
                # do ficheiro original
                # Limpar o fv_2
                os.remove(fv_original2)
                fid2 = open(fv_original2, "a")
                # Abrir ficheiro fv_original
                fid = open(fv_original, "r")
                # Retira viagens de cluster da lista original
                while True:
                    # read next line
                    line4 = fid.readline()
                    # check if line is not null
                    if not line4:
                        break
                    a4 = 0
                    b4 = 0
                    c4 = 0
                    A4 = []
                    for y4 in range(len(line4)):
                        if line4[y4] == ' ' or line4[y4] == '\t':
                            b4 = y4
                            A4.append(line4[a4:b4])
                            a4 = b4 + 1
                            c4 = c4 + 1
                    b4 = y4
                    A4.append(line4[a4:b4])
                    a4 = b4 + 1
                    c4 = c4 + 1
                    # you can access the line - in var A4
                    esta_no_cluster = '0'
                    cluster_fid = open(cluster_file_name, "r")
                    while True and esta_no_cluster == '0':
                        # read next line
                        line5 = cluster_fid.readline()
                        # check if line is not null
                        if not line5:
                            break
                        a5 = 0
                        b5 = 0
                        c5 = 0
                        A5 = []
                        for y5 in range(len(line5)):
                            if line5[y5] == '\t' or line5[y5] == ' ':
                                b5 = y5
                                A5.append(line5[a5:b5])
                                a5 = b5 + 1
                                c5 = c5 + 1

                        # you can access the line - in var A5
#                        print(' ')
#                        print('A limpar o fv_o das viagens que estão no cluster_fid')
#                        print('Linha do cluster = ', A5)
#                        print('linha do fv_o =    ', A4)
#                        print(' ')
                        if A5 == A4:  # A viagem está no cluster
                            esta_no_cluster = '1'
                    # se não estiver no ficheiro de cluster, escrever no o fv_o2
                    if esta_no_cluster == '0':
                        for y4 in A4:
                            fid2.write(y4)
                            fid2.write('\t')
                        fid2.write('\n')
                    else:
                        n_viagens_sem_cluster = n_viagens_sem_cluster - 1
                fid2.close()
                fid.close()
                cluster_fid.close()
                # Substituir o fv_original pelo  fv_original2
                os.remove(fv_original)
                shutil.copy(fv_original2, fv_original)
                n_viagens_cluster_analizadas = n_viagens_cluster_analizadas + 1
        print('linha 299')
        nn = '0'

                    # Agora temos um ficheiro com todas as viagens desse cluster
                    # Há que:
                    # Atribuir a cada viagem o atributo 'core' ou 'outlier'
                    # [[[]]]

                # o original é o fv_original
                # a copia é o fv_original2
                # vamos apagar o fv_original2 e escrever nele as viagens que não estão neste novo cluster
                # depois copiamos para o fv_original
                # reducimos o n_viagens_sem_cluster como adequado
                # e deixamos o codigo correr de novo sem estas viagens que teem cluster

fid_outlier_origem.close()
fid.close()
fid2.close()

os.remove(fv_original2)
os.remove(fv_original)

# ----------------------------------- Destiny Clustering ------------------------------------------

# Retira as viagens na diretoria
# para todas as viagens

fv_original = diretoria + 'List of Voyages.txt'
fv_original2 = diretoria + 'List of Voyages2.txt'
fv_outlier_destino = diretoria + 'Destiny Custer Outliers.txt'

fid = open(fv_original, 'a')
fid_outlier_destino = open(fv_outlier_destino, 'a')
ident = 0
n_viagens_sem_cluster = 0
for file_name in os.listdir(diretoria):
    if 'Voyage ' in file_name:
        # extrai do nome o ponto de inicio e o ponto de fim e atribui um identificador
        # atribui a um indicador cluster 0 para cluster origem e cluster destino
        # escreve esta info num novo ficheiro
        fid.write(file_name[:-4])
        #fid.write("{0:03}".format(ident) + ' ' + file_name[:-4])
        fid.write('\n')
        # contar o nr de viagens na variave - n_viagens_sem_cluster
        n_viagens_sem_cluster = n_viagens_sem_cluster + 1
        ident = ident + 1

fid.close()

# neste novo ficheiro de viagens - fv_original
# copiar fv_original2 =fv_original

shutil.copy(fv_original, fv_original2)

no_cluster = 0
while n_viagens_sem_cluster != 0:
    fid = open(fv_original, "r")
    is_first_line = '1'
    viagem = []
    nn = '1'
    print('nn = ', nn)
    print('n_viagens_sem_cluster = ', n_viagens_sem_cluster)
    while True and nn == '1':

        # read next line
        line = fid.readline()
        # check if line is not null
        if not line:
            break
        a = 0
        b = 0
        c = 0
        A = []
        for y in range(len(line)):
            if line[y] == ' ' or line[y] == '\t':
                b = y
                A.append(line[a:b])
                a = b + 1
                c = c + 1
        b = y
        A.append(line[a:b])
        a = b + 1
        c = c + 1

        # you can access the line - in var A
        # A = np.array(["mmsi",     "origin_timestamp",     "destiny_timestamp",
        #               "origin_lon",   "origin_lat",
        #               "destiny_lon",  "destiny_lat"])
        # Example : Voyage 263758000 2008-07-13T19-49-39 2008-07-13T20-38-05 -9.21 38.7 38.68 38.7

        # ler 1ª linha do fv_original esta será a viagem original
        if is_first_line == '1':
            is_first_line = '0'
            viagem = A
        # Vamos ver se esta viagem é outlier
        fid2 = open(fv_original2, "r")
        is_first_line = 1
        n_ligacoes = 0 
        while True and n_ligacoes < N_min:
            # read next line
            line2 = fid2.readline()
            # check if line is not null
            if not line2:
                break
            a2 = 0
            b2 = 0
            c2 = 0
            A2 = []
            for y2 in range(len(line2)):
                if line2[y2] == ' ' or line2[y2] == '\t':
                    b2 = y2
                    A2.append(line2[a2:b2])
                    a2 = b2 + 1
                    c2 = c2 + 1
            b2 = y2
            A2.append(line2[a2:b2])
            a2 = b2 + 1
            c2 = c2 + 1
            # you can access the line - in var A2
            if viagem != A2:
                # ver se a viagem se liga a esta na
                distance = (float(viagem[5]) - float(A2[5])) ** 2 + (float(viagem[6]) - float(A2[6])) ** 2
                if distance <= Epsilon:
                    n_ligacoes = n_ligacoes + 1
        fid2.close()

        # Se ele for outlier vai para um ficheiro especifico
        if n_viagens_sem_cluster == 1:
            # Abre ficheiro de outlier e escreve lá esta viagem e termina o clustering de origem
            for y4 in viagem:
                fid_outlier_destino.write(y4)
                fid_outlier_destino.write('\t')
            fid_outlier_destino.write('\n')
            nn = 1
            n_viagens_sem_cluster = 0
        elif n_ligacoes < N_min:
            # Abre ficheiro de outlier e escreve lá esta viagem
            for y4 in viagem:
                fid_outlier_destino.write(y4)
                fid_outlier_destino.write('\t')
            fid_outlier_destino.write('\n')
            n_viagens_sem_cluster = n_viagens_sem_cluster - 1
            # Agora há que apagar este outlier da lista de viagens

            # apagar o fv2
            os.remove(fv_original2)
            # reescrever no fv2 o fv_original menos esta viagem
            fid.close()
            fid2 = open(fv_original2, 'a')
            fid = open(fv_original, 'r')
            rr = '0'  # 1ª linha
            while True:
                # read next line
                line_r = fid.readline()
                # check if line is not null
                if not line_r:
                    break
                if rr == '0':  # se é a primeira linha
                    rr = '1'
                else:
                    fid2.write(line_r)
                    # fid2.write('\n')
            fid2.close()
            fid.close()
            os.remove(fv_original)
            # copiar o (novo) fv_2 para o fv_original
            shutil.copy(fv_original2, fv_original)


        elif n_ligacoes == N_min:
            # Criar ficheiro para este cluster
            no_cluster = no_cluster + 1
            cluster_file_name = diretoria + 'Destiny Cluster No. ' + str(no_cluster) + ".txt "
            cluster_fid = open(cluster_file_name, "a+")
            n_viagens_em_cluster = 1
            n_viagens_cluster_analizadas = 0
            # escrever a viagem original
            for y3 in viagem:
                cluster_fid.write(y3)
                cluster_fid.write('\t')
            cluster_fid.write('\n')
            cluster_fid.close()
            # Vamos correr para todas as viagens do cluster
            while n_viagens_cluster_analizadas < n_viagens_em_cluster:
                n_linha = 0
                cluster_fid = open(cluster_file_name, "r+")
                cluster_file_name2 = diretoria + 'Cluster Dummy' + ".txt "
                shutil.copy(cluster_file_name, cluster_file_name2)
                cluster_fid2 = open(cluster_file_name2, "a+")
                mmm = 0
                print('linha 451')
                while True and mmm == 0:
                    # read next line
                    cluster_line = cluster_fid.readline()
                    n_linha = n_linha + 1
                    if not cluster_line:
                        break
                    if n_linha > n_viagens_cluster_analizadas:
                        # check if line is not null
                        a_cluster = 0
                        b_cluster = 0
                        c_cluster = 0
                        A_cluster = []
                        for y_cluster in range(len(cluster_line)):
                            if cluster_line[y_cluster] == '\t' or cluster_line[y_cluster] == ' ':
                                b_cluster = y_cluster
                                A_cluster.append(cluster_line[a_cluster:b_cluster])
                                a_cluster = b_cluster + 1
                                c_cluster = c_cluster + 1
                        b_cluster = y_cluster
                        A_cluster.append(cluster_line[a_cluster:b_cluster])
                        a_cluster = b_cluster + 1
                        c_cluster = c_cluster + 1
                        # you can access the line - in var A_cluster
                        # vamos correr o segundo ficheiro de viagens originais
                        fid2 = open(fv_original2, "r")
                        is_first_line = 1
                        n_ligacoes = 0
                        print('linha 475')
                        while True:
                            # read next line
                            line2 = fid2.readline()
                            # check if line is not null
                            if not line2:
                                break
                            a2 = 0
                            b2 = 0
                            c2 = 0
                            A2 = []
                            for y2 in range(len(line2)):
                                if line2[y2] == ' ' or line2[y2] == '\t':
                                    b2 = y2
                                    A2.append(line2[a2:b2])
                                    a2 = b2 + 1
                                    c2 = c2 + 1
                            b2 = y2
                            A2.append(line2[a2:b2])
                            a2 = b2 + 1
                            c2 = c2 + 1
                            # you can access the line - in var A2
                            # ver se a viagem se liga a esta ligada à viagem
                            distance = (float(A_cluster[7]) - float(A2[7])) ** 2 \
                                       + (float(A_cluster[8]) - float(A2[8])) ** 2
                            if distance <= Epsilon and distance != float(0):
                                # estão esta viagem faz parte do cluster
                                n_viagens_em_cluster = n_viagens_em_cluster + 1
                                # vamos escrever no ficheiro
                                for y2 in A2:
                                    cluster_fid2.write(y2)
                                    cluster_fid2.write('\t')
                                cluster_fid2.write('\n')
                        mmm = 1
                fid2.close()
                fid.close()
                cluster_fid.close()
                cluster_fid2.close()
                os.remove(cluster_file_name)
                shutil.copy(cluster_file_name2, cluster_file_name)
                os.remove(cluster_file_name2)
                # Agora o ficheiro de cluster tem viagens novas
                # Antes de deixarmos o codigo correr para ver no original as que estão perto destas novas
                # viagens, vamos apagar as viagens que foram adicionadas ao ficheiro de cluster nesta iteração
                # do ficheiro original
                # Limpar o fv_2
                os.remove(fv_original2)
                fid2 = open(fv_original2, "a")
                # Abrir ficheiro fv_original
                fid = open(fv_original, "r")
                # Retira viagens de cluster da lista original
                while True:
                    # read next line
                    line4 = fid.readline()
                    # check if line is not null
                    if not line4:
                        break
                    a4 = 0
                    b4 = 0
                    c4 = 0
                    A4 = []
                    for y4 in range(len(line4)):
                        if line4[y4] == ' ' or line4[y4] == '\t':
                            b4 = y4
                            A4.append(line4[a4:b4])
                            a4 = b4 + 1
                            c4 = c4 + 1
                    b4 = y4
                    A4.append(line4[a4:b4])
                    a4 = b4 + 1
                    c4 = c4 + 1
                    # you can access the line - in var A4
                    esta_no_cluster = '0'
                    cluster_fid = open(cluster_file_name, "r")
                    while True and esta_no_cluster == '0':
                        # read next line
                        line5 = cluster_fid.readline()
                        # check if line is not null
                        if not line5:
                            break
                        a5 = 0
                        b5 = 0
                        c5 = 0
                        A5 = []
                        for y5 in range(len(line5)):
                            if line5[y5] == '\t' or line5[y5] == ' ':
                                b5 = y5
                                A5.append(line5[a5:b5])
                                a5 = b5 + 1
                                c5 = c5 + 1
                        # you can access the line - in var A5
#                        print(' ')
#                        print('A limpar o fv_o das viagens que estão no cluster_fid')
#                        print('Linha do cluster = ', A5)
#                        print('linha do fv_o =    ', A4)
#                        print(' ')
                        if A5 == A4:  # A viagem está no cluster
                            esta_no_cluster = '1'
                    # se não estiver no ficheiro de cluster, escrever no o fv_o2
                    if esta_no_cluster == '0':
                        for y4 in A4:
                            fid2.write(y4)
                            fid2.write('\t')
                        fid2.write('\n')
                    else:
                        n_viagens_sem_cluster = n_viagens_sem_cluster - 1
                fid2.close()
                fid.close()
                cluster_fid.close()
                # Substituir o fv_original pelo  fv_original2
                os.remove(fv_original)
                shutil.copy(fv_original2, fv_original)
                n_viagens_cluster_analizadas = n_viagens_cluster_analizadas + 1

        print('linha 581')
        nn = '0'

fid_outlier_destino.close()
fid.close()
fid2.close()

os.remove(fv_original2)
os.remove(fv_original)



# --------------------------- Temos de juntar as origens com os destinos ------------------------------------------

# Vamos reconstruir o fv_original
# para todas as viagens

fv_original = diretoria + 'List of Voyages.txt'
fid = open(fv_original, 'a')
ident = 0
n_viagens_sem_cluster = 0
for file_name in os.listdir(diretoria):
    if 'Voyage ' in file_name:
        # extrai do nome o ponto de inicio e o ponto de fim e atribui um identificador
        # atribui a um indicador cluster 0 para cluster origem e cluster destino
        # escreve esta info num novo ficheiro
        fid.write(file_name[:-4])
        fid.write('\n')
        # contar o nr de viagens na variave - n_viagens_sem_cluster
        n_viagens_sem_cluster = n_viagens_sem_cluster + 1
        ident = ident + 1

fid.close()

# neste novo ficheiro de viagens - fv_original
# copiar fv_original2 =fv_original

shutil.copy(fv_original, fv_original2)

no_cluster = 0
fid = open(fv_original, "r")

while True:
    # read next line
    line = fid.readline()
    # check if line is not null
    if not line:
        break
    a = 0
    b = 0
    c = 0
    A = []
    for y in range(len(line)):
        if line[y] == ' ' or line[y] == '\t':
            b = y
            A.append(line[a:b])
            a = b + 1
            c = c + 1
    b = y
    A.append(line[a:b])
    a = b + 1
    c = c + 1
    # you can access the line - in var A
    # Para cada viagem vamos procurar pelo cluster de origem
    #Para cada ficheiro de cluster origem
    no_destino = ''
    no_origem = ''
    nn = '0'
    print('Viagem a analizar:')
    print(A)
    for file_name in os.listdir(diretoria):
        if 'Origin Cluster No. ' in file_name and nn == '0':
            cluster_fid = open(diretoria + file_name, "r")
            while True and nn == '0':
                # read next line
                cluster_line = cluster_fid.readline()
                # check if line is not null
                if not cluster_line:
                    break
                cluster_a = 0
                cluster_b = 0
                cluster_c = 0
                cluster_A = []
                for cluster_y in range(len(cluster_line)):
                    if cluster_line[cluster_y] == ' ' or cluster_line[cluster_y] == '\t':
                        cluster_b = cluster_y
                        cluster_A.append(cluster_line[cluster_a:cluster_b])
                        cluster_a = cluster_b + 1
                        cluster_c = cluster_c + 1
                cluster_b = cluster_y
                cluster_A.append(cluster_line[cluster_a:cluster_b])
                # you can access the cluster_line - in var cluster_A
                if A[0] == cluster_A[0]:
                    # Então vamos extrair do nome do ficheiro de cluster o nº do cluster de origem
                    nome = file_name[:-4] #para tirar o txt

                    no_origem = str(nome[19:])
                    # Para não juntar outliers
                    if no_origem == '0':
                        no_origem = ''
                    nn = '1'
    # Para cada viagem vamos procurar pelo cluster de destino
    # Para cada ficheiro de cluster de destino
    nn = '0'
    for file_name in os.listdir(diretoria):
        if 'Destiny Cluster No. ' in file_name and nn == '0':
            cluster_fid = open(diretoria + file_name, "r")
            while (True and nn == '0'):
                # read next line
                cluster_line = cluster_fid.readline()
                # check if line is not null
                if not cluster_line:
                    print('line 716')
                    break
                cluster_a = 0
                cluster_b = 0
                cluster_c = 0
                cluster_A = []
                for cluster_y in range(len(cluster_line)):
                    if cluster_line[cluster_y] == ' ' or cluster_line[cluster_y] == '\t':
                        cluster_b = cluster_y
                        cluster_A.append(cluster_line[cluster_a:cluster_b])
                        cluster_a = cluster_b + 1
                        cluster_c = cluster_c + 1
                cluster_b = cluster_y
                cluster_A.append(cluster_line[cluster_a:cluster_b])
                # you can access the cluster_line - in var cluster_A
                if A[0] == cluster_A[0]:
                    # Então vamos extrair do nome do ficheiro de cluster o nº do cluster de origem
                    nome = file_name[:-4]  # para tirar o txt
                    no_destino = str(nome[20:])
                    # Para não juntar outliers
                    if no_destino == '0':
                        no_destino = ''
                    nn = '1'
    if no_destino == '' or no_origem == '':
        # são outliers
        # Vamos mudar o nome do ficheiro dessa viagem para incluir os numeros de cluster
        # nome = diretoria + line[:-1] + ' OC' + str(no_origem) + ' DC' + str(no_destino) + '.txt'
        nome = diretoria + 'Cluster ' + '0-0  ' + ' ' + line[:-1] + '.txt'
        #line = line[4:]
        nome_o = diretoria + line[:-1] + '.txt'
        shutil.copy(nome_o, nome)
        os.remove(nome_o)
    else:
        # Vamos mudar o nome do ficheiro dessa viagem para incluir os numeros de cluster
        #nome = diretoria + line[:-1] + ' OC' + str(no_origem) + ' DC' + str(no_destino) + '.txt'
        nome = diretoria + 'Cluster ' + str(no_origem) + '-' + str(no_destino) + ' ' + line[:-1] + '.txt'
        #line = line[4:]
        nome_o = diretoria + line[:-1] + '.txt'
        print(nome_o)
        print(nome)
        shutil.copy(nome_o, nome)
        os.remove(nome_o)



# representar no mapa







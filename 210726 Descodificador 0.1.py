# -*- coding: utf-8 -*-
"""
Created on Mon Jul 26 16:32:35 2021

@author: Asus
"""
import os
from pyais.messages import NMEAMessage
import csv

dir = r'D:\Dados AIS cópias\DL_VslPos_2019127_2019231\test'

#Lista de ficheiros na diretoria
file_list = os.listdir(dir)

for x in file_list:
    if 'DL_VslPos_' in x:
        # ficheiro primario e duplicado
        nome_pr = x[:-4] + '.csv'
        nome_dp = x[:-4] + '_0.txt'
        os.rename(dir + '\\' + x \
                  , dir + '\\' + nome_dp)
        
        # abrir os ficheiros
        fid_dp = open(dir + '\\' + nome_dp, 'r')

        # Abrir o ficheiro da Lista
        count = 0 # nº da linha a ser analisado
        while True:
            count = count + 1
            # Get next line from file
            line = fid_dp.readline()
            # if line is empty
            # end of file is reached
            print(line)
            if not line:
                break
            #ignorar a 1ª Linha
            print('odd or even =', count)
            if count == 1:
                pass
                
            else:
                # se nº da linha for par: Lê a linha para A
                a = 0
                b = 0
                c = 0
                A = []
                for y in range(len(line)):
                    if line[y] == '\t' or line[y] == ' ':
                        b = y
                        A.append(line[a:b])
                        a = b + 1
                        c = c + 1
                b = y
                A.append(line[a:b])
                a = b + 1
                c = c + 1
                print('A =', A)
                # A = [NwDate	NwDateDupl	MsgChecksum	BSIndex	MsgId	MMSI	Latitude
                # Longitude	MsgData	SOG	COG	Name	Type	Length	Beam]
                if len(A) > 8 and '!AIVDM' in A[8]:
                    # descodificar o campo da 'mensagem_AIS'
                    message = NMEAMessage.from_string(A[8])

                    G = message.decode()
                    print(G.content)

                    if 'lon' in G.content and 'lat' in G.content:
                        #escrever no novo ficheiro
                        with open(dir + '\\' + nome_pr, 'a', encoding='UTF8', newline='') as f:
                            writer = csv.writer(f)
                            # write the data
                            writer.writerow((G.content['mmsi'], G.content['lon'], G.content['lat']))
                        f.close()
        fid_dp.close()






        # após ler um ficheiro, apagar o duplicado

        os.remove(dir + '\\' + nome_dp)




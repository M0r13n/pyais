''' ------------------------------ 210903 Clusterer 1.0  ------------------------------'''

#    Os objetivos deste código são:
# Pegar nos ficheiros de viagem produzidos pelo Monnitraffic 0.8 e agrupálos por par origem-destino

import math
import os


diretoria =




def write_in_file(vector, file_name):
    fid = open(file_name, 'a')
    for x in len(vector):
        fid.write(vector[x])
        fid.write('\t')
    fid.write('\n')
    fid.close()


def str_to_vector(line):
    a = 0
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

    return A

def get_distance(lon_A, lat_A, lon_B, lat_B):
    """Calculates spherical distance between point A and point B"""
    """Uses dot product to find alpha,
    which is the angle between vectors OA and OB,
    where O is the centre of the earth"""
    if lon_A == lon_B and lat_A == lat_B:
        distance = 0
    else:
        lon_A = lon_A * math.pi / 180
        lat_A = lat_A * math.pi / 180
        lon_B = lon_B * math.pi / 180
        lat_B = lat_B * math.pi / 180
        dot_product = \
            math.cos(lon_A) * math.cos(lat_A) * math.cos(lon_B) * math.cos(lat_B)\
            + math.sin(lon_A) * math.cos(lat_A) * math.sin(lon_B) * math.cos(lat_B)\
            + math.sin(lat_A) * math.sin(lat_B)
        alpha = math.acos(dot_product)
        # average radius of the Earth, in kilometers, is 6371
        distance = 6371 * alpha
    return distance

def delete_line_from_file(file, a):
    fid = open(file, 'r')
    fid2 = open(file[:-4] + '2.txt', 'a')
    count = 0
    while True:
        line = fid.readline()
        if not line:
            break

        if count is not a:
            fid2.write(line)
            fid2.write('\n')

        count = count + 1

    fid.close()
    fid2.close()
    os.remove(file)
    os.rename(file[:-4] + '2.txt', file)


def get_line_from_file(x,file_name):
    a = 0

    fid = open(file_name, 'r')
    count = 0
    while True:
        a = a + 1
        line = fid.readline()
        if not line or a > x:
            break

        if a == x:
            V = str_to_vector(line)

    fid.close()

    return V



def Clustering(file, diretoria):
    #clustering controlers
    epsilon = 2  # in km
    n_min = 5

    #file = [id, lon lat]
    fid = open(diretoria + file, 'r')
    zz = 0
    while True:
        line = fid.readline()
        if not line:
            break
        zz = zz + 1
        # Ler a linha para um vetor
        write_in_file([line, '0'], file)

    # zz == number of points to cluster
    #file = [id lon lat num_cluster]

    #Vamos começar a avaliar cada um dos pontos
    num_pt_sem_cluster = zz
    num_cluster = 0
    while num_pt_sem_cluster > 0:
        # Iteramos o ponto V com todos os pontos a ver se este ponto é core de cluster

        fid = open(file, 'r')
        first_line = '0'
        num_ligaçoes = 0
        while True and num_ligaçoes != n_min:
            line = fid.readline()
            if not line:
                break

            if first_line == '0':
                first_line = '1'
                V = str_to_vector(line)
            else:
                A = str_to_vector(line)

                dist = get_distance(float(V[1]),float(V[2]),float(A[1]), float(A[2]))
                if dist < epsilon:
                    num_ligaçoes = num_ligaçoes + 1
        fid.close()

        if num_ligaçoes != n_min: # O ponto V é outlier
            write_in_file(V, ''.join([diretoria, 'CF €£ Outliers.txt']))
            num_pt_sem_cluster = num_pt_sem_cluster - 1

            # deletes exact match from file - code from https://pynative.com/python-delete-lines-from-file/
            delete_line_from_file(file, [0])
        else:
            # then point V is the core of a new cluster
            # this cluster number is here:
            num_cluster = num_cluster + 1
            # the cluster will be in a separate file called:
            file_cluster_name = ''.join([diretoria, 'CF €£ Cluster ',str(num_cluster),'.txt'])
            num_cluster = num_cluster + 1
            fid_c = open(file_cluster_name, 'a')
            write_in_file(V, file_cluster_name)
            num_pt_sem_cluster = num_pt_sem_cluster -1

            # Let's iterate over all points in that cluster
            x = 1 #contagem a partir do 1 (pq conta as linhas do ficheiro e não há linha 0

            while x <= num_cluster:
                V = get_line_from_file(x, file_cluster_name)
                V = str_to_vector(V)
                # com o ponto V, vamos ver todos os pontos que não tem cluster que estão ligados a V
                fid = open(file, 'r')
                # neste vetor registamos os que estão ligados a V
                # estes pts vão para o ficheiro de cluster e terão de ser apagados do ficheiro de pontos

                R = []
                xx = 0 # contagem a partir do 0
                while True:
                    line = fid.readline()
                    if not line:
                        break

                    A = str_to_vector(line)

                    # Se o ponto V estiver repetido, é para apagar
                    if A[0] == V[0]:
                        R = R + [xx]
                    else:
                        # ver o critério da distância
                        dist = get_distance(V[1], V[2], A[1], A[2])
                        if dist <= epsilon:
                            # este pt é adicionado ao cluster
                            write_in_file(A, file_cluster_name)
                            num_cluster = num_cluster +1
                            num_pt_sem_cluster = num_pt_sem_cluster - 1
                            #Este ponto é apagado do ficheiro
                            R = R + [xx]

                    xx = xx + 1
                #delete R from file
                delete_line_from_file(file, R)

                x = x + 1





























# Produzir ficheiro de viagens
# Make voyage file
# where line is [id; lon_o; lon_d; lat_o; lat_d]
voyages_file = ' '.join([diretoria, 'List of Voyages.txt'])
fid_v = open(voyages_file, 'a')

for x in os.listdir(diretoria):
    if 'Voyage ' in x:
        A = str_to_vector(x[:-4])
        fid_v.write(A[0])
        fid_v.write(' ')
        fid_v.write(A[-4])
        fid_v.write(' ')
        fid_v.write(A[-3])
        fid_v.write(' ')
        fid_v.write(A[-2])
        fid_v.write(' ')
        fid_v.write(A[-1])
        fid_v.write('\n')
fid_v.close()


''' ----- clusters de portos conhecidos -----'''
## file_ports = [port_name num_boxes [Lon_min lon_max lat_min lat_max]

# read each line in file_ports
file_ports = ''.join([diretoria, 'File_Ports.txt'])

# file_v = [id lon_o lon_d lat_o lat_d]
# file_v ie the file with the voyages
fid_v = open(voyages_file, 'r')
while True:
    line_v = fid_v.readline()
    if not line_v:
        break
    # Ler a linha para um vetor
    A_v = str_to_vector(line_v)


    fid_ports = open(file_ports, 'r')
    zo = '0'
    zd = '0'
    while True:
        line_ports = fid_ports.readline()
        if not line_ports or (z0 == '1' and zd == '1'):
            break
        # Ler a linha para um vetor
        A_ports = str_to_vector(line_ports)
        z = 0 # counter for the number of prot boxes xhexked

        for x in A_ports[1]:
            if zo == '0':
                if A_ports[2 + z*4] < A_v[1] < A_ports[3 + z * 4] and \
                        A_ports[4 + z*4] < A_v[3] < A_ports[5 + z * 4]:
                    #then the voyage origin is within the port
                    zo = '1' # meaning an origine cluster has been found
                    write_in_file([A_v[0], A_v[1], A_v[3]], ''.join([diretoria, 'Origin Cluster ',A_ports[0], '.txt']))

            if zd == '0':
                if A_ports[2 + z*4] < A_v[2] < A_ports[3 + z * 4] and \
                        A_ports[4 + z*4] < A_v[4] < A_ports[5 + z * 4]:
                    #then the voyage destiby is within the port
                    zd = '1' # meaning an origine cluster has been found
                    write_in_file([A_v[0], A_v[2], A_v[4]], ''.join([diretoria, 'Destiny Cluster ',A_ports[0], '.txt']))

    if zo == '0':
        write_in_file([A_v[0], A_v[1], A_v[3]], ''.join([diretoria, 'Voyages_Origins.txt']))

    if zd == '0':
        write_in_file([A_v[0], A_v[2], A_v[4]], ''.join([diretoria, 'Voyages_Destinies.txt']))

# Aqui temos dois ficheiros de pontos, um com as origens das viagens e outro com os destinos das viagens
# diretoria + 'Voyages_Origins.txt'
# diretoria +'Voyages_Destinies.txt'
# Estes ficheiros estão no formato [id lon lat], prontos a entras na função de clustering



''' ------------------------------ Clustering Origem  ------------------------------'''
# A função clustering trabalha com os pontos do ficheiro [id lon lat]
# e produz um ficheiro para cada cluster
# como não discrimina se o ficheiro de input é origem ou destino, temos de os reformatar
# os ficheiros de cluster que saem da função começam todos com 'CF €£ '


# vamos prduzir os clusters de origem
Clustering(''.join([diretoria, 'Voyages_Origins.txt']), diretoria)

# Vamos renomeá-los
#Lista de ficheiros na diretoria
file_list = os.listdir(diretoria)

for x in file_list:
    if 'CF €£ ' in x:
        os.rename(" ".join(['Origem', x[6:]]), x)


''' ------------------------------ Clustering Destino  ------------------------------'''
# vamos prduzir os clusters de origem
Clustering(''.join([diretoria, 'Voyages_Destinies.txt']), diretoria)

# Vamos renomeálos
#Lista de ficheiros na diretoria
file_list = os.listdir(diretoria)

for x in file_list:
    if 'CF €£ ' in x:
        os.rename(" ".join(['Destino', x[6:]]), x)





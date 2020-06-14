#TFTP SERVER

# Autors: Achraf Hmimou i Oriol Fernandez Briones

# ========================== IMPORT =========================== #
from socket import *                                            #
from struct import *                                            #
import select, time, random, struct, sys                        #
# ========================= VARIABLES ========================= #
serverName = 'localhost'    # Es la direcció IP Del servidor    #
serverPort = 69   # Port on el servidor rebtra les conexions    #
serverSocket = socket(AF_INET,SOCK_DGRAM)#Declaració del socket #
serverSocket.bind(('',serverPort))#Iniciem el socket al port 69 #
clientAddress = (serverName,serverPort)                         #
print ('Servidor llest per rebre conexions')                    #
# ========================= CONSTANTS ========================= #
TFTP_PAQUETS = {                                                #
    'read': 1,  # Petició de lectura (RRQ)                      #
    'write': 2, # Petició d'escriptura (WRQ)                    #
    'data': 3,  # Dades (DATA)                                  #
    'ack': 4,  	# Reconeixement (ACK)                           #
    'error': 5,	# Error (ERROR)                                 #
    'oack': 6   # Opcions (OACK)                                #
}                                                               #
server_error_msg = {                                            #
    0: "No identificat, vegeu el missatge d'error(si existeix)",#
    1: "Fitxer no trobat",                                      #
    2: "Violació d'accés",                                      #
    3: "Disc ple o s'ha excedit la capacitat",                  #
    4: "Operació TFTP il·legal",                                #
    5: "Identificador de transferència desconegut",             #
    6: "El fitxer ja existeix",                                 #
    7: "Usuari desconegut",                                     #
    8: "Error de negociació d'opcions"                          #
}                                                               #
                                                                #
#opcions per defecte...                                         #
TFTP_OPTIONS = {                                                #
    'mode': 'netascii',                                         #
    'host': 'localhost',                                        #
    'op': 0,                                                    #
    'filename': 'fitxer',                                       #
    'blksize': 512,                                             #
    'timeout': 3000                                             #
}                                                               #
# ============================================================= #


''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

'''                   Especificació dels diferents paquets                       '''

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''


# Engarregat de empaquetar el numero de sequencia en un paquet de reconeixement
def ack(num_seq):
    """
    Aquesta funció construeix el paquet de ACK (Codi 04) en el següent format:

      2 bytes     2 bytes
    -------------------------
    |    04    |   Block #  |
    -------------------------
    """

    # S'empaqueta en 4 bytes el codi 04 i el numero de sequencia
    formatter = '>HH'                                                                # Defineix una reserva de 2+2 bytes
    paq = pack(formatter, TFTP_PAQUETS['ack'], num_seq)                              # Empaquetem en els bytes necessaris
    try:
        print("Envia ACK ", num_seq)
        sent = serverSocket.sendto(paq, clientAddress)                               # Envia el paquet
    except Exception as e:                                                           # En el cas de que es perdi la conexió
        print("Error de connexió")



# Encarregat de desenpaquetar el paquet ACK i retornar el numero de bloc del ACK
def extract_ack(ack):
    e_ack = unpack('>HH',ack)
    print ('ACK rebut ',e_ack[1])                                                        # Desempaqueta el paquet de format 2+2 bytes
    return e_ack[1]                                                                  # Retorna el numero de bloc del ACK



''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

# Encarregat de crear, empaquetar i enviar el paquet d'ERROR
def paq_error(errorcode):
    """
    Aquesta funció construeix el paquet de error (Codi 05) en el següent format:

     2 bytes      2 bytes      string    1 byte
    --------------------------------------------
    |   05    |  ErrorCode |   ErrMsg   |   0  |
    --------------------------------------------
    """

    # S'empaqueta en n bytes el codi 05, el codi d'error, missatge de l'error i un 0 final
    formatter = '>HH{}sb'                                        # Defineix una reserva de 2+2+n+1 bytes
    print("Error: ",server_error_msg[errorcode])
    formatter = formatter.format(len(server_error_msg[errorcode]))   # Definim el tamany de n
    paq = pack(formatter, TFTP_PAQUETS['error'], int(errorcode), bytes(server_error_msg[errorcode], 'utf-8'), 0) # Empaquetem en els bytes necessaris
    print("Error durant la transferència")

    try:
        sent = serverSocket.sendto(paq, clientAddress)      # Envia el paquet
    except Exception as e:                                  # En el cas de que es perdi la conexió
        print("Error de connexió")


# Encarregat de desenpaquetar el paquet d'error i retornar el codi error
def extract_error(paq_error):
    if (len(paq_error) == 4):  # Sense missatge d'error
        formatter = '>HH'
    else:
        formatter = '>HH{}sb'                                                          # Defineix una reserva de 2+2+n+1 bytes
        formatter = formatter.format(len(paq_error)-5)                                 # Definim el tamany de n

    e_error = unpack(formatter,paq_error)                                              # Desempaqueta el paquet de format 2+2+n bytes
    return e_error[1]                                                                  # Retorna el contingut del paquet


''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''



# Encarregat de crear, empaquetar i enviar el paquet de DATA
def dades (num_seq, data):
    formatter = '>HH{}s'                                                               # Defineix una reserva 2+2+n bytes
    formatter = formatter.format(len(data))                                            # Definim el tamany de n
    paq = pack(formatter, TFTP_PAQUETS['data'], num_seq, data)                         # Empaqueta el paquet de format 2+2+n bytes
    try:
        print("Envia paquet ",num_seq)
        sent = serverSocket.sendto(paq, clientAddress)                                 # Envia el numero de sequencia al client
    except Exception as e:                                                             # En el cas de que es perdi la conexió
        print("Error de connexió")

# Encarregat de desenpaquetar el paquet DATA i retornar el numero de sequencia
def numero_sequencia(data):
    formatter = '>HH{}s'                                                               # Defineix una reserva de 2+2+n bytes
    formatter = formatter.format(len(data)-4)                                          # Definim el tamany de n
    num_seq = unpack(formatter,data)                                                   # Desempaqueta el paquet de format 2+2+n bytes
    print("Paquet rebut", num_seq[1])
    return num_seq[1];                                                                 # Retorna el numero de sequencia



# Encarregat de desenpaquetar el paquet DATA i retornar el contingut
def extract_data(data):
    formatter = '>HH{}s'                                                               # Defineix una reserva 2+2+n bytes
    formatter = formatter.format(len(data)-4)                                          # Definim el tamany de n
    e_data = unpack(formatter,data)                                                    # Desempaqueta el paquet de format 2+2+n bytes

    if TFTP_OPTIONS['mode'] == 'netascii':
        return e_data[2].decode()                                                      # Retorna el contingut del paquet
    else: #octet
        return bytes(e_data[2])

# Encarregat de comprobar si el missatge rebut es l'ultim de la transferencia
def comprobaUltim(data):
    if (len(data) < int(TFTP_OPTIONS['blksize'])):
        return True
    else:
        return False


''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''


'''

                    NEGOCIACIÓ D'OPCIONS (RFC 1782)

Read Request

      client                                           server
      -------------------------------------------------------
      |1|foofile|0|octet|0|blksize|0|1432|0|  -->               RRQ
                                    <--  |6|blksize|0|1432|0|   OACK
      |4|0|  -->                                                ACK
                             <--  |3|1| 1432 octets of data |   DATA
      |4|1|  -->                                                ACK
                             <--  |3|2| 1432 octets of data |   DATA
      |4|2|  -->                                                ACK
                             <--  |3|3|<1432 octets of data |   DATA
      |4|3|  -->                                                ACK

   Write Request

      client                                           server
      -------------------------------------------------------
      |2|barfile|0|octet|0|blksize|0|2048|0|  -->               RRQ
                                    <--  |6|blksize|0|2048|0|   OACK
      |3|1| 2048 octets of data |  -->                          DATA
                                                   <--  |4|1|   ACK
      |3|2| 2048 octets of data |  -->                          DATA
                                                   <--  |4|2|   ACK
      |3|3|<2048 octets of data |  -->                          DATA
                                                <--  |4|3|   ACK
'''


# Encarregat de crear el paquet oack amb la llista d'opcions que el servidor ha acceptat
def paq_oack(aceptades):
    formatter = '>H'

    for i in range(0,len(aceptades),2):
        formatter += str(len(str(aceptades[i]))) + 's' + 'B'

    paq = pack(formatter, TFTP_PAQUETS['oack'], *aceptades)
    paq = paq.replace(b'\x00\x00\x00',b'')

    print("Paquete OACK enviat")

    try:
        sent = serverSocket.sendto(paq, clientAddress)                          # Envia el numero de sequencia al client
    except Exception as e:                                                       # En el cas de que es perdi la conexió
        print("Error de connexió")


#Comprobem que els valors de les opcions son valids
def comproba_valid(nom, valor):
    if nom == "mode":
        return valor == "netascii" or valor == "octet"
    elif nom == "blksize":
        return int(valor) in range(8,4096)
    elif nom == "timeout":
        return int(valor) in range(100,255000)
    elif nom == "tsize":
        return True


# Funcio que llegeix la request i determina quines opcions son valides.
def typeRequest(data):
    opcode = int.from_bytes(data[:2], "big")
    nameEnd = data.find(b'\0', 2)
    filename = data[2:nameEnd].decode('utf-8')
    modeEnd = data.find(b'\0', nameEnd+1)
    mode = data[nameEnd+1:modeEnd].decode('utf-8')
    format = '>h' + (str(len(filename))+'s'+'B'+str(len(mode))+'s'+'B')


    aceptades = []                                                              # Llista amb totes les opcions que acepa el servidor


    TFTP_OPTIONS['mode'] = mode                                                 # Guardem el mode
    TFTP_OPTIONS['filename'] = filename                                         # Guardem el nom del archiu


    #En aquest bloc desempaquetem els diferents parells opcio / valor
    i = 0
    begin = modeEnd
    end = 0
    while end != -1:                                                            # Recorrem elel paquet de petició
        i%=2
        if i == 0:
            end = data.find(b'\0', begin+1)
            name = data[begin+1:end].decode('utf-8')
            if str(len(name)) != "0":
                format += str(len(name)) + 's' +'B'
        else:
            end = data.find(b'\0', begin+1)
            value = data[begin+1:end].decode('utf-8')
            if str(len(value)) != "0":
                format += str(len(value)) + 's' +'B'
            if comproba_valid(name, value):                                     # En cas que sigui una opcio valida la posem en el vector aceptada
                TFTP_OPTIONS[name] = value
                aceptades.append(bytes(name, 'utf-8'))
                aceptades.append(0)
                aceptades.append(bytes(value, 'utf-8'))
                aceptades.append(0)
        begin = end
        i+=1


    request = unpack(format, data)

    # En cas de que s'hagi acceptat alguna opció
    if(aceptades):
        #Enviem el paquet OACK
        paq_oack(aceptades)

        # En cas de que sigui un GET esperarem un ACK 0
        if  opcode == 1:   # GET
            data, clientAddress = serverSocket.recvfrom(65507)

            codi = int.from_bytes(data[:2], "big")

            if codi == 4:
                reconeixement = extract_ack(data)
                return request[0]
            else:
                print("Error: ", server_error_msg[extract_error(data)])
                return -1
    else:
    #En cas de que no s'accepti cap opció enviem un ACK 0
        if request[0] == 2:
            ack(0)

    # Retornem si Es GET O PUT
    return request[0]


''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

'''                        OPERACIONS GET / PUT                                  '''

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''


# Encarregat de realitzar les operacions necessaries donada una petició GET per part del client
def get():
    global clientAddress

    try:
        print("Enviant dades...")

        # Obrim el fitxer....
        try:
            if TFTP_OPTIONS['mode'] == 'netascii':
                fd = open(TFTP_OPTIONS['filename'],'r')                                     # Obrim l'archiu i deixem el file descriptor a la variable f
            else:
                fd = open(TFTP_OPTIONS['filename'],'rb')                                    # Obrim l'archiu i deixem el file descriptor a la variable f
        except:
            # En cas, de que l'archiu no existeixi enviem paquet d'error
            paq_error(1)
            raise Exception(server_error_msg[1])

        num_seq = 1
        data = fd.read(int(TFTP_OPTIONS['blksize']))
        vegades = 3                                                                         # Numero de cops que intentará reenviar un paquet
        tamany_ultim = 0

        # En cas de que el fitxer estigui buit enviem nomes un paquet amb la capçelera
        if not data:
            dades(num_seq,bytes("", 'utf-8'))
            ack, clientAddress = serverSocket.recvfrom(65507)                               # Espera ack
            print ('ACK rebut ',extract_ack(ack))

        # En cas de que hi hagi informació en el fitxer comencem la transmissió
        while(data):
            serverSocket.settimeout(int(TFTP_OPTIONS['timeout'])/1000)                      # Inicia timeout
            try:
                if TFTP_OPTIONS['mode'] == 'netascii':                                      # en netascii
                    dades(num_seq, bytes(data,encoding='utf8'))
                else:
                    dades(num_seq, data)                                                    # en octet

                tamany_ultim = len(data);
                ack, clientAddress = serverSocket.recvfrom(65507)                           # Espera ack

                opcode = int.from_bytes(ack[:2], "big")
                if(opcode == 4):                                                            # Comproba si rebem un ACK o un ERROR
                    reconeixement = extract_ack(ack)                                        # Extraiem el ack
                    vegades = 3
                    if reconeixement == num_seq:
                        data = fd.read(int(TFTP_OPTIONS['blksize']))                        # En cas de que coincideixi amb el numero de sequencia
                        if num_seq == 65535:                                                # Llegim més informació
                            num_seq = 1
                        else:
                            num_seq += 1
                else:
                    # En cas de que rebem un error en comptes de un ack
                    print("Error: ", server_error_msg[extract_error(ack)])
                    break

            except timeout:
                # En cas de que hi hagi un timeout retransmitim el paquet fins a 3 vegades
                vegades -= 1
                print("Retransmitim paquet amb numero de sequencia: ",num_seq)
                if not vegades:
                    print("No ha sigut posible enviar el paquet")
                    break
        if not data:
            # Per detectar paquets que siguin multiples de 512
            if (tamany_ultim == int(TFTP_OPTIONS['blksize'])):
                print("paquet 0")
                dades(num_seq,bytes("", 'utf-8'))
                ack, clientAddress = serverSocket.recvfrom(65507)                       # Espera ack
                reconeixement = extract_ack(ack)

            print("S'ha acabat la transferencia...")
    except timeout:
        print("S'ha acabat la transferencia...")


''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

# Encarregat de realitzar les operacions necessaries donada una petició GET per part del client
def put():
    #Obrim l'archiu....
    mode = 'w'
    if TFTP_OPTIONS['mode'] == 'octet':
        mode += 'b'

    try:
        fd = open(TFTP_OPTIONS['filename'],mode)                                     # Obrim el file descriptor de l'archiu on farem la escritura
    except:
        # En cas, de que l'archiu no existeixi enviem paquet d'error
        paq_error(1)
        raise Exception(server_error_msg[1])

    print("Rebent dades...")
    fin = False                                                                      # Per a controlar cuan hem arribat a l'ultim paquet

    try:
        while True:
            serverSocket.settimeout(int(TFTP_OPTIONS['timeout'])/1000)               # Establint un timeout
            data,clientAddress = serverSocket.recvfrom(65507)                        # Reb dades (Paquets de max tamany)

            try:
                num_sec = numero_sequencia(data)                                     # Extraiem el numero de sequencia
                try:
                    fd.write (extract_data(data))                                    # Escrivim en el archiu
                except:
                    # Disc ple
                    raise server_error_msg[3]

                ack(num_sec)                                                         # Enviem ACK
                num_aux = num_sec
                fin = comprobaUltim(data)                                            # Comprobem si es el ultim paquet
            except Exception as error:
                paq_error(5)
                fd.close()                                                          # Durant la transmissio
                raise Exception(server_error_msg[5])
                break;

    except timeout:                                                                  # En cas del que el timeout s'hagi produit perque s'ha transmes tot el fitxer
        if fin:
            print("Ha acabat la transferencia")                                      # Terminació prematura
        else:
            paq_error(5)
            fd.close()                                                               # Durant la transmissio
            raise Exception(server_error_msg[5])

    fd.close()






''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

'''                                 MAIN                                         '''

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''


# ESTABLIMENT DE CONEXIÓ

msg, clientAddress = serverSocket.recvfrom(65507)	                          # Llegir la peticio del client

# TAnquem la conexió pel port 69
serverSocket.close()

# Obrim una nou socket utilitzant un port public
newPort = random.randint(1024,49151)                                          # Ports publics

serverSocket = socket(AF_INET,SOCK_DGRAM)
serverSocket.bind(('',newPort))


def main():
    request = typeRequest(msg)      #Determinem el tipus de conexió
    if request == 1:
        get()
    elif request == 2:
        put()

    serverSocket.close()            #Tanquem la conexió

if __name__ == '__main__':
    main()

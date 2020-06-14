#TFTP CLIENT

# Autors: Achraf Hmimou i Oriol Fernandez Briones

# ========================== IMPORT =========================== #
from socket import *                                            #
from struct import *                                            #
import select, time, random, struct, sys                        #
# ========================= VARIABLES ========================= #
serverName = 'localhost'    # Es la direcció IP Del servidor    #
serverPort = 69   # Port on el servidor rebtra les conexions    #
clientSocket = socket(AF_INET,SOCK_DGRAM)#Declaració del socket #
serverAddress = (serverName, serverPort)                        #
                                                                #
# ========================= CONSTANTS ========================= #
TFTP_PAQUETS = {                                                #
    'read': 1,  # Petició de lectura (RRQ)                      #
    'write': 2, # Petició d'escriptura (WRQ)                    #
    'data': 3,  # Dades (DATA)                                  #
    'ack': 4,  	# Reconeixement (ACK)                           #
    'error': 5,	# Error (ERROR)                                 #
    'oack': 6   # Opcions (OACK)                                #
}                                                               #
                                                                #
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
# Valors per defecte                                            #
TFTP_OPTIONS = {                                                #
    'mode': 'octet',                                         #
    'host': 'localhost',                                        #
    'op': 0,                                                    #
    'origen': '',                                               #
    'desti': 'fitxer',                                          #
    'blksize': 512,                                             #
    'timeout': 3000                                             #
}                                                               #
                                                                #
# Paquet de negociació d'OPCIONS                                #
TFTP_OAK = {                                                    #
'mode': '',                                                     #
'blksize': 0,                                                   #
'timeout': 0                                                    #
}                                                               #
                                                                #
# ============================================================= #


''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

'''                   Especificació dels diferents paquets                       '''

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''



#Funció encarregada de enviar la request amb o sense negociació d'opcions
def send_request(filename):
    """
    Aquesta funció construeix el paquet de request (RRW/WRQ) en el següent format:

     2 bytes    string      1 byte    string    1 byte      string    1 byte    string     1 byte
    -----------------------------------------------------------------------------------------------
    | 01/02 |  Nom_fitxer  |   0   |    Mode    |   0  |   opció n  |   0   |   valor n   |   0   |
    -----------------------------------------------------------------------------------------------
    """

    # S'empaqueta en n bytes el codi 01 o 02, n bytes del nom del fitxer, 1 byte per al 0, m bytes per al mode i un byte final
    formatter = '>H{}sB{}sB{}sB{}sB{}sB{}sB'

    formatter = formatter.format (                                                     # Defineix una reserva de 2+n+1+m+1 bytes
        len(filename),
        len(TFTP_OPTIONS['mode']),
        len('blksize'),
        len(str(TFTP_OPTIONS['blksize'])),
        len('timeout'),
        len(str(TFTP_OPTIONS['timeout']))
    )

    paq = pack(formatter,                                                              # Empaquetem en els bytes necessaris
    TFTP_OPTIONS['op'],
    bytes(filename, 'utf-8'),
    0,
    bytes(TFTP_OPTIONS['mode'],'utf-8'),
    0,
    bytes('blksize', 'utf-8'),
    0,
    bytes(str(TFTP_OPTIONS['blksize']), 'utf-8'),
    0,
    bytes('timeout', 'utf-8'),
    0,
    bytes(str(TFTP_OPTIONS['timeout']), 'utf-8'),
    0
    )
    sent = clientSocket.sendto(paq, serverAddress)


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


# Funcio encarregada de comprobar els camps de negociació d'opcions
def comprobaOACK(TFTP_OPTIONS, TFTP_OAK):
    for name in TFTP_OAK:
        if TFTP_OAK[name] == '' or TFTP_OAK[name] == 0:                             # En cas de que s'hagi negociat alguna de les opcions seguents es posa el valor per defecte
            if name == "blksize":
                TFTP_OPTIONS[name] = 512
            elif name == "timeout":
                TFTP_OPTIONS[name] = 3000
            elif name == "mode":
                TFTP_OPTIONS[name] = 'octet'
        else:
            TFTP_OPTIONS[name] = TFTP_OAK[name]


# Mira si les opcions que rretorna el servidor son las que ha demanat el client
def tractaOpcions(data, op):
    opcode = int.from_bytes(data[:2],"big")
    modeEnd = data.find(b'\0', 2)


    # Aquest bloc recorre tot el paquet OACK que retorna el servidor i mira si hi alguna de les opcions que retorna es inconsistent
    # amb el que s'habia demanat en un principi. Si es el cas el client envia un paquet d'error amb codi 8
    if opcode == 6:
        i = 0
        begin = 1
        end = 0
        while end != -1:
            i%=2
            if i == 0:
                end = data.find(b'\0', begin+1)                                             # Aprofitem que els diferents caps estan separats per 0
                name = data[begin+1:end].decode('utf-8')
            else:
                end = data.find(b'\0', begin+1)
                value = data[begin+1:end].decode('utf-8')
                try:
                    TFTP_OAK[name] = value                                                  # Posem el valor retornat al diccionari OAK per despres fer les comprobacions pertintents
                    # Quan t'arriba una opció que no as demanat al paquet OACK
                    if (str(TFTP_OPTIONS[name]) != str(value)):   #NO SEAN DIFERENTES DE LAS QUE HEMOS RECIBIDO
                        # Enviem el paquet d'error
                        paq_error(8);
                        break
                except Exception as error:
                    print("Error: ", error)
                    break
            begin = end
            i+=1

        if op == 1:                                                                         # En cas de ser un get hem d'enviar un ack0 per confirmar al servidor que hem rebut correctament les opcions
            ack(0)
        comprobaOACK(TFTP_OPTIONS,TFTP_OAK)                                                 # Fem les comprobacions pertinents en el paquet d'errors
        return True
    else:
        comprobaOACK(TFTP_OPTIONS,TFTP_OAK)                                                 # Fem les comprobacions pertinents en el paquet d'errors
        return False;

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''



# Encarregat de crear, empaquetar i enviar el paquet de DATA
def dades (num_seq, data):
    '''

    Format del paquet de dades:

    2 bytes     2 bytes      n bytes
    ----------------------------------
    | 03   |    num_seq  |   Data     |
    ----------------------------------
    '''


    formatter = '>HH{}s'                                                            # Defineix una reserva 2+2+n bytes
    formatter = formatter.format(len(data))                                         # Definim el tamany de n
    paq = pack(formatter, TFTP_PAQUETS['data'], int(num_seq), data)                 # Empaqueta el paquet de format 2+2+n bytes
    try:
        sent = clientSocket.sendto(paq, serverAddress)                              # Envia el numero de sequencia al servidor
        print("Envia paquet ",num_seq)
    except Exception as e:                                                          # En el cas de que es perdi la conexió
        print("Error de connexió")



# Encarregat de desenpaquetar el paquet DATA i retornar el contingut
def extract_data(data):
    global TFTP_OPTIONS

    formatter = '>HH{}s'                                                            # Defineix una reserva 2+2+n bytes
    formatter = formatter.format(len(data)-4)                                       # Definim el tamany de n
    e_data = unpack(formatter,data)                                                 # Desempaqueta el paquet de format 2+2+n bytes

    if TFTP_OPTIONS['mode'] == 'netascii':

        return e_data[2].decode()                                                   # Retorna el contingut del paquet
    else: #octet
        return bytes(e_data[2])


# Encarregat de desenpaquetar el paquet DATA i retornar el numero de sequencia
def numero_sequencia(data):
    formatter = '>HH{}s'                                                            # Defineix una reserva de 2+2+n bytes
    formatter = formatter.format(len(data)-4)                                       # Definim el tamany de n
    num_seq = unpack(formatter,data)                                                # Desempaqueta el paquet de format 2+2+n bytes
    print("Paquet rebut ", num_seq[1])
    return num_seq[1];                                                              # Retorna el numero de sequencia





# Encarregat de retornar si el paquet indicat es l'ultim o no
def comprobaUltim(data):
    global TFTP_OPTIONS
    if (len(data) < int(TFTP_OPTIONS["blksize"])):                                  # Si el tamany del archius es menor al establert per negociació d'opcions
        return True
    else:
        return False

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

    global serverAddress

    # S'empaqueta en 4 bytes el codi 04 i el numero de sequencia
    formatter = '>HH'                                                               # Defineix una reserva de 2+2 bytes
    paq = pack(formatter, TFTP_PAQUETS['ack'], num_seq)                             # Empaquetem en els bytes necessaris
    try:
        print("Envia ACK ", num_seq)
        sent = clientSocket.sendto(paq, serverAddress)                              # Envia el paquet
    except Exception as e:
                                                                                    # En el cas de que es perdi la conexió
        print("Error de connexió")



# Encarregat de desenpaquetar el paquet ACK i retornar el numero de bloc del ACK
def extract_ack(ack):
    e_ack = unpack('>HH',ack)                                                       # Desempaqueta el paquet de format 2+2 bytes
    print ('ACK rebut ',e_ack[1])
    return e_ack[1]                                                                 # Retorna el numero de bloc del ACK


''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

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
    formatter = '>HH{}sb'                                                          # Defineix una reserva de 2+2+n+1 bytes
    formatter = formatter.format(len(server_error_msg[errorcode]))                 # Definim el tamany de n
    paq = pack(formatter, TFTP_PAQUETS['error'], int(errorcode), bytes(server_error_msg[errorcode], 'utf-8'), 0) # Empaquetem en els bytes necessaris
    print("Error durant la transferència, s'envia un paquet.")

    try:
        sent = clientSocket.sendto(paq, serverAddress)                             # Envia el paquet
    except Exception as e:                                                         # En el cas de que es perdi la conexió
        print("Error de connexió")



# Encarregat de desenpaquetar el paquet d'error i retornar el codi error
def extract_error(paq_error):
    if (len(paq_error) == 4):                                                      # Sense missatge d'error
        formatter = '>HH'
    else:
        formatter = '>HH{}sb'                                                      # Defineix una reserva de 2+2+n+1 bytes
        formatter = formatter.format(len(paq_error)-5)                             # Definim el tamany de n

    e_error = unpack(formatter,paq_error)                                          # Desempaqueta el paquet de format 2+2+n bytes
    return e_error[1]                                                              # Retorna el contingut del paquet


''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

# Encarregat de desenpaquetar el paquet de resposta del servidor i dir si es tracta d'un ACK, un ERROR o un OACK
def extract_msg(msg):
    opcode = int.from_bytes(msg[:2],"big")

    if opcode == 6:     # OACK
        return tractaOpcions(msg, 2)

    elif opcode == 5 :  # ERROR
        formatter = '>HH{}sb'                                                     # Defineix una reserva 2+2+n+1 bytes
        mensaje = unpack(formatter, msg)                                          # Desempaqueta el paquet de format 2+2+n+1 bytes
        print(server_error_msg[mensaje[1]])                                       # Mostra per pantalla el missatge d'error
        return False                                                              # Indica que hi ha hagut un error
    else: # ACK
        comprobaOACK(TFTP_OPTIONS, TFTP_OAK)
        return True




''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

'''                        OPERACIONS GET / PUT                                  '''

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

# Encarregat de realitzar les operacions necessaries donada una petició GET per part del client
def get():

    global serverAddress, TFTP_OPTIONS

    clientSocket.settimeout(int(TFTP_OPTIONS['timeout'])/1000)
    send_request(TFTP_OPTIONS['origen'])                                                    # Envia request al port 69
    data, serverAddress = clientSocket.recvfrom(65507)                                      # Rebem resposta
    esOACK = tractaOpcions(data, 1);

    #Obrim l'archiu....
    mode = 'w'
    if TFTP_OPTIONS['mode'] == 'octet':
        mode += 'b'

    try:
        f = open(TFTP_OPTIONS['desti'],mode)                                                # Obrim l'archiu i deixem el file descriptor a la variable f
    except:
        # En cas, de que l'archiu no existeixi enviem paquet d'error
        paq_error(1)
        raise Exception(server_error_msg[1])

    try:
        fin = False
        print("Rebent dades...")
        while True:
            if(esOACK):
                #En cas de que el primer paquet sigui un oack
                clientSocket.settimeout(int(TFTP_OPTIONS['timeout'])/1000)

                data, serverAddress = clientSocket.recvfrom(65507)                          # Rebem el segment de data
            try:
                esOACK = True
                num_seq = numero_sequencia(data)                                            # Extraiem el numero de sequencia
                try:
                    f.write(extract_data(data))                                             # Escrivim en el archiu
                except Exception as error:
                    # disc ple
                    raise server_error_msg[3]
                ack(num_seq)

                fin = comprobaUltim(data)

            except Exception as error:
                paq_error(5)
                f.close()
                raise Exception(server_error_msg[5])                                         # Terminació prematura
                break;

    except timeout:
        if fin:                                                                              # En cas del que el timeout s'hagi produit perque s'ha transmes tot el fitxer
            print("Ha acabat la transferencia")
        else:
            paq_error(5)                                                                     # En cas de que no s'hagi rebut cap resposta per el servidor
            f.close()
            raise Exception(server_error_msg[5])                                             # Durant la transmissio

    f.close()                                                                                # Tanquem el archiu

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

# Operació PUT

def put():
    global serverAddress
    #WRQ al servidor...
    clientSocket.settimeout(5)
    send_request(TFTP_OPTIONS['desti'])
    try:                                                      # Envia request al port 69
        msg, serverAddress = clientSocket.recvfrom(65507)                                        # Espera resposta

        validRequest = extract_msg(msg)                                                          # Mirem si es tracta d'un OACK, ACK o Error


        if validRequest:                                                                     # En cas que no sigui un error
            print("Enviant dades...")
            # Obrim el fitxer....
            try:
                if TFTP_OPTIONS['mode'] == 'netascii':
                    fd = open(TFTP_OPTIONS['origen'],'r')                                    # Obrim l'archiu i deixem el file descriptor a la variable f
                else:
                    fd = open(TFTP_OPTIONS['origen'],'rb')
            except:
                # En cas, de que l'archiu no existeixi enviem paquet d'error
                paq_error(1)
                raise Exception(server_error_msg[1])                                         # Obrim l'archiu i deixem el file descriptor a la variable f

            num_seq = 1
            data = fd.read(int(TFTP_OPTIONS['blksize']))                                     # Llegim del fitxer
            vegades = 3                                                                      # Numero de cops que intentará reenviar un paquet
            tamany_ultim = 0                                                                 # Ens indicara el tamany del utlim paquet

            # En cas de que el fitxer estigui buit enviem nomes un paquet amb la capçelera
            if not data:
                dades(num_seq,bytes("", 'utf-8'))
                ack, serverAddress = clientSocket.recvfrom(65507)

            # En cas de que hi hagi informació en el fitxer comencem la transmissió
            while(data):
                clientSocket.settimeout(int(TFTP_OPTIONS['timeout'])/1000)                  # Inicia timeout
                try:
                    if TFTP_OPTIONS['mode'] == 'netascii':                                  # en netascii
                        dades(num_seq, bytes(data,encoding='utf8'))
                    else:
                        dades(num_seq, data)                                                # en octet

                    tamany_ultim = len(data);
                    ack, serverAddress = clientSocket.recvfrom(65507)                       # Espera ack

                    opcode = int.from_bytes(ack[:2], "big")
                    if(opcode == 4):                                                        # Comproba si rebem un ACK o un ERROR
                        reconeixement = extract_ack(ack)                                    # Extraiem el ack
                        vegades = 3
                        if reconeixement == num_seq:                                        # En cas de que coincideixi amb el numero de sequencia
                            data = fd.read(int(TFTP_OPTIONS['blksize']))                    # Llegim més informació
                            # Contador ciclic
                            if num_seq == 65535:
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
                    dades(num_seq,bytes("", 'utf-8'))                                     # Enviem paquet buit per tancar la conexió
                    ack, serverAddress = clientSocket.recvfrom(65507)                     # Espera ack
                    reconeixement  = extract_ack(ack)

                print("S'ha acabat la transferencia...")
    except timeout:                                                                       # Acaba la transferencia
        print("S'ha acabat la transferencia...")



''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

# Encarregat de tractar el arguments que s'indiquen al llançar el programa
def tracta_arguments(arglist):
    global serverAddress, TFTP_OPTIONS

    # S'han de determinar totes les opcions per realitzar la transfrencia
    if len(arglist) != 8:
        print("Numero d'arguments invalids")
    else:
        if str(arglist[1]) == "octet" or str(arglist[1]) == "netascii":
            TFTP_OPTIONS['mode'] = str(arglist[1])

        TFTP_OPTIONS['host'] = str(arglist[2])
        if str(arglist[3]) == 'GET' or str(arglist[3]) == 'get':
            TFTP_OPTIONS['op'] = 1
        elif str(arglist[3]) == 'PUT' or str(arglist[3]) == 'put':
            TFTP_OPTIONS['op'] = 2
        else:
            #Operacio TFTP Ilegal
            raise Exception(server_error_msg[4])

        TFTP_OPTIONS['origen'] = str(arglist[4])
        TFTP_OPTIONS['desti'] = str(arglist[5])
        TFTP_OPTIONS['blksize'] = int(arglist[6])
        TFTP_OPTIONS['timeout'] = int(arglist[7])

        #El timeout no pot ser 0
        if (int(arglist[7]) <= 0):
            TFTP_OPTIONS['timeout'] = 3000

    #Adreça del Servidor
    serverName = TFTP_OPTIONS['host']
    serverAddress = (serverName,serverPort)




''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

'''                                 MAIN                                         '''

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

# Encarregat de mostrar el menu
def menu():
    #ASCCI ART

    print("\n\n\n =================================== TFTP CLIENT =====================================\n\n\n")


    print("Transfereix els fitxers a i desde un equip remot amb el servei TFTP en funcionament.\n")
    print("TFTP mode host [GET|PUT] origen desti blksize [timeout]\n")

    print("OPCIONS")
    print("---------\n")
    print("mode     Especifica el mode de transferencia. Utilitza aquest mode per transferir archius binaris ")
    print("host     Especifica la ip del servidor (per defecte sera local) ")
    print("GET       Transfereix el archiu desti en el host remot al archiu origen en el host local")
    print("PUT       Transfereix el archiu origen en el host local al archiu desti en el host remot ")
    print("origen    Epecifica el archiu a transferir")
    print("desti     Especificia on transferir el archiu")
    print("blksize   Especifica el tamany del segment")
    print("timeout   Especifica el temps d'espera")
    print("\n\n")



def main():

    # Capturem els valors de la linea de comandes
    arglist = sys.argv

    # En cas de que no s'hagi posat cap opció treiem el menu d'opcions per pantalla
    if len(arglist) < 2:
        menu()
    else:
        tracta_arguments(arglist)


    #GET
    if TFTP_OPTIONS['op'] == 1:
        get()
    #PUT
    elif TFTP_OPTIONS['op'] == 2:
        put()

    clientSocket.close()


if __name__ == '__main__':
    main()

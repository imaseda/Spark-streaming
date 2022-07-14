import json
from random import sample
import socket
import time
import sys
#import datetime;

from opensky_api import OpenSkyApi
api = OpenSkyApi()


# Creamos un socket TCP/IP
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind del socket al puerto y localhost
server_address = ('localhost', 20033)
print('starting up on {} port {}'.format(*server_address))
sock.bind(server_address)

# Listen para conexiones entrantes
sock.listen(1)

# Esperamos a la conexión
print('waiting for a connection')
connection, client_address = sock.accept()
# Añado un lapso de tiempo para no acumular los primeros registros
print('established connection')
time.sleep(4)

while True:
    
    states = api.get_states(bbox=(36.173357, 44.024422,-10.137019, 1.736138))
    if states:
        for s in states.states:
            vuelo_dict = {
                'callsign':s.callsign,
                'country': s.origin_country,
                'longitude': s.longitude,
                'latitude': s.latitude,
                'velocity': s.velocity,
                'vertical_rate': s.vertical_rate,
            }
            vuelo_encode_data = json.dumps(vuelo_dict).encode('utf-8')+ ("\n").encode('utf-8')
            #print(vuelo_encode_data)
            connection.send(vuelo_encode_data)
    #ct = datetime.datetime.now()
    #print("current time:-", ct)
    
    time.sleep(10)
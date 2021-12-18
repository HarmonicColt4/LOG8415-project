import time
import mysql.connector
import random
import asyncio
import pickle
from pythonping import ping

HOST = ''
PORT = 5001

master_ip = '10.84.15.10'
slave_ips = ['10.84.15.11', '10.84.15.12']

mode = 'direct hit'

# MySQL - open connections and slaves
while True:
    try:
        master_connection = mysql.connector.connect(user='proxy', password='password', host=master_ip, database='project', connection_timeout=60)
        break
    except mysql.connector.Error as err:
        pass

slave_connections = []

for slave_ip in slave_ips:
    while True:
        try:
            slave_connections.append(mysql.connector.connect(user='proxy', password='password', host=slave_ip, database='project', connection_timeout=60))
            break
        except mysql.connector.Error as err:
            pass

connections = slave_connections + [master_connection]

def parse_request(request):
    obj = pickle.loads(request)
    type = obj['type']
    statement = obj['statement']

    return type, statement

def change_mode(new_mode):
    global mode
    if new_mode == 'direct hit':
        mode = 'direct hit'
        return 'Proxy mode changed to \'direct hit\''
    if new_mode == 'random':
        mode = 'random'
        return 'Proxy mode changed to \'random\''
    if new_mode == 'ping':
        mode = 'ping'
        return 'Proxy mode changed to \'ping\''

def process_request(request):
    type, statement = parse_request(request)

    if type == 'insert':
        with master_connection.cursor() as cursor:
            cursor.execute(statement)
            master_connection.commit()
        
        response = 'Data was successfully inserted'

    if type == 'select':
        connection = select_connection()
        response = process_select(connection, statement)

    if type == 'delete':
        with master_connection.cursor() as cursor:
            cursor.execute(statement)
            master_connection.commit()

        response = 'Table was successfully cleared'

    if type == 'mode':
        response = change_mode(statement)

    if type == 'other':
        if statement == 'print':
            response = f'Current proxy configuration: {mode}'
        else:
            response = f'Request not recognized'

    return response

def select_connection():
    if mode == 'direct hit':
        return master_connection
    if mode == 'random':
        return random.choice(connections)
    if mode == 'ping':
        responses = {}

        for con in connections:
            response = ping(con.server_host)
            responses[con.server_host]=response.rtt_avg

        fastest_host = min(responses, key=responses.get)

        con = list(filter(lambda connection: connection.server_host == fastest_host, connections))[0]
        return con

    return master_connection

def process_select(connection, statement):
    with connection.cursor() as cursor:
        cursor.execute(statement)
        result = cursor.fetchall()
        response = ' '.join([str(r) for r in result])
        response = f'{response} Request performed by {connection.server_host}'

    return response

async def handle_requests(reader, writer):
    while True:
        request = await reader.read(1024)

        if not request:
            break

        response = process_request(request)

        request = response.encode()
        writer.write(request)
        await writer.drain()

    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(
        handle_requests, '', PORT)

    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')

    async with server:
        await server.serve_forever()

time.sleep(300)

asyncio.run(main())
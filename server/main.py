import mysql.connector
import random
import asyncio
from pythonping import ping

# TODO use boto3 to get ip addresses of nodes
# TODO Proxy - direct hit (master read and write)
# TODO Proxy - random selection (master write and read from all nodes)
# TODO Proxy - custom (master write and read from shortest ping node)
# TODO Socket

HOST = ''
PORT = 5001

MASTER_IP = '18.215.35.148'
node_ips = [MASTER_IP, '3.219.0.192', '54.209.67.21', '54.221.209.119']
mode = 'direct hit'

# MySQL - open connections and slaves
master_connection = mysql.connector.connect(user='test', password='password', host=MASTER_IP)

slave_connections = [mysql.connector.connect(user='test', password='password',
                              host=slave_ip) for slave_ip in node_ips if slave_ip != MASTER_IP]

connections = slave_connections + [master_connection]

def process_request(request):
    global mode
    match request:
        case 'read':
            connection = select_connection()
            read_operation(connection)
            return 'Read operation completed'

        case 'direct hit':
            mode = 'direct hit'
            return 'Proxy mode changed to \'direct hit\''
        case 'random':
            mode = 'random'
            return 'Proxy mode changed to \'random\''
        case 'ping':
            mode = 'ping'
            return 'Proxy mode changed to \'ping\''

        case 'print':
            return mode

        case _:
            return 'Request not recognized'

def select_connection():
    match mode:
        case 'direct hit':
            return master_connection
        case 'random':
            return random.choice(connections)
        case 'ping':
            responses = {}

            for con in connections:
                response = ping(con.server_host)
                responses[con.server_host]=response.rtt_avg

            fastest_host = min(responses, key=responses.get)

            con = list(filter(lambda connection: connection.server_host == fastest_host, connections))[0]
            return con

    return master_connection

def read_operation(connection):
    select_query = "SELECT user FROM mysql.user"
    with connection.cursor() as cursor:
        cursor.execute(select_query)
        result = cursor.fetchall()
        for row in result:
            print(row)

async def handle_requests(reader, writer):
    while True:
        data = await reader.read(1024)
        request = data.decode()

        response = process_request(request)

        data = response.encode()
        writer.write(data)
        await writer.drain()

async def main():
    server = await asyncio.start_server(
        handle_requests, '', PORT)

    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')

    async with server:
        await server.serve_forever()

asyncio.run(main())
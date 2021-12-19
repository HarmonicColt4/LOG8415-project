import asyncio
import pickle
import re

HOST = ''
PORT = 5002

TRUSTED_HOST = '10.84.15.20'
TRUSTED_HOST_PORT = 5001

proxy_reader = None
proxy_writer = None

selectValidator = re.compile(r"(^select \* from people where seq = \d{1,};$)")
insertValidator = re.compile(r"(^insert into people values \(\s*\d{1,}\s*,\s*'\w+[\w|\s]*'\s*,\s*'\w+[\w|\s]*'\s*,\s*\d{1,}\s*,\s*'\w+[\w|\s]*'\s*,\s*'[\(]?\d{3}[\)]?[-|\s]?\d{3}[-|\s]?\d{4}'\s*,\s*'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}'\s*,\s*'\w+[\w|\s]*'\s*,\s*'\d{1,2}\/\d{1,2}\/\d{4}'\s*,\s*'\w+[\w|\s]*'\s*\);$)")

def is_valid(request):
    obj = pickle.loads(request)
    type = obj['type']
    statement = obj['statement']

    if type not in ['select', 'insert', 'delete', 'mode']:
        return False

    statement = statement.lower()
    
    if statement.startswith('insert '):
        return bool(insertValidator.match(statement))
    if statement.startswith('select '):
        return bool(selectValidator.match(statement))
    return statement.startswith('delete ') or statement in ['direct hit', 'random', 'ping']

async def process_request(request):
    if is_valid(request):
        proxy_writer.write(request)
        await proxy_writer.drain()

        response = await proxy_reader.read(1024)

    else:
        response = b'Invalid request'
    
    return response

async def handle_requests(reader, writer):
    while True:
        request = await reader.read(1024)

        if not request:
            break

        response = await process_request(request)

        writer.write(response)
        await writer.drain()

    writer.close()
    await writer.wait_closed()

async def tcp_client():
    global proxy_reader, proxy_writer
    while True:
        try:
            print('Wait for proxy server to become available...', end=' ')

            proxy_reader, proxy_writer = await asyncio.open_connection(TRUSTED_HOST, TRUSTED_HOST_PORT)
            
            print('Connected!')
            break
        except ConnectionRefusedError:
            print('Trying again in 15 seconds...')
            await asyncio.sleep(15)
            pass

    server = await asyncio.start_server(
        handle_requests, HOST, PORT)

    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')

    async with server:
        await server.serve_forever()

asyncio.run(tcp_client())
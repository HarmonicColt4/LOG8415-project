import asyncio
import pickle
import time

HOST = ''
PORT = 5002

TRUSTED_HOST = '10.84.15.20'
TRUSTED_HOST_PORT = 5001

proxy_reader = None
proxy_writer = None

async def process_request(request):
    proxy_writer.write(request)
    await proxy_writer.drain()

    response = await proxy_reader.read(1024)
    
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
        handle_requests, '', PORT)

    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')

    async with server:
        await server.serve_forever()

time.sleep(150)

asyncio.run(tcp_client())
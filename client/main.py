import asyncio

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 5001        # The port used by the server

async def tcp_client():
    reader, writer = await asyncio.open_connection(HOST, PORT)

    user_input = input('Send: ')

    while user_input != 'stop':
        writer.write(user_input.encode())
        await writer.drain()

        data = await reader.read(1024)
        print(f'Received: {data.decode()!r}')

        user_input = input('Send: ')

    print('Close the connection')
    writer.close()
    await writer.wait_closed()

asyncio.run(tcp_client())
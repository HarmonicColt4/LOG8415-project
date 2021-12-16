import asyncio
import boto3

client = boto3.client('ec2')

response = client.describe_instances( Filters=[
        {
            'Name': 'tag:Name',
            'Values': [
                'proxy'
            ]
        }
    ])

proxy_ip = [i['PublicIpAddress'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'running'][0]

HOST = proxy_ip  # The server's hostname or IP address
PORT = 5001        # The port used by the server

async def tcp_client():

    while True:
        try:
            print('Wait for proxy server to become available...', end=' ')

            reader, writer = await asyncio.open_connection(HOST, PORT)
            
            print('Connected to proxy!')
            break
        except ConnectionRefusedError:
            print('Trying again in 15 seconds...')
            await asyncio.sleep(15)
            pass

    user_input = input('Send: ')

    while user_input != '':
        writer.write(user_input.encode())
        await writer.drain()

        data = await reader.read(1024)
        print(f'Received: {data.decode()!r}')

        user_input = input('Send: ')

    print('Close the connection')
    writer.close()
    await writer.wait_closed()

asyncio.run(tcp_client())
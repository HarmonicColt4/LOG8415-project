import asyncio
import boto3
import pickle
import multiprocessing

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

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 5001        # The port used by the server

mode = 'direct hit'

async def run_insert_person(reader, writer, person):
    seq, first, last, age, city, phone, email, street, birthday, gender = person.split(',')
    statement = f'INSERT INTO people VALUES ({seq}, \'{first}\', \'{last}\', {age}, \'{city}\', \'{phone}\', \'{email}\', \'{street}\', \'{birthday}\', \'{gender}\');'
    
    obj = {'type': 'insert', 'statement': statement}
    pickledobj = pickle.dumps(obj)
    writer.write(pickledobj)
    await writer.drain()

    # confirm insertion
    data = await reader.read(1024)
    print(f'Received: {data.decode()!r}')

async def run_read_person(reader, writer, person):
    seq = person.split(',')[0]
    statement = f'SELECT * FROM people WHERE seq = {seq};'
    
    obj = {'type': 'select', 'statement': statement}
    pickledobj = pickle.dumps(obj)
    writer.write(pickledobj)
    await writer.drain()

    # confirm insertion
    data = await reader.read(1024)
    print(f'Received: {data.decode()!r}')

async def tcp_client():

    while True:
        try:
            print('Wait for proxy server to become available...', end=' ')

            reader, writer = await asyncio.open_connection(HOST, PORT)
            
            print('Connected!')
            break
        except ConnectionRefusedError:
            print('Trying again in 15 seconds...')
            await asyncio.sleep(15)
            pass

    # read data file
    with open('people.csv', 'r') as f:
        people = f.readlines()

    user_input = input('Send: ')

    while user_input != '':

        if user_input == 'insert':
            # insert data to db
            for person in people:
                await run_insert_person(reader, writer, person)

        elif user_input == 'select':
            # retrieve data from db
            for person in people:
                await run_read_person(reader, writer, person)

        else:
            obj = {'type': 'other', 'statement': user_input}
            pickledobj = pickle.dumps(obj)

            writer.write(pickledobj)
            await writer.drain()

            data = await reader.read(1024)
            print(f'Received: {data.decode()!r}')

        user_input = input('Send: ')

    print('Close the connection')
    writer.close()
    await writer.wait_closed()

asyncio.run(tcp_client())
import asyncio
import boto3
import pickle
import time
import multiprocessing

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

async def change_mode(reader, writer, mode):
    obj = {'type': 'mode', 'statement': mode}
    pickledobj = pickle.dumps(obj)

    writer.write(pickledobj)
    await writer.drain()

    # confirm insertion
    data = await reader.read(1024)
    print(f'Received: {data.decode()!r}')

async def clear_table(reader, writer):
    statement = 'DELETE FROM people'
    obj = {'type': 'delete', 'statement': statement}
    pickledobj = pickle.dumps(obj)

    writer.write(pickledobj)
    await writer.drain()

    # confirm insertion
    data = await reader.read(1024)
    print(f'Received: {data.decode()!r}')

async def tcp_client(HOST, PORT):
    while True:
        try:
            print('Wait for server to become available...', end=' ')

            reader, writer = await asyncio.open_connection(HOST, PORT)
            
            print('Connected!')
            break
        except ConnectionRefusedError:
            print('Trying again in 15 seconds...')
            await asyncio.sleep(15)
            pass

    print('Clearing table')
    time.sleep(3)

    # clear table
    await clear_table(reader, writer)
    time.sleep(3)

    # read data file
    with open('people.csv', 'r') as f:
        people = f.readlines()

    print('Loading data')
    time.sleep(3)

    # insert data to db
    for person in people:
        await run_insert_person(reader, writer, person)

    # delay 20s
    time.sleep(20)

    print('Performing select statements')
    time.sleep(3)

    # retrieve data from db
    for mode in ['direct hit', 'random', 'ping']:
        await change_mode(reader, writer, mode)
        
        # delay 20s
        time.sleep(20)

        for person in people:
            await run_read_person(reader, writer, person)

    print('Clearing table')
    time.sleep(3)

    # clear table
    await clear_table(reader, writer)

    print('Close the connection')
    writer.close()
    await writer.wait_closed()

def main(server, port):
    client = boto3.client('ec2')
    
    response = client.describe_instances( Filters=[
            {
                'Name': 'tag:Name',
                'Values': [
                    server
                ]
            }
        ])

    server_ip = [i['PublicIpAddress'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'running'][0]

    HOST = server_ip    # The server's hostname or IP address
    PORT = port        # The port used by the server

    asyncio.run(tcp_client(HOST, PORT))

if __name__ == "__main__":
    import sys
    main(sys.argv[1], int(sys.argv[2]))
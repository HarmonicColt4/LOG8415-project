import client
import mysql_ec2_helper
import boto3
import os
import time
from fabric import Connection

def find_instance_ip(name_tag):
    client = boto3.client('ec2')

    response = client.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [name_tag]
            }
        ]
    )

    ip = [i['PublicIpAddress'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'running']
    
    return ip


if not os.path.exists('results'):
    os.makedirs('results')

mysql_ec2_helper.deploy_standalone()
mysql_ec2_helper.deploy_cluster()
mysql_ec2_helper.deploy_proxy()

print("Waiting for instances to initialize and complete sysbench run")

time.sleep(300)

standalone_ip = find_instance_ip('standalone')[0]
print("Getting results from standalone instance")
with Connection(standalone_ip, user='ubuntu', connect_kwargs={'key_filename': 'mysql.pem'}) as c:
    c.get('/tmp/benchmark_standalone.txt', local='results/benchmark_standalone.txt')

print("Terminating standalone instance")
mysql_ec2_helper.terminate_instance('standalone')

print("Deploying gatekeeper instance")
mysql_ec2_helper.deploy_gatekeeper()

print("Launching client")
time.sleep(3)
client.main('proxy', 5001)

master_ip = find_instance_ip('master')[0]
slave_1_ip = find_instance_ip('slave')[0]
slave_2_ip = find_instance_ip('slave')[1]
proxy_ip = find_instance_ip('proxy')[0]

print("Getting results from instances")
with Connection(master_ip, user='ubuntu', connect_kwargs={'key_filename': 'mysql.pem'}) as c:
    c.get('/home/ubuntu/benchmark_replication.txt', local='results/benchmark_replication.txt')
    c.get('/home/ubuntu/powerapi_master.txt', local='results/powerapi_master_1.txt')

with Connection(slave_1_ip, user='ubuntu', connect_kwargs={'key_filename': 'mysql.pem'}) as c:
    c.get('/home/ubuntu/powerapi_slave1.txt', local='results/powerapi_slave1_1.txt')

with Connection(slave_2_ip, user='ubuntu', connect_kwargs={'key_filename': 'mysql.pem'}) as c:
    c.get('/home/ubuntu/powerapi_slave2_.txt', local='results/powerapi_slave2_1.txt')

with Connection(proxy_ip, user='ubuntu', connect_kwargs={'key_filename': 'mysql.pem'}) as c:
    c.get('/home/ubuntu/powerapi_proxy_.txt', local='results/powerapi_proxy_1.txt')

print("Adjusting security group rules for gatekeeper cloud pattern and reboot instances")
mysql_ec2_helper.adjust_security_group_rules_with_gatekeeper()

print('Reboot cluster')
mysql_ec2_helper.reboot_instance(['master', 'slave'])
time.sleep(5)

print('Reboot proxy')
mysql_ec2_helper.reboot_instance(['proxy'])
time.sleep(5)

print('Reboot gatekeeper')
mysql_ec2_helper.reboot_instance(['gatekeeper'])
time.sleep(60)

client.main('gatekeeper', 5002)

gatekeeper_ip = find_instance_ip('gatekeeper')[0]

print("Getting results from instances")
with Connection(master_ip, user='ubuntu', connect_kwargs={'key_filename': 'mysql.pem'}) as c:
    c.get('/home/ubuntu/powerapi_master.txt', local='results/powerapi_master_2.txt')

with Connection(slave_1_ip, user='ubuntu', connect_kwargs={'key_filename': 'mysql.pem'}) as c:
    c.get('/home/ubuntu/powerapi_slave1.txt', local='results/powerapi_slave1_2.txt')

with Connection(slave_2_ip, user='ubuntu', connect_kwargs={'key_filename': 'mysql.pem'}) as c:
    c.get('/home/ubuntu/powerapi_slave2.txt', local='results/powerapi_slave2_2.txt')

with Connection(proxy_ip, user='ubuntu', connect_kwargs={'key_filename': 'mysql.pem'}) as c:
    c.get('/home/ubuntu/powerapi_proxy.txt', local='results/powerapi_proxy_2.txt')

with Connection(gatekeeper_ip, user='ubuntu', connect_kwargs={'key_filename': 'mysql.pem'}) as c:
    c.get('/home/ubuntu/powerapi_gatekeeper.txt', local='results/powerapi_gatekeeper.txt')

mysql_ec2_helper.stop_all_instances()
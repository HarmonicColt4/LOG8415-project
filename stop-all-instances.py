import boto3

ec2 = boto3.client('ec2')

# get instances
response = ec2.describe_instances(
    Filters=[
        {
            'Name': 'tag:Name',
            'Values': [
                'master', 'slave', 'proxy', 'gatekeeper'
            ]
        }
    ]
)

instances_ids = [i['InstanceId'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'running']

if len(instances_ids) > 0:
    ec2.stop_instances(InstanceIds=instances_ids)
    print('Stopping instances')

else:
    print('Instances already stopped')
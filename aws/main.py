import boto3

ec2 = boto3.client('ec2')

# find master and slaves' id using 'Name' tag
response = ec2.describe_instances(
    Filters=[
        {
            'Name': 'tag:Name',
            'Values': [
                'master', 'slave'
            ]
        },
    ]
)

instance_ids = [i['InstanceId'] for r in response['Reservations']
                    for i in r['Instances']]

def start_cluster():
    ec2.start_instances(InstanceIds=instance_ids)

def stop_cluster():
    ec2.stop_instances(InstanceIds=instance_ids)

stop_cluster()
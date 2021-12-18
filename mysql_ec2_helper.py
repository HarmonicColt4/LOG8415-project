import boto3

client = boto3.client('ec2')
ec2 = boto3.resource('ec2')

def find_instances(name_tags):
    return client.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': name_tags
            }
        ]
    )

def launch_instance(user_data_filepath, type, private_ip, name_tag):
    subnet_id, sg_id = get_subnet_sg_ids()

    user_data = ''

    with open(user_data_filepath, 'r') as reader:
        user_data = reader.read()
    
    client.run_instances(
        ImageId='ami-04505e74c0741db8d',
        InstanceType=type,
        KeyName='mysql',
        MaxCount=1,
        MinCount=1,
        SecurityGroupIds=[
            sg_id,
        ],
        SubnetId=subnet_id,
        UserData=user_data,
        PrivateIpAddress=private_ip,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': name_tag,
                    },
                ],
            },
        ],
    )

def deploy_standalone():
    response = find_instances(['standalone'])

    # if instance is not created, launch instance
    terminated = [i['InstanceId'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'terminated']

    if len(terminated) == len(response['Reservations']):
        print('Creating standalone')

        launch_instance('setup.txt', 't2.micro', '10.84.15.100', 'standalone')

    else:
    # start proxy instance if it's stopped

        # get instance ids
        instances_id = [i['InstanceId'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'stopped']

        if len(instances_id) > 0:
            print('Starting standalone')
            client.start_instances(InstanceIds=instances_id)

        else:
            print('Standalone already running')

def deploy_cluster():
    # get instances
    response = find_instances(['master', 'proxy'])

    # if cluster instances are terminated and not created, launch instances
    terminated = [i['InstanceId'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'terminated']

    if len(terminated) == len(response['Reservations']):
        print('Creating cluster')
        create_cluster_instances()

    else:
    # start cluster instances if they are stopped

        # get instance ids
        instances_ids = [i['InstanceId'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'stopped']

        if len(instances_ids) > 0:
            client.start_instances(InstanceIds=instances_ids)
            print('Starting cluster')

        else:
            print('Cluster already running')

def deploy_proxy():
    response = find_instances(['proxy'])

    # if proxy instance is not created, launch instance
    terminated = [i['InstanceId'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'terminated']

    if len(terminated) == len(response['Reservations']):
        print('Creating proxy')

        launch_instance('proxy/setup.txt', 't2.large', '10.84.15.20', 'proxy')

    else:
    # start proxy instance if it's stopped

        # get instance ids
        instances_id = [i['InstanceId'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'stopped']

        if len(instances_id) > 0:
            print('Starting proxy')
            client.start_instances(InstanceIds=instances_id)

        else:
            print('Proxy already running')

def deploy_gatekeeper():
    response = find_instances(['gatekeeper'])

    # if gatekeeper instance is not created, launch instance
    terminated = [i['InstanceId'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'terminated']

    if len(terminated) == len(response['Reservations']):
        print('Creating gatekeeper')

        launch_instance('gatekeeper/setup.txt', 't2.large', '10.84.15.21', 'gatekeeper')
    else:
    # start gatekeeper instance if it's stopped

        # get instance ids
        instances_id = [i['InstanceId'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'stopped']

        if len(instances_id) > 0:
            print('Starting gatekeeper')
            client.start_instances(InstanceIds=instances_id)

        else:
            print('gatekeeper already running')

def adjust_security_group_rules_with_gatekeeper():
    response = client.describe_security_groups(
    Filters=[
        {
            'Name': 'group-name',
            'Values': [
                'gatekeeper'
            ]
        },
    ])

    if len(response['SecurityGroups']) == 0:
        
        # get mysql vpc id
        response = client.describe_vpcs(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [
                    'mysql',
                ]
            },
        ])

        vpc_id = response['Vpcs'][0]['VpcId']

        # create security group for gatekeeper
        response = client.create_security_group(
            Description='gatekeeper',
            GroupName='gatekeeper',
            VpcId=vpc_id
        )

        # get new security group's id
        sg_id = response['GroupId']

        security_group = ec2.SecurityGroup(sg_id)
        security_group.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=22, ToPort=22)
        security_group.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=5002, ToPort=5002)

    else:
        sg_id = response['SecurityGroups'][0]['GroupId']

    # get gatekeeper instance
    response = find_instances(['gatekeeper'])

    # get running instance ids 
    instances_ids = [i['InstanceId'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'running']
    
    # change security group for gatekeeper
    for id in instances_ids:
        response = client.modify_instance_attribute(InstanceId=id, Groups=[sg_id])

    # modify cluster security group rules
    response = client.describe_security_groups(
    Filters=[
        {
            'Name': 'group-name',
            'Values': [
                'mysql'
            ]
        },
    ])

    sg_id = response['SecurityGroups'][0]['GroupId']

    security_group = ec2.SecurityGroup(sg_id)

    # remove existing rules
    response = client.describe_security_group_rules(
    Filters=[
            {
                'Name': 'group-id',
                'Values': [
                    sg_id
                ]
            },
        ]
    )

    sgr_ids = [sgr['SecurityGroupRuleId'] for sgr in response['SecurityGroupRules'] if not sgr['IsEgress']]
    security_group.revoke_ingress(SecurityGroupRuleIds=sgr_ids)

    sgr_ids = [sgr['SecurityGroupRuleId'] for sgr in response['SecurityGroupRules'] if sgr['IsEgress']]
    security_group.revoke_egress(SecurityGroupRuleIds=sgr_ids)

    # add new rules
    security_group.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=22, ToPort=22)
    security_group.authorize_ingress(CidrIp='10.84.15.21/32', IpProtocol='tcp', FromPort=5001, ToPort=5001)
    security_group.authorize_ingress(CidrIp='10.84.15.10/32', IpProtocol='tcp', FromPort=3306, ToPort=3306)
    security_group.authorize_ingress(CidrIp='10.84.15.11/32', IpProtocol='tcp', FromPort=3306, ToPort=3306)
    security_group.authorize_ingress(CidrIp='10.84.15.12/32', IpProtocol='tcp', FromPort=3306, ToPort=3306)
    security_group.authorize_ingress(CidrIp='10.84.15.20/32', IpProtocol='icmp', FromPort=8, ToPort=-1)
    security_group.authorize_egress(IpPermissions=[
        {
            'FromPort': 5001,
            'IpProtocol': 'tcp',
            'IpRanges': [
                {
                    'CidrIp': '10.84.15.21/32',
                    'Description': 'gatekeeper'
                },
            ],
            'ToPort': 5001
        },
    ])
    security_group.authorize_egress(IpPermissions=[
        {
            'FromPort': 3306,
            'IpProtocol': 'tcp',
            'IpRanges': [
                {
                    'CidrIp': '10.84.15.10/32',
                    'Description': 'mysql'
                },
            ],
            'ToPort': 3306
        },
    ])
    security_group.authorize_egress(IpPermissions=[
        {
            'FromPort': 3306,
            'IpProtocol': 'tcp',
            'IpRanges': [
                {
                    'CidrIp': '10.84.15.11/32',
                    'Description': 'mysql'
                },
            ],
            'ToPort': 3306
        },
    ])
    security_group.authorize_egress(IpPermissions=[
        {
            'FromPort': 3306,
            'IpProtocol': 'tcp',
            'IpRanges': [
                {
                    'CidrIp': '10.84.15.12/32',
                    'Description': 'mysql'
                },
            ],
            'ToPort': 3306
        },
    ])

def create_cluster_instances():

    launch_instance('cluster-user-data/master.txt', 't2.micro', '10.84.15.10', 'master')

    for i in range(1,3):
        launch_instance(f'cluster-user-data/slave{i}.txt', 't2.micro', f'10.84.15.1{i}', 'slave')

def create_vpc():
    vpc = ec2.create_vpc(CidrBlock='10.84.0.0/16')

    # assign a name to our VPC
    vpc.create_tags(Tags=[{"Key": "Name", "Value": "mysql"}])
    vpc.wait_until_available()

    # enable public dns hostname
    client.modify_vpc_attribute( VpcId = vpc.id , EnableDnsSupport = { 'Value': True } )
    client.modify_vpc_attribute( VpcId = vpc.id , EnableDnsHostnames = { 'Value': True } )

    # create an internet gateway and attach it to VPC
    internetgateway = ec2.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=internetgateway.id)

    # create a route table and a public route
    routetable = vpc.create_route_table()
    route = routetable.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=internetgateway.id)

    # create subnet and associate it with route table
    subnet = ec2.create_subnet(CidrBlock='10.84.15.0/24', VpcId=vpc.id)
    client.modify_subnet_attribute(
        SubnetId=subnet.id,
        MapPublicIpOnLaunch={
            'Value': True
        },
    )
    routetable.associate_with_subnet(SubnetId=subnet.id)

    # create keypair if it doesn't exist
    response = client.describe_key_pairs(Filters=[
        {
            'Name': 'key-name',
            'Values': [
                'mysql',
            ]
        },
    ])

    if len(response['KeyPairs']) == 0:
        response = client.create_key_pair(KeyName='mysql', KeyType='ed25519')

        # create private key file
        with open('mysql.pem', 'w') as writer:
            writer.write(response['KeyMaterial'])

    return vpc

def create_security_group(vpc_id):
    securitygroup = ec2.create_security_group(GroupName='mysql', Description='allow ssh mysql ping and tcp traffic', VpcId=vpc_id)
    securitygroup.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=22, ToPort=22)
    securitygroup.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=5001, ToPort=5001)
    securitygroup.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=3306, ToPort=3306)
    securitygroup.authorize_ingress(CidrIp='0.0.0.0/0', IpProtocol='icmp', FromPort=8, ToPort=-1)

    return securitygroup

def get_subnet_sg_ids():
    subnet_id = ''
    sg_id = ''

    response = client.describe_vpcs(
    Filters=[
        {
            'Name': 'tag:Name',
            'Values': [
                'mysql'
            ]
        }
    ])


    if len(response['Vpcs']) == 0:
        vpc = create_vpc()

        subnet = list(vpc.subnets.all())[0]

        subnet_id = subnet.id

    else:
        vpc_id = response['Vpcs'][0]['VpcId']

        response = client.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id
                ]
            }
        ])

        subnet_id = response['Subnets'][0]['SubnetId']

    response = client.describe_security_groups(
    Filters=[
        {
            'Name': 'group-name',
            'Values': [
                'mysql'
            ]
        },
    ])

    if len(response['SecurityGroups']) == 0:
        security_group = create_security_group(vpc.id)

        sg_id = security_group.group_id

    else:
        sg_id = response['SecurityGroups'][0]['GroupId']

    return subnet_id, sg_id
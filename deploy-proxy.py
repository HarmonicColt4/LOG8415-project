import boto3

ec2 = boto3.client('ec2')

def deploy_cluster():
    # get instances
    response = ec2.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [
                    'master', 'slave'
                ]
            }
        ]
    )

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
            ec2.start_instances(InstanceIds=instances_ids)
            print('Starting cluster')

        else:
            print('Cluster already running')

def deploy_proxy():
    response = ec2.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [
                    'proxy'
                ]
            }
        ]
    )

    # if proxy instance is not created, launch instance
    terminated = [i['InstanceId'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'terminated']

    if len(terminated) == len(response['Reservations']):
        print('Creating proxy')

        subnet_id, sg_id = get_subnet_sg_ids()

        user_data = ''
    
        with open('proxy/setup.txt', 'r') as reader:
            user_data = reader.read()
        
        ec2.run_instances(
            ImageId='ami-04505e74c0741db8d',
            InstanceType='t2.large',
            KeyName='mysql',
            MaxCount=1,
            MinCount=1,
            SecurityGroupIds=[
                sg_id,
            ],
            SubnetId=subnet_id,
            UserData=user_data,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'proxy',
                        },
                    ],
                },
            ],
        )

    else:
    # start proxy instance if it's stopped

        # get instance ids
        instances_id = [i['InstanceId'] for r in response['Reservations'] for i in r['Instances'] if i['State']['Name'] == 'stopped']

        if len(instances_id) > 0:
            print('Starting proxy')
            ec2.start_instances(InstanceIds=instances_id)

        else:
            print('Proxy already running')

def create_cluster_instances():
    # get subnet id and security group id
    subnet_id, sg_id = get_subnet_sg_ids()

    user_data = ''
    
    with open('cluster-user-data/master.txt', 'r') as reader:
        user_data = reader.read()

    ec2.run_instances(
        ImageId='ami-04505e74c0741db8d',
        InstanceType='t2.micro',
        KeyName='mysql',
        MaxCount=1,
        MinCount=1,
        SecurityGroupIds=[
            sg_id,
        ],
        SubnetId=subnet_id,
        UserData=user_data,
        PrivateIpAddress='10.84.15.10',
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': 'master',
                    },
                ],
            },
        ],
    )

    for i in range(1,4):
        with open(f'cluster-user-data/slave{i}.txt', 'r') as reader:
            user_data = reader.read()
        ec2.run_instances(
            ImageId='ami-04505e74c0741db8d',
            InstanceType='t2.micro',
            KeyName='mysql',
            MaxCount=1,
            MinCount=1,
            SecurityGroupIds=[
                sg_id,
            ],
            SubnetId=subnet_id,
            UserData=user_data,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'slave',
                        },
                    ],
                },
            ],
        )

def create_vpc():
    vpc = ec2.create_vpc(CidrBlock='10.84.0.0/16')

    # assign a name to our VPC
    vpc.create_tags(Tags=[{"Key": "Name", "Value": "mysql"}])
    vpc.wait_until_available()

    # enable public dns hostname
    ec2.modify_vpc_attribute( VpcId = vpc.id , EnableDnsSupport = { 'Value': True } )
    ec2.modify_vpc_attribute( VpcId = vpc.id , EnableDnsHostnames = { 'Value': True } )

    # create an internet gateway and attach it to VPC
    internetgateway = ec2.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=internetgateway.id)

    # create a route table and a public route
    routetable = vpc.create_route_table()
    route = routetable.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=internetgateway.id)

    # create subnet and associate it with route table
    subnet = ec2.create_subnet(CidrBlock='10.84.15.0/24', VpcId=vpc.id)
    routetable.associate_with_subnet(SubnetId=subnet.id)

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

    response = ec2.describe_vpcs(
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

        subnet_id = vpc.subnets[0].id

    else:
        vpc_id = response['Vpcs'][0]['VpcId']

        response = ec2.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id
                ]
            }
        ])

        subnet_id = response['Subnets'][0]['SubnetId']

    response = ec2.describe_security_groups(
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


deploy_cluster()
#deploy_proxy()
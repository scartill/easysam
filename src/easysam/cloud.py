import boto3
import logging as lg
from benedict import benedict


def scan(resources_data: benedict, errors: list[str], aws_profile: str = None):
    # Forward compatibility with future resources
    if '__future__' not in resources_data:
        return

    cloud = resources_data.get_dict('cloud', {})

    lg.info('Scanning cloud for resources')

    session_kwargs = {}
    if aws_profile:
        session_kwargs['profile_name'] = aws_profile

    session = boto3.Session(**session_kwargs)
    ec2 = session.client('ec2')

    vpcs = ec2.describe_vpcs()['Vpcs']

    if not vpcs:
        errors.append('Error: No VPCs found')
        return

    if len(vpcs) > 1:
        errors.append('Error: Not implemented for multiple VPCs')
        return

    vpc = vpcs[0]
    vpc_id = vpc['VpcId']
    cloud['vpc_id'] = vpc_id
    cloud['vpc_cidr'] = vpc['CidrBlock']

    lg.info(f'Found VPC {vpc_id} with CIDR {cloud["vpc_cidr"]}')

    subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])[
        'Subnets'
    ]
    subnet_ids = [subnet['SubnetId'] for subnet in subnets]

    lg.info(f'Found {len(subnet_ids)} subnets in VPC {vpc_id}')
    lg.debug(f'Subnet IDs: {subnet_ids}')

    cloud['subnet_ids'] = subnet_ids
    resources_data['cloud'] = cloud

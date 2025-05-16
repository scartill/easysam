import boto3


def get_aws_client(service, cliparams, resource=False):
    '''Create and return an AWS client with optional profile and region'''
    profile = cliparams.get('aws_profile')
    region = cliparams.get('region')
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    params = {}

    if region:
        params['region_name'] = region

    if resource:
        return session.resource(service, **params)
    else:
        return session.client(service, **params)


def get_aws_resource(service, cliparams):
    '''Create and return an AWS resource with optional profile and region'''
    return get_aws_client(service, cliparams, resource=True)

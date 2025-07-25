import boto3


def get_aws_client(service, cliparams, resource=False):
    '''Create and return an AWS client with optional profile'''
    profile = cliparams.get('aws_profile')
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    params = {}

    if resource:
        return session.resource(service, **params)
    else:
        return session.client(service, **params)


def get_aws_resource(service, cliparams):
    '''Create and return an AWS resource with optional profile'''
    return get_aws_client(service, cliparams, resource=True)

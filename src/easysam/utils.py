from pathlib import Path
import boto3


def get_aws_client(service, toolparams, resource=False):
    """Create and return an AWS client with optional profile"""
    profile = toolparams.get('aws_profile')
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    params = {}

    if resource:
        return session.resource(service, **params)
    else:
        return session.client(service, **params)


def get_aws_resource(service, toolparams):
    """Create and return an AWS resource with optional profile"""
    return get_aws_client(service, toolparams, resource=True)


def get_build_dir(directory, deploy_ctx):
    return Path(directory, 'build', deploy_ctx.get('name', 'default'))

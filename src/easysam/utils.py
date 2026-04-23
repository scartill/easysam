import boto3
import base64
import os


def get_aws_client(service, cliparams):
    '''Create and return an AWS client with optional profile'''
    profile = cliparams.get('aws_profile')
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    params = {}

    return session.client(service, **params)

import os

import boto3
from opensearchpy import (
    OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
)

INDEX_NAME = 'searchable-documents'


def create_client():
    service = 'aoss'
    region = os.getenv('REGION')
    collection = os.getenv('SEARCH_SEARCHABLE_COLLECTION_ID')
    host = f'{collection}.{region}.{service}.amazonaws.com'
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, service)
    return OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20
    )

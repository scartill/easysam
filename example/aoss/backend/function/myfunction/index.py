import os

import boto3
from opensearchpy import (
    OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
)
import requests
from requests_aws4auth import AWS4Auth


INDEX_NAME = 'searchable-documents'


def handler(event, context):
    try:
        match event:
            case 'search':
                return search_aoss()
            case 'index':
                return index_aoss()
            case _:
                return 'Warning: Invalid event'

    except Exception as e:
        return f'Error: {str(e)}'


def create_aoss_client():
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


def index_aoss():
    document = {
        'title': 'The Great Gatsby',
        'content': 'The Great Gatsby is a novel by F. Scott Fitzgerald. It is a story about the American Dream and the corruption of the American Dream.'
    }
    client = create_aoss_client()
    return client.index(index=INDEX_NAME, body=document)


def search_aoss():
    service = 'aoss'
    region = os.getenv('REGION')
    collection = os.getenv('SEARCH_SEARCHABLE_COLLECTION_ID')
    host = f'https://{collection}.{region}.{service}.amazonaws.com'
    index = INDEX_NAME

    url = host + "/" + index
    headers = {"Content-Type": "application/json"}

    awsauth = AWS4Auth(
        refreshable_credentials=boto3.Session().get_credentials(),
        region=region,
        service='aoss'  # NOTE: The service name is 'aoss' not 'es
    )

    query = {
        'query': {
            'match_all': {}
        }
    }

    r = requests.get(url + "/_search", auth=awsauth, headers=headers, json=query)
    r.raise_for_status()
    return r.text

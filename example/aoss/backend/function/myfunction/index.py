import os

import boto3
from opensearchpy import (
    OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
)

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


def search_aoss():
    client = create_aoss_client()
    query = {
        'query': {
            'match_all': {}
        }
    }
    return client.search(index=INDEX_NAME, body=query)


def index_aoss():
    document = {
        'title': 'The Great Gatsby',
        'content': 'The Great Gatsby is a novel by F. Scott Fitzgerald. It is a story about the American Dream and the corruption of the American Dream.'
    }
    client = create_aoss_client()
    return client.index(index=INDEX_NAME, body=document)

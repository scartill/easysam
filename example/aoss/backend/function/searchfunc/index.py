from common.aoss import create_client, INDEX_NAME


def handler(event, context):
    try:
        match event:
            case 'search':
                return search_aoss()
            case _:
                return 'Warning: Invalid event'

    except Exception as e:
        return f'Error: {str(e)}'


def search_aoss():
    client = create_client()
    query = {'query': {'match_all': {}}}
    return client.search(index=INDEX_NAME, body=query)

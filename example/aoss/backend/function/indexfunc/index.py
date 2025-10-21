from common.aoss import create_client, INDEX_NAME


def handler(event, context):
    try:
        match event:
            case 'index':
                return index_aoss()
            case _:
                return 'Warning: Invalid event'

    except Exception as e:
        return f'Error: {str(e)}'


def index_aoss():
    document = {
        'title': 'The Great Gatsby',
        'content': 'The Great Gatsby is a novel by F. Scott Fitzgerald. It is a story about the American Dream and the corruption of the American Dream.'
    }
    client = create_client()
    return client.index(index=INDEX_NAME, body=document)

import json
import logging
from common.aoss import create_client, INDEX_NAME

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        # Check if this is a DynamoDB Stream event
        if (
            'Records' in event
            and event['Records']
            and event['Records'][0].get('eventSource') == 'aws:dynamodb'
        ):
            return process_dynamodb_stream(event)

    except Exception as e:
        logger.error(f'Error processing event: {str(e)}')
        return f'Error: {str(e)}'


def process_dynamodb_stream(event):
    """
    Process DynamoDB Stream events from SearchableItem table.
    Automatically indexes items into OpenSearch when they are created or modified.
    """
    logger.info(f'Received {len(event["Records"])} records from DynamoDB Stream')
    client = create_client()

    for record in event['Records']:
        event_name = record['eventName']
        logger.info(f'Event type: {event_name}')

        if event_name == 'INSERT':
            new_image = record['dynamodb'].get('NewImage', {})
            logger.info(f'New item created: {json.dumps(new_image)}')
            # Index the new item in OpenSearch
            index_item(client, new_image)

        elif event_name == 'MODIFY':
            new_image = record['dynamodb'].get('NewImage', {})
            logger.info(f'Item modified: {json.dumps(new_image)}')
            # Update the item in OpenSearch
            index_item(client, new_image)

        elif event_name == 'REMOVE':
            old_image = record['dynamodb'].get('OldImage', {})
            item_id = old_image.get('ItemID', {}).get('S')
            logger.info(f'Item deleted: {item_id}')
            # Remove from OpenSearch index
            if item_id:
                remove_item(client, item_id)

    return {
        'statusCode': 200,
        'body': json.dumps(f'Successfully processed {len(event["Records"])} records'),
    }


def index_item(client, dynamodb_item):
    """
    Index a DynamoDB item into OpenSearch.
    Converts DynamoDB format to a regular document.
    """
    # Convert DynamoDB item format to regular document
    # This is a simple example - extend based on your schema
    document = {}
    for key, value in dynamodb_item.items():
        if 'S' in value:
            document[key] = value['S']
        elif 'N' in value:
            document[key] = value['N']

    item_id = document.get('ItemID')
    if item_id:
        logger.info(f'Indexing item {item_id} into OpenSearch')
        client.index(index=INDEX_NAME, id=item_id, body=document)


def remove_item(client, item_id):
    """Remove an item from the OpenSearch index."""
    try:
        logger.info(f'Removing item {item_id} from OpenSearch')
        client.delete(index=INDEX_NAME, id=item_id)
    except Exception as e:
        logger.warning(f'Could not delete item {item_id}: {str(e)}')

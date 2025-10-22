import json
import logging as lg

lg.basicConfig(level=lg.INFO)
logger = lg.getLogger()


def handler(event, context):
    '''
    DynamoDB Stream trigger handler that logs Item changes.
    This is a simple example demonstrating trigger functionality with Prismarine models.
    '''
    logger.info(f'Received event: {json.dumps(event)}')

    for record in event.get('Records', []):
        event_name = record.get('eventName')
        logger.info(f'Event: {event_name}')

        if event_name == 'INSERT':
            new_image = record['dynamodb'].get('NewImage', {})
            logger.info(f'New item created: {new_image}')

        elif event_name == 'MODIFY':
            new_image = record['dynamodb'].get('NewImage', {})
            old_image = record['dynamodb'].get('OldImage', {})
            logger.info(f'Item modified from {old_image} to {new_image}')

        elif event_name == 'REMOVE':
            old_image = record['dynamodb'].get('OldImage', {})
            logger.info(f'Item removed: {old_image}')

    return {
        'statusCode': 200,
        'body': json.dumps({'message': f'Processed {len(event.get("Records", []))} records'})
    }

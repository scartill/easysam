import os
import uuid
import json

import boto3


def handler(event, context):
    message = json.loads(event)
    print('Message received: ', message)
    env = os.getenv('ENV')
    simple_stream_name = f'kinesismultiplebucketsapp-simple-{env}'
    complex_stream_name = f'kinesismultiplebucketsapp-complex-{env}'
    kinesis = boto3.client('kinesis')

    uid = str(uuid.uuid4())

    kinesis.put_record(
        StreamName=complex_stream_name,
        PartitionKey=uid,
        Data=json.dumps(message).encode('utf-8'),
    )

    kinesis.put_record(
        StreamName=simple_stream_name,
        PartitionKey=uid,
        Data=json.dumps(message).encode('utf-8'),
    )

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*'
        },
        'body': json.dumps({'Result': 'OK'})
    }

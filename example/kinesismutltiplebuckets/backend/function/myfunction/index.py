import os
import json

import boto3


def handler(event, context):
    message = json.loads(event['body'])
    print('Message received: ', message)
    env = os.getenv('ENV')
    simple_stream_name = f'simple-{env}'
    complex_stream_name = f'complex-{env}'
    kinesis = boto3.client('kinesis')

    kinesis.put_record(
        StreamName=complex_stream_name,
        Data=json.dumps(message),
    )

    kinesis.put_record(
        StreamName=simple_stream_name,
        Data=json.dumps(message),
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

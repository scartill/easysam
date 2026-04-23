import json
import boto3
import os

s3 = boto3.client('s3')
sqs = boto3.client('sqs')


def handler(event, context):
    '''
    Example Lambda function demonstrating custom policies usage.
    This function has custom IAM policies that allow:
    - Creating CloudWatch Logs groups and streams
    - Putting log events
    
    The function can also access:
    - S3 bucket 'documents' (via bucket resource definition)
    - SQS queue 'notifications' (via send resource definition)
    '''
    bucket_name = os.environ.get('DOCUMENTS_BUCKET_NAME', '')
    queue_url = os.environ.get('NOTIFICATIONS_QUEUE_URL', '')
    
    # Example: List objects in the documents bucket
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        objects = [obj['Key'] for obj in response.get('Contents', [])]
    except Exception as e:
        objects = []
        print(f'Error listing bucket: {e}')
    
    # Example: Send message to notifications queue
    try:
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({'status': 'processed', 'timestamp': '2024-01-01T00:00:00Z'})
        )
    except Exception as e:
        print(f'Error sending message: {e}')
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*'
        },
        'body': json.dumps({
            'message': 'Function executed successfully',
            'bucket_objects_count': len(objects),
            'note': 'This function uses custom IAM policies for CloudWatch Logs access'
        })
    }

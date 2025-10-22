import boto3
import json
import time

import click


def invoke_lambda(function_name, message, env, aws_profile=None):
    """Directly invoke a lambda function"""
    session_kwargs = {}
    if aws_profile:
        session_kwargs['profile_name'] = aws_profile

    session = boto3.Session(**session_kwargs)
    lambda_client = session.client('lambda')

    response = lambda_client.invoke(
        FunctionName=f'{function_name}-{env}',
        Payload=json.dumps(message),
    )

    answer = json.loads(response['Payload'].read())
    click.echo(f'Lambda response: {answer}')


def trigger_stream_via_table(table_name, env, aws_profile=None):
    """Trigger DynamoDB Stream by inserting, modifying, and deleting an item"""
    session_kwargs = {}
    if aws_profile:
        session_kwargs['profile_name'] = aws_profile

    session = boto3.Session(**session_kwargs)
    dynamodb = session.client('dynamodb')
    full_table_name = f'{table_name}-{env}'

    click.echo(f'\n=== Testing DynamoDB Stream Triggers on {full_table_name} ===')

    # 1. Insert a new item (triggers INSERT event)
    item_id = f'test-item-{int(time.time())}'
    click.echo(f'\n1. Inserting item with ID: {item_id}')
    dynamodb.put_item(
        TableName=full_table_name,
        Item={
            'ItemID': {'S': item_id},
            'Title': {'S': 'Test Document'},
            'Content': {'S': 'This is a test document to trigger the DynamoDB Stream'},
        },
    )
    click.echo('   [OK] Item inserted - should trigger indexfunc with INSERT event')
    time.sleep(2)  # Give stream time to process

    # 2. Modify the item (triggers MODIFY event)
    click.echo(f'\n2. Modifying item {item_id}')
    dynamodb.put_item(
        TableName=full_table_name,
        Item={
            'ItemID': {'S': item_id},
            'Title': {'S': 'Updated Test Document'},
            'Content': {'S': 'This content has been updated'},
        },
    )
    click.echo('   [OK] Item updated - should trigger indexfunc with MODIFY event')
    time.sleep(2)

    # 3. Delete the item (triggers REMOVE event)
    click.echo(f'\n3. Deleting item {item_id}')
    dynamodb.delete_item(TableName=full_table_name, Key={'ItemID': {'S': item_id}})
    click.echo('   [OK] Item deleted - should trigger indexfunc with REMOVE event')
    click.echo('\nCheck CloudWatch Logs for indexfunc to see the stream processing!')


@click.command()
@click.option('--env', default='easysamdev')
@click.option('--aws-profile', default='adsight', help='AWS profile to use')
@click.option(
    '--test-stream/--no-test-stream', default=True, help='Test DynamoDB Stream triggers'
)
@click.option(
    '--test-search/--no-test-search', default=True, help='Test search function'
)
def main(env, aws_profile, test_stream, test_search):
    """Test the AOSS application with DynamoDB Streams and search functionality"""

    if test_stream:
        # Trigger the stream by manipulating the table
        trigger_stream_via_table('AossSearchableItem', env, aws_profile)

    if test_search:
        # Test the search function
        click.echo('\n=== Testing Search Function ===')
        invoke_lambda('searchfunc', 'search', env, aws_profile)


if __name__ == '__main__':
    main()

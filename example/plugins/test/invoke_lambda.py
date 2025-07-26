import boto3
import json

import click


@click.command()
@click.option('--env', default='dev')
@click.argument('message', default='{"message": "Hello, World!"}')
def send_message(message, env):
    lambda_client = boto3.client('lambda')

    response = lambda_client.invoke(
        FunctionName=f'mycustomfun-{env}',
        Payload=json.dumps(message),
    )

    answer = json.loads(response['Payload'].read())
    body = json.loads(answer['body'])
    click.echo(json.dumps(body, indent=2))


if __name__ == '__main__':
    send_message()

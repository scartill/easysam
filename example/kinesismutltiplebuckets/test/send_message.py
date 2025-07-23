import boto3
import json

import click


@click.command()
@click.argument('message')
@click.option('--env', default='kinesissampledev')
def send_message(message, env):
    lambda_client = boto3.client('lambda')

    response = lambda_client.invoke(
        FunctionName=f'myfunction-{env}',
        Payload=json.dumps(message),
    )

    answer = response['Payload'].read()
    click.echo(answer)


if __name__ == '__main__':
    send_message()

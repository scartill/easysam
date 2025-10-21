import boto3
import json

import click


def send_message(function_name, message, env):
    lambda_client = boto3.client('lambda')

    response = lambda_client.invoke(
        FunctionName=f'{function_name}-{env}',
        Payload=json.dumps(message),
    )

    answer = json.loads(response['Payload'].read())
    click.echo(answer)


@click.command()
@click.option('--env', default='easysamdev')
def main(env):
    send_message('indexfunc', 'index', env)
    send_message('searchfunc', 'search', env)


if __name__ == '__main__':
    main()

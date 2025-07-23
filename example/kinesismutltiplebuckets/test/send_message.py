import boto3
import json


def send_message(message, env='kinesissampledev'):
    lambda_client = boto3.client('lambda')

    response = lambda_client.invoke(
        FunctionName=f'myfunction-{env}',
        Payload=json.dumps(message),
    )

    return response['Payload'].read()


if __name__ == '__main__':
    response = send_message({'message': 'Hello, world!'})
    print(response)

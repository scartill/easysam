import boto3

from prismarine.runtime.dynamo_access import DynamoAccess
from common.utils import get_env


class MyDynamoAccess(DynamoAccess):
    def get_resource(self):
        return boto3.resource('dynamodb')

    def get_table(self, full_model_name: str):
        env = get_env()
        return self.get_resource().Table(f'{full_model_name}-{env}')


dynamoaccess = MyDynamoAccess()


def get_dynamo_access():
    return dynamoaccess

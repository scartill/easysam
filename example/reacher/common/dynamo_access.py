import boto3

from prismarine.runtime.dynamo_access import DynamoAccess
from common.utils import get_env


class MyDynamoAccess(DynamoAccess):
    def get_resource(self):
        return boto3.resource('dynamodb')

    def get_table(self, full_model_name: str):
        env = get_env()
        return self.get_resource().Table(f'{full_model_name}-{env}')

    # get_client() is inherited from DynamoAccess (returns
    # self.get_resource().meta.client) and is what the generated vector
    # search() method uses for the low-level SearchVectors call. No override
    # needed unless you want a dedicated boto3 client.


dynamoaccess = MyDynamoAccess()


def get_dynamo_access():
    return dynamoaccess

from pathlib import Path
import logging as lg


UTILS_PY = '''\
# Common code

def my_common_function():
    return 'Hello, world!'
'''

RESOURCES_YAML = '''\
prefix: MyApp

tags:
  mytag: myvalue

import:
  - backend
'''

LAMBDA_EASY_SAM = '''\
lambda:
  name: myfunction
  resources:
    tables:
    - MyItem
  integration:
    path: /items
    open: true
    greedy: false
'''

INDEX_PY = '''\
# Lambda function code

import json

import common.utils as u


def handler(event, context):
    data = u.my_common_function()

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*'
        },
        'body': json.dumps({'data': data})
    }
'''


DATABASE_EASY_SAM = '''\
tables:
  MyItem:
    attributes:
    - hash: true
      name: ItemID
'''

ROOT_GITIGNORE = '''\
build
template.yml
template.yaml
swagger.yaml
prismarine_client.py
.aws-sam
'''

FUNCTION_GITIGNORE = '''\
__pycache__/
*.py[oc]
**/common/
'''

REQUIREMENTS_TXT = '''\
boto3
'''

REQUIREMENTS_TXT_PRISMARINE = '''\
boto3
prismarine
'''

RESOURCES_YAML_PRISMARINE = '''\
prefix: MyApp

import:
  - backend

prismarine:
  default-base: common
  access-module: common.dynamo_access
  tables:
    - package: myobject
'''

UTILS_PY_PRISMARINE = '''\
import os


def get_env():
    return os.environ.get('ENV', 'dev')
'''

DYNAMO_ACCESS_PY = '''\
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
'''

MODELS_PY = '''\
from typing import TypedDict, NotRequired
from prismarine.runtime import Cluster


c = Cluster('MyApp')


@c.model(PK='Foo', SK='Bar', trigger='itemlogger')
class Item(TypedDict):
    Foo: str
    Bar: str
    Baz: NotRequired[str]
'''

DB_PY = '''\
import prismarine_client as pc


class ItemModel(pc.ItemModel):
    pass
'''

TRIGGER_LAMBDA_EASY_SAM = '''\
lambda:
  name: itemlogger
  resources:
    tables:
    - Item
'''

TRIGGER_INDEX_PY = '''\
import json
import logging as lg

lg.basicConfig(level=lg.INFO)
logger = lg.getLogger()


def handler(event, context):
    '''
    DynamoDB Stream trigger handler that logs Item changes.
    This is a simple example demonstrating trigger functionality with Prismarine models.
    '''
    logger.info(f'Received event: {json.dumps(event)}')

    for record in event.get('Records', []):
        event_name = record.get('eventName')
        logger.info(f'Event: {event_name}')

        if event_name == 'INSERT':
            new_image = record['dynamodb'].get('NewImage', {})
            logger.info(f'New item created: {new_image}')

        elif event_name == 'MODIFY':
            new_image = record['dynamodb'].get('NewImage', {})
            old_image = record['dynamodb'].get('OldImage', {})
            logger.info(f'Item modified from {old_image} to {new_image}')

        elif event_name == 'REMOVE':
            old_image = record['dynamodb'].get('OldImage', {})
            logger.info(f'Item removed: {old_image}')

    return {
        'statusCode': 200,
        'body': json.dumps({'message': f'Processed {len(event.get("Records", []))} records'})
    }
'''


def init(cliparams, app_name, prismarine=False):
    lg.info(f'Initializing app {app_name} {"with Prismarine support" if prismarine else ""}')
    app_dir = Path(app_name)
    lg.debug(f'Creating app directory {app_dir}')
    app_dir.mkdir(parents=True, exist_ok=True)
    lg.debug(f'Creating resources EasySAM file {app_dir / "resources.yaml"}')
    resources_content = RESOURCES_YAML_PRISMARINE if prismarine else RESOURCES_YAML
    app_dir.joinpath('resources.yaml').write_text(resources_content)
    lg.debug(f'Creating root .gitignore file {app_dir / ".gitignore"}')
    app_dir.joinpath('.gitignore').write_text(ROOT_GITIGNORE)

    common_dir = app_dir / 'common'
    common_dir.mkdir(parents=True, exist_ok=True)
    lg.debug(f'Creating common directory {common_dir}')
    utils_content = UTILS_PY_PRISMARINE if prismarine else UTILS_PY
    common_dir.joinpath('utils.py').write_text(utils_content)

    if prismarine:
        lg.debug(f'Creating dynamo_access.py file {common_dir / "dynamo_access.py"}')
        common_dir.joinpath('dynamo_access.py').write_text(DYNAMO_ACCESS_PY)
        myobject_dir = common_dir / 'myobject'
        lg.debug(f'Creating myobject directory {myobject_dir}')
        myobject_dir.mkdir(parents=True, exist_ok=True)
        lg.debug(f'Creating models.py file {myobject_dir / "models.py"}')
        myobject_dir.joinpath('models.py').write_text(MODELS_PY)
        lg.debug(f'Creating db.py file {myobject_dir / "db.py"}')
        myobject_dir.joinpath('db.py').write_text(DB_PY)

    backend_dir = app_dir / 'backend'
    lg.debug(f'Creating backend directory {backend_dir}')
    backend_dir.mkdir(parents=True, exist_ok=True)

    if not prismarine:
        lg.debug(f'Creating database directory {backend_dir}')
        database_dir = backend_dir / 'database'
        database_dir.mkdir(parents=True, exist_ok=True)
        lg.debug(f'Creating database EasySAM file {database_dir / "easysam.yaml"}')
        database_dir.joinpath('easysam.yaml').write_text(DATABASE_EASY_SAM)

    function_dir = backend_dir / 'function'
    lg.debug(f'Creating function directory {function_dir}')
    function_dir.mkdir(parents=True, exist_ok=True)
    lg.debug(f'Creating function .gitignore file {function_dir / ".gitignore"}')
    function_dir.joinpath('.gitignore').write_text(FUNCTION_GITIGNORE)

    if prismarine:
        lambda_dir = function_dir / 'itemlogger'
        lg.debug(f'Creating lambda directory {lambda_dir}')
        lambda_dir.mkdir(parents=True, exist_ok=True)
        lg.debug(f'Creating lambda EasySAM file {lambda_dir / "easysam.yaml"}')
        lambda_dir.joinpath('easysam.yaml').write_text(TRIGGER_LAMBDA_EASY_SAM)
        lg.debug(f'Creating lambda index file {lambda_dir / "index.py"}')
        lambda_dir.joinpath('index.py').write_text(TRIGGER_INDEX_PY)
    else:
        lambda_dir = function_dir / 'myfunction'
        lg.debug(f'Creating lambda directory {lambda_dir}')
        lambda_dir.mkdir(parents=True, exist_ok=True)
        lg.debug(f'Creating lambda EasySAM file {lambda_dir / "easysam.yaml"}')
        lambda_dir.joinpath('easysam.yaml').write_text(LAMBDA_EASY_SAM)
        lg.debug(f'Creating lambda index file {lambda_dir / "index.py"}')
        lambda_dir.joinpath('index.py').write_text(INDEX_PY)

    third_party_dir = app_dir / 'thirdparty'
    lg.debug(f'Creating third party directory {third_party_dir}')
    third_party_dir.mkdir(parents=True, exist_ok=True)
    lg.debug(f'Creating third party requirements.txt file {third_party_dir / "requirements.txt"}')
    requirements_content = REQUIREMENTS_TXT_PRISMARINE if prismarine else REQUIREMENTS_TXT
    third_party_dir.joinpath('requirements.txt').write_text(requirements_content)

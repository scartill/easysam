from pathlib import Path
import logging as lg


UTILS_PY = '''\
# Common code

def my_common_function():
    return 'Hello, world!'
'''

RESOURCES_YAML = '''\
prefix: MyApp

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


def init(cliparams, app_name):
    lg.info(f'Initializing app {app_name}')
    app_dir = Path(app_name)
    lg.debug(f'Creating app directory {app_dir}')
    app_dir.mkdir(parents=True, exist_ok=True)
    lg.debug(f'Creating resources EasySAM file {app_dir / "resources.yaml"}')
    app_dir.joinpath('resources.yaml').write_text(RESOURCES_YAML)
    lg.debug(f'Creating root .gitignore file {app_dir / ".gitignore"}')
    app_dir.joinpath('.gitignore').write_text(ROOT_GITIGNORE)

    common_dir = app_dir / 'common'
    common_dir.mkdir(parents=True, exist_ok=True)
    lg.debug(f'Creating common directory {common_dir}')
    common_dir.joinpath('utils.py').write_text(UTILS_PY)

    backend_dir = app_dir / 'backend'
    lg.debug(f'Creating backend directory {backend_dir}')
    backend_dir.mkdir(parents=True, exist_ok=True)
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
    third_party_dir.joinpath('requirements.txt').write_text(REQUIREMENTS_TXT)

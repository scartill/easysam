import logging as lg

from jsonschema import validate as validate_schema, ValidationError

BUCKETS_SCHEMA = {
    'type': 'object',
    'properties': {
        'public': {'type': 'boolean'},
        'extaccesspolicy': {'type': 'string'}
    },
    'required': ['public'],
    'optional': ['extaccesspolicy'],
    'additionalProperties': False
}

QUEUES_SCHEMA = {
    'type': 'object',
    'properties': {
    },
    'additionalProperties': False
}

STREAMS_SCHEMA = {
    'type': 'object',
    'properties': {
        'bucketname': {'type': 'string'},
        'bucketprefix': {'type': 'string'},
        'intervalinseconds': {
            'type': 'integer',
            'minimum': 60,
            'maximum': 900
        },
    },
    'required': ['bucketname', 'bucketprefix'],
    'optional': ['intervalinseconds'],
    'additionalProperties': False
}

LAMBDA_SCHEMA = {
    'type': 'object',
    'properties': {
        'resources': {'type': 'object'},
        'timeout': {
            'type': 'integer',
            'minimum': 1,
            'maximum': 900
        },
        'buckets': {'type': 'array', 'items': {'type': 'string'}},
        'send': {'type': 'array', 'items': {'type': 'string'}},
        'streams': {'type': 'array', 'items': {'type': 'string'}},
        'tables': {'type': 'array', 'items': {'type': 'string'}},
        'queues': {'type': 'array', 'items': {'type': 'string'}},
        'services': {
            'type': 'array',
            'items': {
                'type': 'string',
                'enum': ['comprehend']
            }
        },
        'uri': {'type': 'string'}
    },
    'required': ['uri'],
    'optional': ['timeout', 'send', 'streams', 'tables'],
    'additionalProperties': False
}

PATH_SCHEMA = {
    'type': 'object',
    'properties': {
        'integration': {
            'type': 'string',
            'enum': ['lambda', 'dynamo', 'sqs']
        },
        'method': {
            'type': 'string',
            'enum': ['get', 'post']
        },
        'function': {'type': 'string'},
        'parameters': {'type': 'array', 'items': {'type': 'string'}},
        'action': {'type': 'string'},
        'role': {'type': 'string'},
        'queue': {'type': 'string'},
        'requestTemplate': {'type': 'string'},
        'responseTemplateFile': {'type': 'string'},
        'authorizer': {'type': 'string'},
        'greedy': {'type': 'boolean'},
        'open': {'type': 'boolean'}
    },
    'optional': [
        'integration',
        'method',
        'role',
        'queue',
        'requestTemplate',
        'responseTemplateFile',
        'authorizer',
        'greedy',
        'open'
    ],
    'additionalProperties': False
}

RESOURCES_SCHEMA = {
    'type': 'object',
    'properties': {
        'prefix': {'type': 'string'},
        'buckets': {
            'type': 'object',
            'patternProperties': {
                '^[\\$a-z0-9-]+$': BUCKETS_SCHEMA
            },
            'additionalProperties': False
        },
        'queues': {
            'type': 'object',
            'patternProperties': {
                '^[\\$a-z0-9-]+$': {'type': 'null'}
            },
            'additionalProperties': False
        },
        'streams': {
            'type': 'object',
            'patternProperties': {
                '^[\\$a-z0-9-]+$': STREAMS_SCHEMA
            },
            'additionalProperties': False
        },
        'functions': {
            'type': 'object',
            'patternProperties': {
                '^[\\$a-z0-9-]+$': LAMBDA_SCHEMA
            },
            'additionalProperties': False
        },
        'paths': {
            'type': 'object',
            'patternProperties': {
                '^[\\$a-zA-Z0-9\\{\\}/]+$': PATH_SCHEMA
            },
            'additionalProperties': False
        },
        'import': {'type': 'array'},
        'prismarine': {'type': 'object'},
        'tables': {'type': 'object'},
        'authorizers': {'type': 'object'},
    },
    'required': ['prefix'],
    'optional': [
        'buckets',
        'queues',
        'streams',
        'lambda',
        'paths',
        'import',
        'prismarine',
        'functions',
        'tables',
        'authorizers',
    ],
    'additionalProperties': False,
}


def validate_schema(resources_data: dict, errors: list[str]):
    try:
        validate_schema(resources_data, RESOURCES_SCHEMA)

    except ValidationError as e:
        lg.error(f'Invalid resources data: {e}')
        errors.append(f"Invalid resources data: {e.message}")
        return

    validate_buckets(resources_data, errors)
    validate_queues(resources_data, errors)
    validate_streams(resources_data, errors)
    validate_lambda(resources_data, errors)
    validate_paths(resources_data, errors)
    validate_import(resources_data, errors)
    validate_prismarine(resources_data, errors)


def validate_buckets(resources_data: dict, errors: list[str]):
    for bucket, details in resources_data['buckets'].items():
        if bucket == 'private' and details['public']:
            errors.append(f"Bucket '{bucket}' cannot be public")


def validate_queues(resources_data: dict, errors: list[str]):
    pass


def validate_streams(resources_data: dict, errors: list[str]):
    for stream, details in resources_data['streams'].items():
        bucketname = details['bucketname']

        if resources_data['buckets'].get(bucketname) is None:
            errors.append(f"Stream '{stream}' bucketname must be a valid bucket")
            continue


def validate_lambda(resources_data: dict, errors: list[str]):
    for lambda_func, details in resources_data['functions'].items():
        if 'buckets' in details:
            for bucket in details['buckets']:
                if bucket not in resources_data['buckets']:
                    errors.append(f"Lambda '{lambda_func}' bucket must be a valid bucket")
                    continue

        if 'tables' in details:
            for table in details['tables']:
                if table not in resources_data['tables']:
                    errors.append(f"Lambda '{lambda_func}' table must be a valid table")
                    continue

        if 'queues' in details:
            for queue in details['queues']:
                if queue not in resources_data['queues']:
                    errors.append(f"Lambda '{lambda_func}' queue must be a valid queue")
                    continue

        if 'streams' in details:
            for stream in details['streams']:
                if stream not in resources_data['streams']:
                    errors.append(f"Lambda '{lambda_func}' stream must be a valid stream")
                    continue


def validate_paths(resources_data: dict, errors: list[str]):
    for path, details in resources_data['paths'].items():
        match details.get('integration', 'lambda'):
            case 'lambda':
                validate_lambda_path(resources_data, path, details, errors)
            case 'dynamo':
                validate_dynamo_path(details, errors)
            case 'sqs':
                validate_sqs_path(details, errors)


def validate_lambda_path(resources_data: dict, path: str, details: dict, errors: list[str]):
    for key in details.keys():
        if key not in ['integration', 'function', 'authorizer', 'greedy']:
            errors.append(f"Lambda path '{path}' has invalid key: {key}")

    if 'authorizer' in details and 'open' in details:
        errors.append('Lambda path cannot have both authorizer and open')

    if 'authorizer' not in details and 'open' not in details:
        errors.append('Lambda path must have either authorizer or open')

    if 'authorizer' in details:
        if details['authorizer'] not in resources_data['authorizers']:
            errors.append(f"Lambda path '{path}' authorizer must be a valid authorizer")


def validate_dynamo_path(details: dict, errors: list[str]):
    pass


def validate_sqs_path(details: dict, errors: list[str]):
    pass


def validate_import(resources_data: dict, errors: list[str]):
    if 'import' in resources_data:
        if not isinstance(resources_data['import'], list):
            errors.append('Import must be a list')
            return
        for import_item in resources_data['import']:
            if not isinstance(import_item, str):
                errors.append('Each import item must be a string')


def validate_prismarine(resources_data: dict, errors: list[str]):
    if 'prismarine' in resources_data:
        if not isinstance(resources_data['prismarine'], dict):
            errors.append('Prismarine must be a dictionary')
            return
        if 'default-base' not in resources_data['prismarine']:
            errors.append('Prismarine must have a default-base')
        if 'access-module' not in resources_data['prismarine']:
            errors.append('Prismarine must have an access-module')
        if 'tables' in resources_data['prismarine']:
            if not isinstance(resources_data['prismarine']['tables'], list):
                errors.append('Prismarine tables must be a list')
        else:
            errors.append('Prismarine must have tables defined')

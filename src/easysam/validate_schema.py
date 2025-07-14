import logging as lg

from jsonschema import Draft7Validator


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

LAMBDA_POLL_SCHEMA = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'batchsize': {'type': 'integer'},
            'batchwindow': {'type': 'integer'},
        },
        'required': ['name'],
        'optional': ['batchsize', 'batchwindow'],
        'additionalProperties': False
    }
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
        'polls': LAMBDA_POLL_SCHEMA,
        'services': {
            'type': 'array',
            'items': {
                'type': 'string',
                'enum': ['comprehend']
            }
        },
        'uri': {'type': 'string'},
        'schedule': {'type': 'string'},
    },
    'required': ['uri'],
    'optional': [
        'timeout',
        'send',
        'streams',
        'tables',
        'queues',
        'polls',
        'services',
        'schedule',
    ],
    'additionalProperties': False
}

LAMBDA_PATH_SCHEMA = {
    'type': 'object',
    'properties': {
        'integration': {
            'type': 'string',
            'enum': ['lambda']
        },
        'function': {'type': 'string'},
        'authorizer': {'type': 'string'},
        'greedy': {'type': 'boolean'},
        'open': {'type': 'boolean'}
    },
    'required': ['integration', 'function'],
    'optional': ['authorizer', 'greedy', 'open'],
    'additionalProperties': False
}

DYNAMO_PATH_SCHEMA = {
    'type': 'object',
    'properties': {
        'integration': {
            'type': 'string',
            'enum': ['dynamo']
        },
        'method': {
            'type': 'string',
            'enum': ['get', 'post']
        },
        'parameters': {'type': 'array', 'items': {'type': 'string'}},
        'action': {'type': 'string'},
        'role': {'type': 'string'},
        'requestTemplate': {'type': 'string'},
        'responseTemplateFile': {'type': 'string'},
    },
    'required': [
        'integration',
        'method',
        'parameters',
        'action',
        'role',
        'requestTemplate',
        'responseTemplateFile'
    ],
    'additionalProperties': False
}

SQS_PATH_SCHEMA = {
    'type': 'object',
    'properties': {
        'integration': {
            'type': 'string',
            'enum': ['sqs']
        },
        'method': {
            'type': 'string',
            'enum': ['get', 'post']
        },
        'role': {'type': 'string'},
        'queue': {'type': 'string'},
        'requestTemplate': {'type': 'string'},
        'responseTemplateFile': {'type': 'string'},
        'authorizer': {'type': 'string'},
    },
    'required': [
        'integration',
        'method',
        'role',
        'queue',
        'requestTemplate',
        'responseTemplateFile',
    ],
    'optional': ['authorizer'],
    'additionalProperties': False
}

PATH_SCHEMA = {
    'oneOf': [LAMBDA_PATH_SCHEMA, DYNAMO_PATH_SCHEMA, SQS_PATH_SCHEMA]
}

PRISMARINE_SCHEMA = {
    'type': 'object',
    'properties': {
        'default-base': {'type': 'string'},
        'access-module': {'type': 'string'},
        'extra-imports': {'type': 'array', 'items': {'type': 'string'}},
        'tables': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'package': {'type': 'string'},
                    'base': {'type': 'string'},
                },
                'required': ['package'],
                'optional': ['base'],
                'additionalProperties': False
            }
        }
    },
    'required': ['tables'],
    'optional': ['default-base', 'access-module', 'extra-imports'],
    'additionalProperties': False
}

TABLE_ATTRIBUTE_SCHEMA = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'hash': {'type': 'boolean'},
        'range': {'type': 'boolean'},
    },
    'required': ['name'],
    'optional': ['hash', 'range'],
    'additionalProperties': False
}

TABLES_SCHEMA = {
    'type': 'object',
    'properties': {
        'attributes': {
            'type': 'array',
            'items': TABLE_ATTRIBUTE_SCHEMA
        },
        'indices': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'attributes': {
                        'type': 'array',
                        'items': TABLE_ATTRIBUTE_SCHEMA,
                        'additionalProperties': False
                    },
                },
                'required': ['name', 'attributes'],
                'additionalProperties': False
            }
        }
    },
    'required': ['attributes'],
    'optional': ['indices'],
    'additionalProperties': False
}

AUTHORIZER_SCHEMA = {
    'type': 'object',
    'properties': {
        'function': {'type': 'string'},
        'token': {'type': 'string'},
        'query': {'type': 'string'},
        'headers': {'type': 'array', 'items': {'type': 'string'}},
        'ttl': {'type': 'integer'},
    },
    'required': ['function'],
    'optional': ['token', 'query', 'headers', 'ttl'],
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
        'import': {'type': 'array', 'items': {'type': 'string'}},
        'prismarine': PRISMARINE_SCHEMA,
        'tables': {
            'type': 'object',
            'patternProperties': {
                '^[\\$a-zA-Z0-9-]+$': TABLES_SCHEMA
            },
            'additionalProperties': False
        },
        'authorizers': {
            'type': 'object',
            'patternProperties': {
                '^[\\$a-z0-9-]+$': AUTHORIZER_SCHEMA
            },
            'additionalProperties': False
        },
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


def validate(resources_data: dict, errors: list[str]):
    # General schema validation
    validator = Draft7Validator(RESOURCES_SCHEMA)
    validation_errors = sorted(validator.iter_errors(resources_data), key=str)

    for error in validation_errors:
        lg.error(f'Validation error: {error}')
        errors.append(f"Invalid resources data: {error.message} in {list(error.path)}")

    # More specific validations
    validate_buckets(resources_data, errors)
    validate_queues(resources_data, errors)
    validate_streams(resources_data, errors)
    validate_lambda(resources_data, errors)
    validate_paths(resources_data, errors)
    validate_import(resources_data, errors)
    validate_prismarine(resources_data, errors)


def validate_buckets(resources_data: dict, errors: list[str]):
    for bucket, details in resources_data.get('buckets', {}).items():
        if bucket == 'private' and details['public']:
            errors.append(f"Bucket '{bucket}' cannot be public")


def validate_queues(resources_data: dict, errors: list[str]):
    pass


def validate_streams(resources_data: dict, errors: list[str]):
    for stream, details in resources_data.get('streams', {}).items():
        bucketname = details['bucketname']

        if resources_data['buckets'].get(bucketname) is None:
            errors.append(
                f"Stream '{stream}': '{bucketname}' must be a valid bucket"
            )

            continue


def validate_lambda(resources_data: dict, errors: list[str]):
    for lambda_name, details in resources_data.get('functions', {}).items():
        for bucket in details.get('buckets', []):
            if bucket not in resources_data['buckets']:
                errors.append(
                    f'Lambda {lambda_name}: '
                    f'Bucket {bucket} must be a valid bucket'
                )

                continue

        for table in details.get('tables', []):
            if table not in resources_data['tables']:
                errors.append(
                    f'Lambda {lambda_name}: '
                    f'Table {table} must be a valid table'
                )

                continue

        for poll in details.get('polls', []):
            if poll['name'] not in resources_data['queues']:
                errors.append(
                    f'Lambda {lambda_name}: '
                    f'Queue {poll["name"]} must be a valid queue'
                )

                continue

        for send in details.get('send', []):
            if send not in resources_data['queues']:
                errors.append(
                    f'Lambda {lambda_name}: '
                    f'Send {send} must be a valid queue'
                )

                continue

        for stream in details.get('streams', []):
            if stream not in resources_data['streams']:
                errors.append(
                    f'Lambda {lambda_name}: '
                    f'Stream {stream} must be a valid stream'
                )

                continue


def validate_paths(resources_data: dict, errors: list[str]):
    for path, details in resources_data.get('paths', {}).items():
        match details.get('integration', 'lambda'):
            case 'lambda':
                validate_lambda_path(resources_data, path, details, errors)
            case 'dynamo':
                validate_dynamo_path(details, errors)
            case 'sqs':
                validate_sqs_path(details, errors)


def validate_lambda_path(resources_data: dict, path: str, details: dict, errors: list[str]):
    if 'authorizer' in details and 'open' in details:
        errors.append('Lambda path cannot have both authorizer and open')

    if 'authorizer' not in details and 'open' not in details:
        errors.append('Lambda path must have either authorizer or open')

    if 'authorizer' in details:
        if details['authorizer'] not in resources_data.get('authorizers', {}):
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

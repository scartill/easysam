import logging as lg
from pathlib import Path

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
    'required': ['integration', 'function', 'greedy'],
    'optional': ['authorizer', 'open'],
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
            'enum': ['get']
        },
        'parameters': {
            'type': 'array',
            'items': {'type': 'string'}
        },
        'action': {
            'type': 'string',
            'enum': ['GetItem']
        },
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
            'enum': ['post']
        },
        'role': {'type': 'string'},
        'queue': {'type': 'string'},
        'requestTemplate': {'type': 'string'},
        'requestTemplateFile': {'type': 'string'},
        'responseTemplate': {'type': 'string'},
        'responseTemplateFile': {'type': 'string'},
        'authorizer': {'type': 'string'},
    },
    'required': [
        'integration',
        'method',
        'role',
        'queue',
    ],
    'optional': [
        'authorizer',
        'requestTemplate',
        'requestTemplateFile',
        'responseTemplate',
        'responseTemplateFile',
    ],
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
        'ttl': {'type': 'integer', 'minimum': 0, 'maximum': 3600},
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


def validate(resources_dir: Path, resources_data: dict, errors: list[str]):
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
    validate_paths(resources_dir, resources_data, errors)
    validate_import(resources_dir, resources_data, errors)
    validate_prismarine(resources_dir, resources_data, errors)
    validate_authorizers(resources_data, errors)


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


def validate_paths(resources_dir: Path, resources_data: dict, errors: list[str]):
    for path, details in resources_data.get('paths', {}).items():
        match details.get('integration', 'lambda'):
            case 'lambda':
                validate_lambda_path(resources_data, path, details, errors)
            case 'dynamo':
                validate_dynamo_path(resources_dir, path, details, errors)
            case 'sqs':
                validate_sqs_path(resources_dir, resources_data, path, details, errors)


def validate_lambda_path(resources_data: dict, path: str, details: dict, errors: list[str]):
    authorizer = details.get('authorizer')
    open_path = details.get('open')

    if authorizer and open_path:
        errors.append('Lambda path cannot have both authorizer and open')

    if not authorizer and not open_path:
        errors.append('Lambda path must have either authorizer or be open')

    if authorizer:
        if authorizer not in resources_data.get('authorizers', {}):
            errors.append(f"Lambda path '{path}' authorizer must be a valid authorizer")


def validate_dynamo_path(
        resources_dir: Path,
        path: str,
        details: dict,
        errors: list[str]
):
    validate_request_response_templates(resources_dir, path, details, errors)


def validate_sqs_path(
        resources_dir: Path,
        resources_data: dict,
        path: str,
        details: dict,
        errors: list[str]
):
    if details['queue'] not in resources_data['queues']:
        errors.append(f"SQS path '{path}' queue must be a valid queue")

    validate_request_response_templates(resources_dir, path, details, errors)


def validate_request_response_templates(
        resources_dir: Path,
        path: str,
        details: dict,
        errors: list[str]
):
    request = False
    response = False

    if request_template_file := details.get('requestTemplateFile'):
        request_template_path = Path(resources_dir, request_template_file).resolve()

        if not request_template_path.exists():
            errors.append(f"SQS path '{path}' request template must be a valid file")

        if 'requestTemplate' in details:
            errors.append(
                f"Path '{path}' cannot have both requestTemplate and requestTemplateFile"
            )

        request = True

    if 'requestTemplate' in details:
        request = True

    if response_template_file := details.get('responseTemplateFile'):
        response_template_path = Path(resources_dir, response_template_file).resolve()

        if not response_template_path.exists():
            errors.append(f"SQS path '{path}' response template must be a valid file")

        if 'responseTemplate' in details:
            errors.append(
                f"Path '{path}' cannot have both responseTemplate and responseTemplateFile"
            )

        response = True

    if 'responseTemplate' in details:
        response = True

    if not request:
        errors.append(f"Path '{path}' must have a request template")

    if not response:
        errors.append(f"Path '{path}' must have a response template")


def validate_import(resources_dir: Path, resources_data: dict, errors: list[str]):
    if import_list := resources_data.get('import'):
        for import_item in import_list:
            import_path = Path(resources_dir, import_item).resolve()

            if not import_path.exists():
                errors.append(f"Import '{import_item}' must be a valid directory")


def validate_prismarine(resources_dir: Path, resources_data: dict, errors: list[str]):
    prismarine = resources_data.get('prismarine', {})

    if not prismarine:
        return

    default_base = prismarine.get('default-base')
    default_base_dir = Path(resources_dir, default_base).resolve()

    if not default_base_dir.exists():
        errors.append(f"Prismarine default-base '{default_base}' must be a valid directory")
        return

    for table in prismarine.get('tables', []):
        table_base = table.get('base') or default_base
        table_base_dir = Path(resources_dir, table_base).resolve()

        if not table_base_dir.exists():
            errors.append(
                f"Prismarine table package '{table_base}' must have a valid bsee directory"
            )


def validate_authorizers(resources_data: dict, errors: list[str]):
    for authorizer, details in resources_data.get('authorizers', {}).items():
        present_types = ['token' in details, 'query' in details, 'headers' in details]

        if present_types.count(True) != 1:
            errors.append(f"Authorizer '{authorizer}' cannot have multiple types")

        if details['function'] not in resources_data.get('functions', {}):
            errors.append(f"Authorizer '{authorizer}' function must be a valid function")

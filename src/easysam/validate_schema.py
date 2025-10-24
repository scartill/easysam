import json
import logging as lg
from pathlib import Path

from jsonschema import Draft7Validator


def validate(resources_dir: Path, resources_data: dict, errors: list[str]):
    '''Validate resources data against the schema and perform custom validations.

    Args:
        resources_dir: The directory containing the resources.yaml file.
        resources_data: The pre-loaded resources data dictionary.
        errors: The list of errors.
    '''

    schema = load_schema()
    validator = Draft7Validator(schema)
    validation_errors = sorted(validator.iter_errors(resources_data), key=str)

    for error in validation_errors:
        lg.error(f'Validation error: {error}')
        errors.append(f'Invalid resources data: {error.message} in {list(error.path)}')

    # More specific validations
    validate_buckets(resources_data, errors)
    validate_queues(resources_data, errors)
    validate_streams(resources_data, errors)
    validate_tables(resources_data, errors)
    validate_lambda(resources_data, errors)
    validate_paths(resources_dir, resources_data, errors)
    validate_import(resources_dir, resources_data, errors)
    validate_prismarine(resources_dir, resources_data, errors)
    validate_authorizers(resources_data, errors)
    validate_search(resources_data, errors)


def load_schema() -> dict:
    '''Load the JSON schema from the schemas.json file.'''
    schema_path = Path(__file__).parent / 'schemas.json'
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_buckets(resources_data: dict, errors: list[str]):
    '''Validate bucket-specific rules.'''
    for bucket, details in resources_data.get('buckets', {}).items():
        if bucket == 'private' and details['public']:
            errors.append(f'Bucket \'{bucket}\' cannot be public')


def validate_queues(resources_data: dict, errors: list[str]):
    '''Validate queue-specific rules.'''
    pass


def validate_tables(resources_data: dict, errors: list[str]):
    '''Validate table-specific rules.'''
    for table_name, table in resources_data.get('tables', {}).items():
        if trigger_config := table.get('trigger'):
            # trigger_config is always an object at this point (processed by load.py)
            trigger_function = trigger_config.get('function')
            if trigger_function not in resources_data.get('functions', {}):
                errors.append(
                    f'Table {table_name}: '
                    f'Trigger function {trigger_function} must be a valid function'
                )


def validate_streams(resources_data: dict, errors: list[str]):
    '''Validate stream-specific rules.'''
    for stream, details in resources_data.get('streams', {}).items():
        for bucket in details.get('buckets', {}).values():
            if 'bucketname' not in bucket and 'extbucketarn' not in bucket:
                errors.append(f"Stream '{stream}': 'bucketname' or 'extbucketarn' is required")
                continue

            if 'bucketname' in bucket and 'extbucketarn' in bucket:
                errors.append(
                    f"Stream '{stream}': "
                    "'bucketname' and 'extbucketarn' cannot be used together"
                )
                continue

            if 'bucketname' in bucket:
                bucketname = bucket['bucketname']

                if resources_data['buckets'].get(bucketname) is None:
                    errors.append(
                        f"Stream '{stream}': '{bucketname}' must be a valid bucket"
                    )

                continue

            if 'extbucketarn' in bucket:
                if (
                    not bucket['extbucketarn'].startswith('arn:aws:s3:::') and
                    bucket['extbucketarn'] != '<overriden>'
                ):
                    errors.append(f"Stream '{stream}': 'extbucketarn' must be a valid ARN")


def validate_lambda(resources_data: dict, errors: list[str]):
    '''Validate lambda function-specific rules.'''
    lg.debug('Validating lambda functions')

    for lambda_name, details in resources_data.get('functions', {}).items():
        lg.debug(f'Validating lambda {lambda_name}')

        for bucket in details.get('buckets', []):
            if bucket not in resources_data.get('buckets', {}):
                errors.append(
                    f'Lambda {lambda_name}: '
                    f'Bucket {bucket} must be a valid bucket'
                )

                continue

        for table in details.get('tables', []):
            if table not in resources_data.get('tables', {}):
                errors.append(
                    f'Lambda {lambda_name}: '
                    f'Table {table} must be a valid table'
                )

                continue

        for poll in details.get('polls', []):
            if poll['name'] not in resources_data.get('queues', {}):
                errors.append(
                    f'Lambda {lambda_name}: '
                    f'Queue {poll["name"]} must be a valid queue'
                )

                continue

        for send in details.get('send', []):
            if send not in resources_data.get('queues', {}):
                errors.append(
                    f'Lambda {lambda_name}: '
                    f'Send {send} must be a valid queue'
                )

                continue

        for stream in details.get('streams', []):
            if stream not in resources_data.get('streams', {}):
                errors.append(
                    f'Lambda {lambda_name}: '
                    f'Stream {stream} must be a valid stream'
                )

                continue

        for collection in details.get('searches', []):
            if collection not in resources_data.get('search', {}):
                errors.append(
                    f'Lambda {lambda_name}: '
                    f'Search {collection} must be a valid search'
                )

                continue


def validate_paths(resources_dir: Path, resources_data: dict, errors: list[str]):
    '''Validate path-specific rules.'''
    for path, details in resources_data.get('paths', {}).items():
        match details.get('integration', 'lambda'):
            case 'lambda':
                validate_lambda_path(resources_data, path, details, errors)
            case 'dynamo':
                validate_dynamo_path(resources_dir, path, details, errors)
            case 'sqs':
                validate_sqs_path(resources_dir, resources_data, path, details, errors)


def validate_lambda_path(resources_data: dict, path: str, details: dict, errors: list[str]):
    '''Validate lambda path-specific rules.'''
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
    '''Validate dynamo path-specific rules.'''
    validate_request_response_templates(resources_dir, path, details, errors)


def validate_sqs_path(
    resources_dir: Path,
    resources_data: dict,
    path: str,
    details: dict,
    errors: list[str]
):
    '''Validate SQS path-specific rules.'''
    if details['queue'] not in resources_data['queues']:
        errors.append(f"SQS path '{path}' queue must be a valid queue")

    validate_request_response_templates(resources_dir, path, details, errors)


def validate_request_response_templates(
    resources_dir: Path,
    path: str,
    details: dict,
    errors: list[str]
):
    '''Validate request and response templates.'''
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
    '''Validate import-specific rules.'''
    if import_list := resources_data.get('import'):
        for import_item in import_list:
            import_path = Path(resources_dir, import_item).resolve()

            if not import_path.exists():
                errors.append(f"Import '{import_item}' must be a valid directory")


def validate_prismarine(resources_dir: Path, resources_data: dict, errors: list[str]):
    '''Validate prismarine-specific rules.'''
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
                f"Prismarine table package '{table_base}' must have a valid base directory"
            )


def validate_authorizers(resources_data: dict, errors: list[str]):
    '''Validate authorizer-specific rules.'''
    for authorizer, details in resources_data.get('authorizers', {}).items():
        present_types = ['token' in details, 'query' in details, 'headers' in details]

        if present_types.count(True) != 1:
            errors.append(f"Authorizer '{authorizer}' cannot have multiple types")

        if details['function'] not in resources_data.get('functions', {}):
            errors.append(f"Authorizer '{authorizer}' function must be a valid function")


def validate_search(resources_data: dict, errors: list[str]):
    '''Validate search-specific rules - no rules yet.'''
    search = resources_data.get('search', {})

    if not search:
        return

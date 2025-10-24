import logging as lg
from pathlib import Path
from typing import Any

from benedict import benedict
import yaml

import prismarine.prisma_common as prisma_common
import prismarine.prisma_easysam as prisma_easysam

from easysam.validate_schema import validate as validate_schema
from easysam.definitions import FatalError


IMPORT_FILE = 'easysam.yaml'

SUPPORTED_SECTIONS = [
    'tables',
    'paths',
    'functions',
    'buckets',
    'authorizers',
    'prismarine',
    'import',
    'lambda',
    'search',
]


STREAM_INTERVAL_SECONDS = 300


def resources(
    resources_dir: Path,
    pypath: list[Path],
    deploy_ctx: dict[str, str],
    errors: list[str]
) -> benedict:
    '''
    Load the resources from the resources.yaml file.

    Args:
        resources_dir: The directory containing the resources.yaml file.
        pypath: The additional Python path to use.
        deploy_ctx: The deployment context dictionary.
        errors: The list of errors.

    Returns:
        A dictionary containing the resources.
    '''

    resources = Path(resources_dir, 'resources.yaml')

    try:
        yaml.SafeLoader.add_constructor('!Conditional', conditional_constructor)
        raw_resources_data = benedict(yaml.safe_load(Path(resources).read_text(encoding='utf-8')))
    except Exception as e:
        errors.append(f'Error loading resources file {resources}: {e}')
        return benedict()

    lg.info('Resolving conditional resources')
    lg.debug(f'Deployment context: {deploy_ctx}')
    resources_data = resolve_conditionals(raw_resources_data, deploy_ctx, errors)
    lg.debug('Resources data after resolving conditionals:')
    lg.debug(resources_data.to_yaml())

    lg.info('Applying overrides')
    apply_overrides(resources_data, deploy_ctx)

    lg.info('Processing resources')
    pypath = [resources_dir] + list(pypath)
    preprocess_resources(resources_data, resources_dir, pypath, errors)

    lg.info('Validating resources')
    validate_schema(resources_dir, resources_data, errors)

    lg.info('Adding internal values')
    check_lambda_layer(resources_dir, resources_data)

    return resources_data


def prismarine_dynamo_tables(
    prefix: str,
    base: str,
    package: str,
    resources_dir: Path,
    pypath: list[Path],
    errors: list[str]
):
    lg.debug(f'Generating prismarine dynamo tables for {prefix}')

    try:
        prisma_common.set_path(pypath)
        base_dir = Path(resources_dir, base).resolve()
        cluster = prisma_common.get_cluster(base_dir, package)
        # TODO Amend prismarine to return errors
        return prisma_easysam.build_dynamo_tables(prefix, cluster)

    except Exception as e:
        lg.error(f'Error generating dynamo tables for {prefix}: {e}')
        errors.append(f'Error generating prismarine dynamo tables for {base_dir}')
        return None


def preprocess_prismarine(
    resources_data: dict,
    resources_dir: Path,
    pypath: list[Path],
    errors: list[str]
):
    prefix = resources_data['prefix']
    prisma = resources_data['prismarine']
    prisma_base = prisma.get('default-base')
    prisma_tables = prisma['tables'] or []

    for prisma_integration in prisma_tables:
        base = prisma_integration.get('base') or prisma_base
        package = prisma_integration.get('package')

        if not base:
            errors.append(f'No base found for {package}')
            continue

        if not package:
            errors.append(f'No package found for {base}')
            continue

        tables = prismarine_dynamo_tables(
            prefix, base, package, resources_dir, pypath, errors
        )

        if not tables:
            lg.warning(f'No valid tables found for {package}, continuing')
            continue

        if 'tables' not in resources_data:
            resources_data['tables'] = {}

        resources_data['tables'].update(tables)


def preprocess_lambda(
    resources_data: dict,
    resources_dir: Path,
    lambda_def: dict,
    entry_path: Path,
    entry_dir: Path,
    errors: list[str]
):
    if 'functions' not in resources_data:
        resources_data['functions'] = {}

    lambda_name = lambda_def.get('name')

    if not lambda_name:
        errors.append(f'Import file {entry_path} contains no lambda name')
        return

    if lambda_name in resources_data['functions']:
        errors.append(
            f'Import file {entry_path} contains duplicate lambda name {lambda_name}'
        )
        return

    lambda_resources = lambda_def.get('resources', {})

    if 'uri' not in lambda_resources:
        lg.debug(f'Adding uri to lambda {lambda_name}')
        lambda_resources['uri'] = Path(entry_dir).relative_to(resources_dir).as_posix()

    lg.debug(f'Adding lambda {lambda_name} to resources')
    resources_data['functions'][lambda_name] = lambda_resources
    integration = lambda_def.get('integration', {})

    if integration:
        path = integration.get('path')

        if not path:
            errors.append(f'Import file {entry_path} contains no path name')
            return

        if 'paths' not in resources_data:
            resources_data['paths'] = {}

        if path in resources_data['paths']:
            errors.append(f'Import file {entry_path} contains duplicate path {path}')
            return

        integration['function'] = lambda_name
        integration['integration'] = 'lambda'
        del integration['path']
        lg.debug(f'Adding path {path} to resources')
        resources_data['paths'][path] = integration


def preprocess_tables(
    resources_data: dict,
    table_def: dict,
    entry_path: Path,
    errors: list[str]
):
    if 'tables' not in resources_data:
        resources_data['tables'] = {}

    for table_name, table_data in table_def.items():
        if table_name in resources_data['tables']:
            errors.append(f'Import file {entry_path} contains duplicate table {table_name}')
            continue

        lg.debug(f'Adding table {table_name} to resources')
        resources_data['tables'][table_name] = table_data


def preprocess_file(
    resources_data: dict,
    resources_dir: Path,
    entry_path: Path,
    errors: list[str]
):
    lg.info(f'Processing import file {entry_path}')
    try:
        entry_dir = entry_path.parent
        entry_data = yaml.safe_load(entry_path.read_text(encoding='utf-8'))
    except Exception as e:
        errors.append(f'Error loading import file {entry_path}: {e}')
        return

    if not all(key in ['lambda', 'import', 'tables'] for key in entry_data.keys()):
        errors.append(f'Import file {entry_path} contains unexpected sections')
        return

    if lambda_def := entry_data.get('lambda'):
        preprocess_lambda(
            resources_data, resources_dir, lambda_def, entry_path, entry_dir, errors
        )

    if tables_def := entry_data.get('tables'):
        preprocess_tables(resources_data, tables_def, entry_path, errors)

    if local_import_def := entry_data.get('import'):
        for import_file in local_import_def:
            import_path = Path(entry_dir, import_file)
            preprocess_file(resources_data, resources_dir, import_path, errors)


def preprocess_imports(resources_data: dict, resources_dir: Path, errors: list[str]):
    for import_dir_str in resources_data.get('import', []):
        import_dir = Path(resources_dir, import_dir_str)
        lg.info(f'Processing import directory {import_dir}')

        if not import_dir.exists():
            errors.append(f'Import directory {import_dir} not found')
            continue

        for entry_path in import_dir.glob(f'**/{IMPORT_FILE}'):
            preprocess_file(resources_data, resources_dir, entry_path, errors)


def process_default_functions(resources_data: dict, errors: list[str]):
    def transform_lambda_poll(poll: str | dict):
        if isinstance(poll, str):
            return {'name': poll}
        else:
            return poll

    if 'functions' in resources_data:
        for name, function in resources_data['functions'].items():
            lg.debug(f'Processing function {name}')

            if polls := function.get('polls'):
                function['polls'] = [transform_lambda_poll(poll) for poll in polls]

            if 'searches' in function:
                if not function['searches']:
                    function['searches'] = ['searchable']


def process_default_streams(resources_data: dict, errors: list[str]):
    new_streams = {}

    for stream_name, stream in resources_data.get('streams', {}).items():
        if 'buckets' in stream and 'bucketname' in stream:
            errors.append(f'Stream {stream} cannot have both buckets and bucketname')
            continue

        if 'bucketname' in stream:
            stream['buckets'] = {
                'private': {
                    'bucketname': stream['bucketname'],
                    'bucketprefix': stream.get('bucketprefix', ''),
                    'intervalinseconds': stream.get('intervalinseconds')
                }
            }

            del stream['bucketname']

            if 'bucketprefix' in stream:
                del stream['bucketprefix']

            if 'intervalinseconds' in stream:
                del stream['intervalinseconds']

        for bucket in stream.get('buckets', {}).values():
            if 'bucketprefix' not in bucket:
                bucket['bucketprefix'] = ''

            if 'intervalinseconds' not in bucket:
                bucket['intervalinseconds'] = STREAM_INTERVAL_SECONDS

        new_streams[stream_name] = stream

    if new_streams:
        resources_data['streams'] = new_streams


def process_default_paths(resources_data: dict, errors: list[str]):
    for path in resources_data.get('paths', {}).values():
        if 'integration' not in path:
            path['integration'] = 'lambda'

        match path.get('integration'):
            case 'dynamo':
                path['action'] = path.get('action', 'GetItem')
            case 'sqs':
                path['method'] = path.get('method', 'post')
            case 'lambda':
                if 'greedy' not in path:
                    path['greedy'] = True


def process_default_tables(resources_data: dict, errors: list[str]):
    for table_name, table in resources_data.get('tables', {}).items():
        if trigger_config := table.get('trigger'):
            # If trigger is a string, convert to object
            if isinstance(trigger_config, str):
                trigger_config = {'function': trigger_config}
                table['trigger'] = trigger_config

            # Set default viewtype to 'new-and-old'
            if 'viewtype' not in trigger_config:
                trigger_config['viewtype'] = 'new-and-old'

            # Set default startingposition to 'latest'
            if 'startingposition' not in trigger_config:
                trigger_config['startingposition'] = 'latest'


def preprocess_defaults(resources_data: dict, errors: list[str]):
    process_default_searches(resources_data, errors)
    process_default_functions(resources_data, errors)
    process_default_streams(resources_data, errors)
    process_default_tables(resources_data, errors)
    process_default_paths(resources_data, errors)


def preprocess_resources(
    resources_data: dict,
    resources_dir: Path,
    pypath: list[Path],
    errors: list[str]
):
    def sort_dict(d):
        return dict(sorted(d.items(), key=lambda x: x[0]))

    if 'prismarine' in resources_data:
        preprocess_prismarine(resources_data, resources_dir, pypath, errors)

    if 'import' in resources_data:
        preprocess_imports(resources_data, resources_dir, errors)

    preprocess_defaults(resources_data, errors)

    for section in SUPPORTED_SECTIONS:
        if section in resources_data:
            if isinstance(resources_data[section], dict):
                resources_data[section] = sort_dict(resources_data[section])
            elif isinstance(resources_data[section], list):
                resources_data[section] = sorted(resources_data[section])

    resources_data = sort_dict(resources_data)


def check_lambda_layer(resources_dir: Path, resources_data: dict):
    thirdparty_dir = Path(resources_dir, 'thirdparty')
    resources_data['enable_lambda_layer'] = thirdparty_dir.exists()


class Conditional(yaml.YAMLObject):
    def __init__(self, key, environment='any', region='any'):
        self.key = key
        self.environment = environment
        self.region = region

    def __repr__(self):
        fields = [
            f'key={self.key}',
            f'environment={self.environment}',
            f'region={self.region}',
        ]

        return f'Conditional({", ".join(fields)})'


def conditional_constructor(loader, node):
    mapping = loader.construct_mapping(node)

    if 'key' not in mapping:
        raise ValueError('All !Conditional keys must have a key')

    attributes = {'key': mapping['key']}

    if 'environment' in mapping:
        attributes['environment'] = mapping['environment']

    if 'region' in mapping:
        attributes['region'] = mapping['region']

    return Conditional(**attributes)


def check_condition(
    condition: str,
    value: str,
    deploy_ctx: dict[str, str],
    errors: list[str]
):
    if value == 'any':
        return True

    context_value = deploy_ctx.get(condition)

    if context_value is None:
        errors.append(
            f'Fatal error: Condition "{condition}" not found in deployment context. '
            f'Unable to resolve conditional resources. Consider adding "--{condition}"'
        )

        raise FatalError(errors)

    negate = value.startswith('~')
    value = value.lstrip('~')

    lg.info(
        f'Checking condition "{condition}" '
        f'{value} (condition) == {context_value} (context) (negate={negate})'
    )

    include = value == context_value
    result = include if not negate else not include
    return result


def resolve_conditionals(
    resources_data: dict,
    deploy_ctx: dict[str, str],
    errors: list[str]
):
    resolved = benedict()

    for key, value in resources_data.items():
        if isinstance(value, dict):
            resolved_value = resolve_conditionals(value, deploy_ctx, errors)
        else:
            resolved_value = value

        if isinstance(key, Conditional):
            include = all([
                check_condition('environment', key.environment, deploy_ctx, errors),
                check_condition('target_region', key.region, deploy_ctx, errors),
            ])

            if include:
                resolved[key.key] = resolved_value
        else:
            resolved[key] = resolved_value

    return resolved


def apply_overrides(resources_data: dict, deploy_ctx: dict[str, Any]):
    if 'overrides' in deploy_ctx:
        for override_path, override_value in deploy_ctx['overrides'].items():
            key = override_path.replace('/', '.')
            lg.info(f'Applying override: {key} = {override_value}')
            resources_data[key] = override_value


def process_default_searches(resources_data: dict, errors: list[str]):
    lg.debug('Processing default searches')

    if 'search' in resources_data:
        lg.debug('Search is defined')

        if not resources_data['search']:
            lg.debug('Search is empty, adding searchable')
            resources_data['search'] = {
                'searchable': {}
            }

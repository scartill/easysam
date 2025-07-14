# SAM Template Generator and Swagger support for API Gateway

from pathlib import Path
import logging as lg
from typing import Any

from jinja2 import Environment, FileSystemLoader
import yaml

import prismarine.prisma_common as prisma_common
import prismarine.prisma_easysam as prisma_easysam

from easysam.validate import validate
from easysam.prismarine import generate as generate_prismarine_clients


type ProcessingResult = tuple[dict[str, Any], list[str]]


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
]


def write_result(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    sane_text = '\n'.join(line for line in text.splitlines() if line and line.strip())
    Path(path).write_text(sane_text)


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
        entry_data = yaml.safe_load(entry_path.read_text())
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

    for section in SUPPORTED_SECTIONS:
        if section in resources_data:
            if isinstance(resources_data[section], dict):
                resources_data[section] = sort_dict(resources_data[section])
            elif isinstance(resources_data[section], list):
                resources_data[section] = sorted(resources_data[section])

    resources_data = sort_dict(resources_data)


def generate(resources_dir: Path, pypath: list[Path], preprocess_only: bool) -> ProcessingResult:
    '''
    Generate a SAM template from a directory.

    Args:
        resources_dir: The directory containing the resources.
        pypath: The Python path to use.
        preprocess_only: Whether to return the processed resources
            without generating a template.

    Returns:
        A tuple containing the processed resources and any errors as a list.
    '''

    errors = []
    pypath = [resources_dir] + list(pypath)
    resources = Path(resources_dir, 'resources.yaml')

    try:
        resources_data = yaml.safe_load(Path(resources).read_text())
    except Exception as e:
        errors.append(f'Error loading resources file {resources}: {e}')
        return {}, errors

    lg.info('Processing resources')
    preprocess_resources(resources_data, resources_dir, pypath, errors)

    lg.info('Validating resources')
    validate(resources_data, errors)

    if preprocess_only or errors:
        return resources_data, errors

    lg.debug('Resources processed:\n' + yaml.dump(resources_data, indent=4))

    try:
        build_dir = Path(resources_dir, 'build')
        swagger = Path(build_dir, 'swagger.yaml')
        template = Path(resources_dir, 'template.yml')

        loader = FileSystemLoader(searchpath=[
            str(Path(__file__).parent.resolve()),
            str(resources_dir.resolve()),
        ])

        jenv = Environment(loader=loader)
        swagger_template = jenv.get_template('swagger.j2')
        sam_template = jenv.get_template('template.j2')
        swagger_output = swagger_template.render(resources_data)
        sam_output = sam_template.render(resources_data)
        write_result(swagger, swagger_output)
        lg.info(f'Swagger file generated: {swagger}')
        write_result(template, sam_output)
        lg.info(f'SAM template generated: {template}')

    except Exception as e:
        errors.append(f'Error generating template: {e}')
        return resources_data, errors

    if 'prismarine' in resources_data:
        lg.info('Generating prismarine clients')
        generate_prismarine_clients(resources_dir, resources_data, errors)

    return resources_data, errors

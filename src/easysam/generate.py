# SAM Template Generator and Swagger support for API Gateway

from pathlib import Path
import logging as lg

from jinja2 import Environment, FileSystemLoader
import yaml
import click

import prismarine.prisma_common as prisma_common
import prismarine.prisma_easysam as prisma_easysam

from easysam.prismarine import generate as generate_prismarine_clients


IMPORT_FILE = 'easysam.yaml'


def write_result(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    sane_text = '\n'.join(line for line in text.splitlines() if line and line.strip())
    Path(path).write_text(sane_text)


def prismarine_dynamo_tables(prefix, base, package, resources_dir, path):
    lg.debug(f'Generating prismarine dynamo tables for {prefix}')

    try:
        prisma_common.set_path(path)
        base_dir = Path(resources_dir, base).resolve()
        cluster = prisma_common.get_cluster(base_dir, package)
        return prisma_easysam.build_dynamo_tables(prefix, cluster)
    except Exception as e:
        lg.error(f'Error generating dynamo tables for {prefix}: {e}')
        raise UserWarning(f'Error generating prismarine dynamo tables for {base_dir}')


def preprocess_prismarine(resources_data, resources_dir, path):
    prefix = resources_data['prefix']
    prisma = resources_data['prismarine']
    prisma_base = prisma.get('default-base')
    prisma_tables = prisma['tables'] or []

    for prisma_integration in prisma_tables:
        base = prisma_integration.get('base') or prisma_base
        package = prisma_integration.get('package')

        if not base:
            raise UserWarning(f'No base found for {package}')

        if not package:
            raise UserWarning(f'No package found for {base}')

        tables = prismarine_dynamo_tables(prefix, base, package, resources_dir, path)

        if 'tables' not in resources_data:
            resources_data['tables'] = {}

        resources_data['tables'].update(tables)


def preprocess_lambda(resources_data, resources_dir, lambda_def, entry_path, entry_dir):
    if 'functions' not in resources_data:
        resources_data['functions'] = {}

    lambda_name = lambda_def.get('name')

    if not lambda_name:
        raise UserWarning(f'Import file {entry_path} contains no lambda name')

    if lambda_name in resources_data['functions']:
        raise UserWarning(
            f'Import file {entry_path} contains duplicate lambda name {lambda_name}'
        )

    lambda_resources = lambda_def.get('resources', {})

    if 'uri' not in lambda_resources:
        lambda_resources['uri'] = Path(entry_dir).relative_to(resources_dir).as_posix()

    lg.debug(f'Adding lambda {lambda_name} to resources')
    resources_data['functions'][lambda_name] = lambda_resources
    integration = lambda_def.get('integration', {})

    if integration:
        path = integration.get('path')

        if not path:
            raise UserWarning(f'Import file {entry_path} contains no path name')

        if 'paths' not in resources_data:
            resources_data['paths'] = {}

        if path in resources_data['paths']:
            raise UserWarning(f'Import file {entry_path} contains duplicate path {path}')

        integration['function'] = lambda_name
        del integration['path']
        lg.debug(f'Adding path {path} to resources')
        resources_data['paths'][path] = integration


def preprocess_tables(resources_data: dict, table_def: dict, entry_path: Path):
    if 'tables' not in resources_data:
        resources_data['tables'] = {}

    for table_name, table_data in table_def.items():
        if table_name in resources_data['tables']:
            raise UserWarning(f'Import file {entry_path} contains duplicate table {table_name}')

        lg.debug(f'Adding table {table_name} to resources')
        resources_data['tables'][table_name] = table_data


def preprocess_file(resources_data: dict, resources_dir: Path, entry_path: Path):
    entry_dir = entry_path.parent
    entry_data = yaml.safe_load(entry_path.read_text())
    lg.info(f'Processing import file {entry_path}')

    if not all(key in ['lambda', 'import', 'tables'] for key in entry_data.keys()):
        raise UserWarning(f'Import file {entry_path} contains unexpected sections')

    if lambda_def := entry_data.get('lambda'):
        preprocess_lambda(resources_data, resources_dir, lambda_def, entry_path, entry_dir)

    if tables_def := entry_data.get('tables'):
        preprocess_tables(resources_data, tables_def, entry_path)

    if local_import_def := entry_data.get('import'):
        for import_file in local_import_def:
            import_path = Path(entry_dir, import_file)
            preprocess_file(resources_data, resources_dir, import_path)


def preprocess_imports(resources_data: dict, resources_dir: Path):
    for import_dir_str in resources_data.get('import', []):
        import_dir = Path(resources_dir, import_dir_str)
        lg.info(f'Processing import directory {import_dir}')

        if not import_dir.exists():
            raise UserWarning(f'Import directory {import_dir} not found')

        for entry_path in import_dir.glob(f'**/{IMPORT_FILE}'):
            preprocess_file(resources_data, resources_dir, entry_path)


def preprocess_resources(resources_data, resources_dir, path):
    def sort_dict(d):
        return dict(sorted(d.items(), key=lambda x: x[0]))

    if 'prismarine' in resources_data:
        preprocess_prismarine(resources_data, resources_dir, path)

    if 'import' in resources_data:
        preprocess_imports(resources_data, resources_dir)

    for section in ['tables', 'paths', 'functions', 'buckets', 'authorizers']:
        if section in resources_data:
            resources_data[section] = sort_dict(resources_data[section])

    resources_data = sort_dict(resources_data)


def generate(directory, path, preprocess_only):
    resources_dir = Path(directory)
    path = [resources_dir] + list(path)
    resources = Path(resources_dir, 'resources.yaml')
    build_dir = Path(resources_dir, 'build')
    swagger = Path(build_dir, 'swagger.yaml')
    template = Path(resources_dir, 'template.yml')
    resources_data = yaml.safe_load(Path(resources).read_text())

    lg.info('Processing resources')
    preprocess_resources(resources_data, resources_dir, path)

    if preprocess_only:
        click.echo(yaml.dump(resources_data, indent=4))
        return

    lg.debug('Resources processed:\n' + yaml.dump(resources_data, indent=4))

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

    if 'prismarine' in resources_data:
        lg.info('Generating prismarine clients')
        generate_prismarine_clients(resources_dir, resources_data)

    return resources_data

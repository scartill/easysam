import logging as lg
from pathlib import Path

import click
import rich
from benedict import benedict

from easysam.commondep import commondep
from easysam.definitions import FatalError
from easysam.load import resources as load_resources
from easysam.validate_cloud import validate as validate_cloud


@click.group(help='Inspect the application for debugging purposes')
@click.pass_obj
def inspect(obj):
    pass


@inspect.command(name='common-deps', help='Inspect a lambda function')
@click.option(
    '--common-dir', type=str, default='common',
    help='The directory containing the common dependencies'
)
@click.argument(
    'lambda-dir', type=click.Path(exists=True)
)
def common_deps(common_dir, lambda_dir):
    common_dir = Path(common_dir)
    lambda_dir = Path(lambda_dir)

    deps = commondep(common_dir, lambda_dir)
    click.echo('Dependencies:')

    for dep in deps:
        click.echo(f'* {dep}')


@inspect.command(help='Validate the resources.yaml file')
@click.pass_obj
@click.option(
    '--path', multiple=True, help='Add a path to the Python path'
)
@click.option(
    '--select', type=str,
    help='Select a specific resource to render after the schema is validated. '
         'Uses the keystring syntax to select the resource'
)
@click.argument('directory', type=click.Path(exists=True))
def schema(obj, directory, path, select):
    errors = []
    directory = Path(directory)
    pypath = [Path(p) for p in path]
    deploy_ctx = obj.get('deploy_ctx', {})

    try:
        resources_data = load_resources(
            directory, pypath, deploy_ctx, errors
        )

    except FatalError as e:
        lg.error('There were fatal errors. Interrupting schema validation.')
        errors = e.errors

    if errors:
        rich.print(f'[red]There were {len(errors)} validation errors.[/red]')
        for error in errors:
            rich.print(f'[red]{error}[/red]')

    else:
        slice = resources_data.get(select) if select else resources_data

        if isinstance(slice, benedict):
            rich.print(slice.to_yaml())

        rich.print('[green]No validation errors found.[/green]')


@inspect.command(help='Inspect the resources in-depth')
@click.pass_obj
@click.option('--path', multiple=True)
@click.argument('directory', type=click.Path(exists=True))
def cloud(obj, directory, path):
    directory = Path(directory)
    pypath = [Path(p) for p in path]
    errors = []
    deploy_ctx = obj.get('deploy_ctx', {})

    if 'environment' not in deploy_ctx:
        raise click.UsageError('Environment is required for cloud inspection')

    environment = deploy_ctx['environment']

    try:
        resources_data = load_resources(
            directory, pypath, deploy_ctx, errors
        )

        if errors:
            rich.print(
                '[red]There were validation errors.[/red] '
                'Please run `easysam inspect schema` to fix them.'
            )

            return

        lg.info(f"Validating cloud resources for '{environment}'")
        validate_cloud(obj, resources_data, environment, errors)

    except FatalError as e:
        lg.error('There were fatal errors. Interrupting inspection.')
        errors = e.errors

    if errors:
        for error in errors:
            click.echo(error)

        if len(errors) > 1:
            rich.print(f'[red]There were {len(errors)} errors.[/red]')
        else:
            rich.print('[red]There was an error.[/red]')
    else:
        rich.print('[green]Cloud resources are ready.[/green]')

import logging as lg
from pathlib import Path

import click
import rich
from benedict import benedict

from easysam.commondep import commondep
from easysam.generate import load_resources
from easysam.validate_cloud import validate as validate_cloud


@click.group(help='Inspect the application for debugging purposes')
@click.pass_obj
@click.option('--environment', type=str)
@click.option('--target-region', type=str)
def inspect(obj, environment, target_region):
    deploy_ctx = obj['deploy_ctx']

    if environment:
        deploy_ctx['environment'] = environment

    if target_region:
        deploy_ctx['region'] = target_region


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
    directory = Path(directory)
    pypath = [Path(p) for p in path]
    errors = []
    deploy_ctx = obj['deploy_ctx']
    context_file = obj.get('context_file')
    resources_data = load_resources(directory, pypath, deploy_ctx, context_file, errors)

    if errors:
        rich.print(f'[red]There were {len(errors)} validation errors.[/red]')
        for error in errors:
            rich.print(f'[red]{error}[/red]')

    else:
        slice = resources_data.get(select) if select else resources_data

        if isinstance(slice, benedict):
            rich.print(slice.to_yaml())

        rich.print('[green]No validation errors found.[/green]')


@inspect.command(help='Inspect the resources.yaml file in-depth')
@click.pass_obj
@click.option('--path', multiple=True)
@click.option('--environment', type=str, required=True)
@click.argument('directory', type=click.Path(exists=True))
def cloud(obj, directory, path, environment):
    directory = Path(directory)
    pypath = [Path(p) for p in path]
    errors = []

    if 'environment' not in obj:
        raise click.UsageError('Environment is required for cloud inspection')

    deploy_ctx = {
        'environment': environment,
    }

    context_file = obj.get('context_file')
    resources_data = load_resources(directory, pypath, deploy_ctx, context_file, errors)

    if errors:
        rich.print(
            '[red]There were validation errors.[/red] '
            'Please run `easysam inspect schema` to fix them.'
        )

        return

    lg.info(f"Validating cloud resources for {environment}")
    validate_cloud(obj, resources_data, environment, errors)

    if errors:
        for error in errors:
            click.echo(error)

        if len(errors) > 1:
            rich.print(f'[red]There were {len(errors)} errors.[/red]')
        else:
            rich.print('[red]There was an error.[/red]')
    else:
        rich.print('[green]Cloud resources are ready.[/green]')

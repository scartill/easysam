import logging as lg
from pathlib import Path

import yaml
import click
import rich

from easysam.commondep import commondep
from easysam.generate import load_resources
from easysam.validate_cloud import validate as validate_cloud


@click.group(help='Inspect the application for debugging purposes')
def inspect():
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
@click.option('--path', multiple=True)
@click.argument('directory', type=click.Path(exists=True))
def schema(directory, path):
    directory = Path(directory)
    pypath = [Path(p) for p in path]
    errors = []
    resources_data = load_resources(directory, pypath, {}, errors)

    if errors:
        rich.print(f'[red]There were {len(errors)} validation errors.[/red]')
        for error in errors:
            rich.print(f'[red]{error}[/red]')

    else:
        rich.print(yaml.dump(resources_data, indent=4))
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
    resources_data = load_resources(directory, pypath, {}, errors)

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

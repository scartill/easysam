from pathlib import Path

import click

from easysam.commondep import commondep


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

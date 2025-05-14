import click
import logging as lg
import shutil
from pathlib import Path


from easysam.generate import generate
from easysam.commondep import commondep


@click.command(name='deploy')
@click.argument('directory', type=click.Path(exists=True))
def deploy_cmd(directory):
    resources = generate(directory, [], False)
    deploy(directory, resources)


def deploy(directory, resources):
    lg.info(f'Deploying SAM template from {directory}')
    remove_common_dependencies(directory)
    copy_common_dependencies(directory, resources)


def common_dep_dir(directory):
    return Path(directory, 'common')


def remove_common_dependencies(directory):
    lg.info(f'Removing common dependencies from {directory}')
    common = common_dep_dir(directory)

    if common.exists():
        lg.info(f'Removing {common}')
        shutil.rmtree(common)


def copy_common_dependencies(directory, resources):
    lg.info(f'Copying common dependencies to {directory}')
    common = common_dep_dir(directory)

    if 'functions' not in resources:
        lg.warning('No functions found in resources')
        return

    for lambda_function in resources['functions']:
        deps = commondep(common, lambda_function['uri'])

        for dep in deps:
            lg.info(f'Copying {dep} to {common}')
            shutil.copy(dep, common)

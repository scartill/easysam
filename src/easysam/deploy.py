import click
import logging as lg
import shutil
from pathlib import Path
import yaml
import subprocess

from easysam.generate import generate
from easysam.commondep import commondep


@click.command(name='deploy')
@click.pass_obj
@click.argument('directory', type=click.Path(exists=True))
def deploy_cmd(obj, directory):
    directory = Path(directory)
    resources = generate(directory, [], False)
    click.echo(yaml.dump(resources, default_flow_style=False))
    deploy(obj, directory, resources)


def deploy(cliparams, directory, resources):
    lg.info(f'Deploying SAM template from {directory}')
    remove_common_dependencies(directory)
    copy_common_dependencies(directory, resources)
    sam_build(cliparams, directory)


def sam_build(cliparams, directory):
    lg.info(f'Building SAM template from {directory}')
    params = ['sam', 'build']

    if cliparams.get('verbose'):
        params.append('--debug')

    subprocess.run(params, cwd=directory.resolve())


def common_dep_dir(directory):
    return Path(directory, 'common')


def remove_common_dependencies(directory):
    lg.info(f'Removing common dependencies from {directory}')
    backend = Path(directory, 'backend')

    for common_dep in backend.glob('common/*'):
        lg.info(f'Removing {common_dep}')
        shutil.rmtree(common_dep)


def copy_common_dependencies(directory, resources):
    lg.info(f'Copying common dependencies to {directory}')
    common = common_dep_dir(directory)

    if 'functions' not in resources:
        lg.warning('No functions found in resources')
        return

    for lambda_function in resources['functions'].values():
        lambda_path = Path(directory, lambda_function['uri'])
        deps = commondep(common, lambda_path)

        for dep in deps:
            dep_path = Path(common, dep)
            print(dep_path)
            print(lambda_path)

            if dep_path.is_dir():
                lg.info(f'Copying {dep_path} directory to {lambda_path}')
                shutil.copytree(dep_path, lambda_path)
            else:
                dep_filepath = dep_path.with_suffix('.py')
                lg.info(f'Copying {dep_filepath} file to {lambda_path}')
                shutil.copy(dep_filepath, lambda_path)

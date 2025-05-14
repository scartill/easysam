import click
import logging as lg
import shutil
from pathlib import Path
import subprocess

from easysam.generate import generate
from easysam.commondep import commondep


@click.command(name='deploy')
@click.pass_obj
@click.option('--region', type=str, help='AWS region')
@click.option('--tag', type=str, multiple=True, help='AWS tags', required=True)
@click.argument('directory', type=click.Path(exists=True))
@click.argument('stack', type=str)
def deploy_cmd(obj, directory, stack, **kwargs):
    obj.update(kwargs)
    directory = Path(directory)
    resources = generate(directory, [], False)
    deploy(obj, directory, resources, stack)


def deploy(cliparams, directory, resources, stack):
    lg.info(f'Deploying SAM template from {directory}')
    remove_common_dependencies(directory)
    copy_common_dependencies(directory, resources)
    sam_build(cliparams, directory)
    sam_deploy(cliparams, directory, stack)


def sam_build(cliparams, directory):
    lg.info(f'Building SAM template from {directory}')
    build_params = ['sam.cmd', 'build']

    if cliparams.get('verbose'):
        build_params.append('--debug')

    subprocess.run(build_params, cwd=directory.resolve(), text=True)


def sam_deploy(cliparams, directory, aws_stack):
    lg.info(f'Deploying SAM template from {directory} to {aws_stack}')

    deploy_params = [
        'sam.cmd',
        'deploy',
        '--parameter-overrides', f'ParameterKey=Stage,ParameterValue={aws_stack}',
        '--stack-name', aws_stack,
        '--no-fail-on-empty-changeset',
        '--no-confirm-changeset',
        '--resolve-s3',
        '--capabilities', 'CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'
    ]

    aws_tags = cliparams.get('tag')
    lg.info(f'Using AWS tags: {aws_tags}')
    aws_tag_string = ' '.join(aws_tags)
    lg.debug(f'AWS tag string: {aws_tag_string}')
    deploy_params.extend(['--tags', aws_tag_string])

    if region := cliparams.get('region'):
        deploy_params.extend(['--region', region])

    if cliparams.get('verbose'):
        deploy_params.append('--debug')

    result = subprocess.run(deploy_params, cwd=directory.resolve(), text=True)

    if result.returncode != 0:
        lg.error(f'Error deploying SAM template: {result.stderr}')
    else:
        lg.info(f'Successfully deployed SAM template: {result.stdout}')


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

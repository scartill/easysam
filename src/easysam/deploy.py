import logging as lg
import shutil
from pathlib import Path
import subprocess

import click


from easysam.generate import generate
from easysam.commondep import commondep
import easysam.utils as u

SAM_CLI_VERSION = '1.138.0'
PIP_VERSION = '25.1.1'


@click.command(name='deploy')
@click.pass_obj
@click.option('--region', type=str, help='AWS region')
@click.option('--tag', type=str, multiple=True, help='AWS tags', required=True)
@click.option('--dry-run', is_flag=True, help='Dry run the deployment')
@click.option('--sam-tool', type=str, help='Path to the SAM CLI', default='sam')
@click.argument('directory', type=click.Path(exists=True))
@click.argument('stack', type=str)
def deploy_cmd(obj, directory, stack, **kwargs):
    obj.update(kwargs)
    directory = Path(directory)
    resources = generate(directory, [], False)
    deploy(obj, directory, resources, stack)


@click.command(name='delete')
@click.pass_obj
@click.option('--force', is_flag=True, help='Force delete the stack')
@click.option('--region', type=str, help='AWS region')
@click.argument('stack', type=str)
def delete_cmd(obj, stack, force, **kwargs):
    obj.update(kwargs)
    delete(obj, stack, force)


def deploy(cliparams, directory, resources, stack):
    lg.info(f'Deploying SAM template from {directory}')
    check_pip_version(cliparams)
    check_sam_cli_version(cliparams)
    remove_common_dependencies(directory)
    copy_common_dependencies(directory, resources)
    sam_build(cliparams, directory)
    sam_deploy(cliparams, directory, stack)
    remove_common_dependencies(directory)


def delete(cliparams, stack, force):
    lg.info(f'Deleting SAM template from {stack}')
    cf = u.get_aws_client('cloudformation', cliparams)
    mode = 'FORCE_DELETE_STACK' if force else 'STANDARD'
    cf.delete_stack(StackName=stack, DeletionMode=mode)  # type: ignore


def check_pip_version(cliparams):
    lg.info('Checking pip version')

    try:
        lg.debug(f'Running command: {" ".join(["pip", "--version"])}')
        pip_version = subprocess.check_output(['pip', '--version']).decode('utf-8')

        if pip_version < PIP_VERSION:
            raise UserWarning(f'pip version must be {PIP_VERSION} or higher')

    except Exception as e:
        raise UserWarning('pip not found') from e


def check_sam_cli_version(cliparams):
    lg.info('Checking SAM CLI version')
    sam_path = cliparams['sam_tool']

    try:
        lg.debug(f'Running command: {" ".join([sam_path, "--version"])}')
        sam_version = subprocess.check_output([sam_path, '--version']).decode('utf-8')

        if sam_version < SAM_CLI_VERSION:
            raise UserWarning(f'SAM CLI version must be {SAM_CLI_VERSION} or higher')

    except Exception as e:
        raise UserWarning('SAM CLI not found') from e


def sam_build(cliparams, directory):
    lg.info(f'Building SAM template from {directory}')
    build_params = [cliparams['sam_tool'], 'build']

    if cliparams.get('verbose'):
        build_params.append('--debug')

    if cliparams['dry_run']:
        lg.info(f'Would run: {" ".join(build_params)}')
        return

    subprocess.run(build_params, cwd=directory.resolve(), text=True)


def sam_deploy(cliparams, directory, aws_stack):
    lg.info(f'Deploying SAM template from {directory} to {aws_stack}')

    deploy_params = [
        cliparams['sam_tool'],
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

    if cliparams['dry_run']:
        lg.info(f'Would run: {" ".join(deploy_params)}')
        return

    if cliparams.get('aws_profile'):
        lg.info(f'Using AWS profile: {cliparams["aws_profile"]}')
        deploy_params.extend(['--profile', cliparams['aws_profile']])

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

    for common_dep in backend.glob('**/common'):
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
        lambda_common_path = Path(lambda_path, 'common')
        lambda_common_path.mkdir(parents=True, exist_ok=True)
        deps = commondep(common, lambda_path)

        for dep in deps:
            dep_path = Path(common, dep)

            if dep_path.is_dir():
                lg.info(f'Copying {dep_path} directory to {lambda_common_path}')
                lambda_common_dep_path = Path(lambda_common_path, dep_path.name)
                shutil.copytree(dep_path, lambda_common_dep_path)
            else:
                dep_filepath = dep_path.with_suffix('.py')
                lg.info(f'Copying {dep_filepath} file to {lambda_common_path}')
                lambda_common_filepath = Path(lambda_common_path, dep_filepath.name)
                shutil.copy(dep_filepath, lambda_common_filepath)

import logging as lg
import shutil
from pathlib import Path
import subprocess

from easysam.generate import generate
from easysam.commondep import commondep
import easysam.utils as u

SAM_CLI_VERSION = '1.138.0'
PIP_VERSION = '25.1.1'


def deploy(cliparams, directory, stack):
    resources = generate(directory, [], False)

    lg.info(f'Deploying SAM template from {directory}')
    check_pip_version(cliparams)
    check_sam_cli_version(cliparams)
    remove_common_dependencies(directory)
    copy_common_dependencies(directory, resources)
    sam_build(cliparams, directory)
    sam_deploy(cliparams, directory, stack)

    if not cliparams.get('no_cleanup'):
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
    sam_tool = cliparams['sam_tool']
    sam_params = sam_tool.split(' ')
    sam_params.append('--version')

    try:
        lg.debug(f'Running command: {" ".join(sam_params)}')
        sam_version = subprocess.check_output(sam_params).decode('utf-8')
        lg.debug(f'SAM CLI version: {sam_version}')

        if sam_version < SAM_CLI_VERSION:
            raise UserWarning(f'SAM CLI version must be {SAM_CLI_VERSION} or higher')

    except Exception as e:
        raise UserWarning(f'SAM CLI not found. Error: {e}') from e


def sam_build(cliparams, directory):
    lg.info(f'Building SAM template from {directory}')
    sam_tool = cliparams['sam_tool']
    sam_params = sam_tool.split(' ')
    sam_params.append('build')

    if cliparams.get('verbose'):
        sam_params.append('--debug')

    if cliparams['dry_run']:
        lg.info(f'Would run: {" ".join(sam_params)}')
        return

    lg.debug(f'Running command: {" ".join(sam_params)}')
    subprocess.run(sam_params, cwd=directory.resolve(), text=True, check=True)
    lg.info('Successfully built SAM template')


def sam_deploy(cliparams, directory, aws_stack):
    lg.info(f'Deploying SAM template from {directory} to {aws_stack}')
    sam_tool = cliparams['sam_tool']
    sam_params = sam_tool.split(' ')

    sam_params.extend([
        'deploy',
        '--parameter-overrides', f'ParameterKey=Stage,ParameterValue={aws_stack}',
        '--stack-name', aws_stack,
        '--no-fail-on-empty-changeset',
        '--no-confirm-changeset',
        '--resolve-s3',
        '--capabilities', 'CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'
    ])

    aws_tags = cliparams.get('tag')
    lg.info(f'Using AWS tags: {aws_tags}')
    aws_tag_string = ' '.join(aws_tags)
    lg.debug(f'AWS tag string: {aws_tag_string}')
    sam_params.extend(['--tags', aws_tag_string])

    if region := cliparams.get('region'):
        sam_params.extend(['--region', region])

    if cliparams.get('verbose'):
        sam_params.append('--debug')

    if cliparams['dry_run']:
        lg.info(f'Would run: {" ".join(sam_params)}')
        return

    if cliparams.get('aws_profile'):
        lg.info(f'Using AWS profile: {cliparams["aws_profile"]}')
        sam_params.extend(['--profile', cliparams['aws_profile']])

    lg.debug(f'Running command: {" ".join(sam_params)}')
    subprocess.run(sam_params, cwd=directory.resolve(), text=True, check=True)
    lg.info('Successfully deployed SAM template')


def common_dep_dir(directory):
    return Path(directory, 'common')


def remove_common_dependencies(directory):
    lg.info(f'Removing common dependencies from {directory}')
    backend = Path(directory, 'backend')

    for common_dep in backend.glob('**/common'):
        lg.debug(f'Removing {common_dep}')
        shutil.rmtree(common_dep)


def copy_common_dependencies(directory, resources):
    lg.info(f'Copying common dependencies to {directory}')
    common = common_dep_dir(directory)

    if 'functions' not in resources:
        lg.warning('No functions found in resources')
        return

    for lambda_name, lambda_function in resources['functions'].items():
        lambda_path = Path(directory, lambda_function['uri'])
        lambda_common_path = Path(lambda_path, 'common')
        lambda_common_path.mkdir(parents=True, exist_ok=True)
        deps = commondep(common, lambda_path)

        lg.info(f'Lambda {lambda_name} has {len(deps)} common dependencies')
        lg.debug(f'Dependencies: {" ".join(deps)}')

        for dep in deps:
            dep_path = Path(common, dep)

            if dep_path.is_dir():
                lg.debug(f'Copying {dep_path} directory to {lambda_common_path}')
                lambda_common_dep_path = Path(lambda_common_path, dep_path.name)
                shutil.copytree(dep_path, lambda_common_dep_path)
            else:
                dep_filepath = dep_path.with_suffix('.py')
                lg.debug(f'Copying {dep_filepath} file to {lambda_common_path}')
                lambda_common_filepath = Path(lambda_common_path, dep_filepath.name)
                shutil.copy(dep_filepath, lambda_common_filepath)

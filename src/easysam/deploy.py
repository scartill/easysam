import logging as lg
import json
import time
import shutil
from pathlib import Path
import subprocess

from benedict import benedict
from rich.live import Live
from rich.spinner import Spinner

from easysam.generate import generate
from easysam.commondep import commondep
import easysam.utils as u

SAM_CLI_VERSION = '1.138.0'
PIP_VERSION = '25.1.1'


def deploy(cliparams: dict, directory: Path, deploy_ctx: benedict):
    '''
    Deploy a SAM template to AWS.

    Args:
        cliparams: The CLI parameters.
        directory: The directory containing the SAM template.
        deploy_ctx: The deployment context.
    '''

    resources, errors = generate(cliparams, directory, [], deploy_ctx)

    if errors:
        lg.error(f'There were {len(errors)} errors:')

        for error in errors:
            lg.error(error)

        raise UserWarning('There were errors - aborting deployment')

    lg.info(f'Deploying SAM template from {directory}')
    check_pip_version(cliparams)
    check_sam_cli_version(cliparams)
    remove_common_dependencies(directory)
    copy_common_dependencies(directory, resources)

    # Building the application from the SAM template
    sam_build(cliparams, directory)

    # Deploying the application to AWS
    sam_deploy(cliparams, directory, deploy_ctx, resources)

    if not cliparams.get('no_cleanup'):
        remove_common_dependencies(directory)


def delete(cliparams, environment):
    lg.info(f'Deleting SAM template from {environment}')
    force = cliparams.get('force')
    await_deletion = cliparams.get('await_deletion')
    cf = u.get_aws_client('cloudformation', cliparams)
    mode = 'FORCE_DELETE_STACK' if force else 'STANDARD'
    cf.delete_stack(StackName=environment, DeletionMode=mode)  # type: ignore

    if await_deletion:
        lg.info(f'Awaiting deletion of {environment}')
        stack_status = 'UNKNOWN'

        with Live(Spinner('aesthetic', 'Checking stack status...'), transient=True):
            while stack_status != 'DELETE_COMPLETE':
                lg.debug(f'Stack {environment} is {stack_status}')

                if stack_status != 'UNKNOWN':
                    time.sleep(10)

                try:
                    stacks = cf.describe_stacks(StackName=environment).get('Stacks')
                except Exception as e:
                    lg.debug(f'Error describing stack {environment}: {e}')
                    break

                if not stacks:
                    lg.info(f'Stack {environment} deleted')
                    break

                stack_status = stacks[0]['StackStatus']

                if stack_status not in ['DELETE_COMPLETE', 'DELETE_IN_PROGRESS']:
                    raise UserWarning(f'Stack {environment} is {stack_status}')

    lg.info(f'Stack {environment} deleted')


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

    try:
        lg.debug(f'Running command: {" ".join(sam_params)}')
        subprocess.run(sam_params, cwd=directory.resolve(), text=True, check=True)
        lg.info('Successfully built SAM template')

    except subprocess.CalledProcessError as e:
        lg.error(f'Failed to build SAM template: {e}')
        raise UserWarning('Failed to build SAM template') from e


def sam_deploy(cliparams, directory, deploy_ctx, resources):
    lg.info(f'Deploying SAM template from {directory} to\n{json.dumps(deploy_ctx, indent=4)}')
    sam_tool = cliparams['sam_tool']
    sam_params = sam_tool.split(' ')

    aws_stack = deploy_ctx['environment']

    if not aws_stack:
        raise UserWarning('No AWS stack found in deploy context')

    sam_params.extend([
        'deploy',
        '--parameter-overrides', f'ParameterKey=Stage,ParameterValue={aws_stack}',
        '--stack-name', aws_stack,
        '--no-fail-on-empty-changeset',
        '--no-confirm-changeset',
        '--resolve-s3',
        '--capabilities', 'CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'
    ])

    region = deploy_ctx.get('target_region')

    if region:
        sam_params.extend(['--region', region])

    aws_tags = list(cliparams.get('tag', []))

    if 'tags' in resources:
        aws_tags.extend(
            f'{name}={value}'
            for name, value in resources['tags'].items()
        )

    aws_tag_string = ' '.join(aws_tags)
    lg.info(f'AWS tag string: {aws_tag_string}')
    sam_params.extend(['--tags', aws_tag_string])

    if cliparams.get('verbose'):
        sam_params.append('--debug')

    if cliparams['dry_run']:
        lg.info(f'Would run: {" ".join(sam_params)}')
        return

    if cliparams.get('aws_profile'):
        lg.info(f'Using AWS profile: {cliparams["aws_profile"]}')
        sam_params.extend(['--profile', cliparams['aws_profile']])

    try:
        lg.debug(f'Running command: {" ".join(sam_params)}')
        subprocess.run(sam_params, cwd=directory.resolve(), text=True, check=True)
        lg.info('Successfully deployed SAM template')

    except subprocess.CalledProcessError as e:
        lg.error(f'Failed to deploy SAM template: {e}')
        raise UserWarning('Failed to deploy SAM template') from e


def common_dep_dir(directory):
    return Path(directory, 'common')


def remove_common_dependencies(directory):
    lg.info(f'Removing common dependencies from {directory}')
    backend = Path(directory, 'backend')

    for common_dep in backend.glob('**/common'):
        lg.debug(f'Removing {common_dep}')
        shutil.rmtree(common_dep)


def copy_common_dependencies(directory, resources):
    lg.info('Looking for common dependencies')
    common = common_dep_dir(directory)

    if not common.exists():
        lg.info('No common dependencies found')
        return

    lg.info(f'Copying common dependencies to {directory}')

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

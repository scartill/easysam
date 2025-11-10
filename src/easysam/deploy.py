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
DEFAULT_SAM_TOOL = 'uv run sam'


def deploy(
    toolparams: dict,
    directory: Path,
    deploy_ctxs: list[benedict],
):
    """
    Deploy a SAM template to AWS.

    Args:
        toolparams: The CLI parameters.
        directory: The directory containing the SAM template.
        deploy_ctxs: The deployment contexts.

    Note: other deployment contexts can be discovered by inspecting the resources.yaml file.
    """

    resources_set, errors = generate(
        toolparams, directory, deploy_ctxs
    )

    if errors:
        lg.error(f'There were {len(errors)} errors:')

        for error in errors:
            lg.error(error)

        raise UserWarning(
            f'There were {len(errors)} errors - aborting deployment'
        )

    _check_pip_version(toolparams)
    _check_sam_cli_version(toolparams)

    for deploy_ctx in deploy_ctxs:
        name = deploy_ctx.get('name', 'default')
        lg.info(f'Invoking deployment for {name}')
        resources = resources_set[name]

        _deploy_with_context(
            toolparams=toolparams,
            resources=resources,
            directory=directory,
            deploy_ctx=deploy_ctx,
        )


def delete(toolparams, environment):
    lg.info(f'Deleting SAM template from {environment}')
    force = toolparams.get('force')
    await_deletion = toolparams.get('await_deletion')
    cf = u.get_aws_client('cloudformation', toolparams)
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


def _deploy_with_context(
    *,
    toolparams: dict,
    resources: benedict,
    directory: Path,
    deploy_ctx: benedict,
):
    lg.info(f'Deploying SAM template from {directory}')
    remove_common_dependencies(directory)
    copy_common_dependencies(directory, resources)

    # Building the application from the SAM template
    _sam_build(toolparams, directory, deploy_ctx)

    # Deploying the application to AWS
    _sam_deploy(toolparams, directory, deploy_ctx, resources)

    if not toolparams.get('no_cleanup'):
        remove_common_dependencies(directory)


def _check_pip_version(toolparams):
    lg.info('Checking pip version')

    try:
        lg.debug(f'Running command: {" ".join(["pip", "--version"])}')
        pip_version = subprocess.check_output(['pip', '--version']).decode('utf-8')

        if pip_version < PIP_VERSION:
            raise UserWarning(f'pip version must be {PIP_VERSION} or higher')

    except Exception as e:
        raise UserWarning('pip not found') from e


def _check_sam_cli_version(toolparams):
    lg.info('Checking SAM CLI version')
    sam_tool = toolparams.get('sam_tool', DEFAULT_SAM_TOOL)
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


def _sam_build(
    toolparams: dict,
    directory: Path,
    deploy_ctx: benedict,
):
    lg.info(f'Building SAM template from {directory}')
    build_dir = u.get_build_dir(directory, deploy_ctx)
    template = Path(build_dir, 'template.yml')

    if not template.exists():
        raise UserWarning(
            f'Template {template} not found in build directory {build_dir}'
        )

    sam_tool: str = toolparams.get('sam_tool', DEFAULT_SAM_TOOL)
    sam_params = sam_tool.split(' ')

    sam_build_dir = Path(
        build_dir.relative_to(directory), '.aws-sam'
    )

    sam_params.extend(
        [
            'build',
            '--template-file',
            template.relative_to(directory).as_posix(),
            '--build-dir',
            sam_build_dir.as_posix(),
        ]
    )

    if region := deploy_ctx.get('target_region'):
        sam_params.extend(['--region', region])
    else:
        lg.info('No AWS region found in the target. Relying on the environment or profile to infer the region.')

    if toolparams.get('verbose'):
        sam_params.append('--debug')

    try:
        lg.info(f'Running command: {" ".join(sam_params)}')
        subprocess.run(
            sam_params,
            cwd=directory.as_posix(),
            text=True,
            check=True,
        )
        lg.info('Successfully built SAM template')

    except subprocess.CalledProcessError as e:
        lg.error(f'Failed to build SAM template: {e}')
        raise UserWarning('Failed to build SAM template') from e


def _sam_deploy(toolparams, directory, deploy_ctx, resources):
    lg.info(
        f'Deploying SAM template from {directory} to\n{json.dumps(deploy_ctx, indent=4)}'
    )
    sam_tool = toolparams.get('sam_tool', DEFAULT_SAM_TOOL)
    sam_params = sam_tool.split(' ')
    aws_stack = deploy_ctx['environment']

    if not aws_stack:
        raise UserWarning('No AWS stack found in deploy context')

    sam_params.extend(
        [
            'deploy',
            '--parameter-overrides',
            f'ParameterKey=Stage,ParameterValue={aws_stack}',
            '--stack-name',
            aws_stack,
            '--no-fail-on-empty-changeset',
            '--no-confirm-changeset',
            '--resolve-s3',
            '--capabilities',
            'CAPABILITY_IAM',
            'CAPABILITY_NAMED_IAM',
        ]
    )

    region = deploy_ctx.get('target_region')

    if region:
        sam_params.extend(['--region', region])
    else:
        lg.info('No AWS region found in the target. Relying on the environment or profile to infer the region.')

    aws_tags = list(toolparams.get('tag', []))

    if 'tags' in resources:
        aws_tags.extend(f'{name}={value}' for name, value in resources['tags'].items())

    aws_tag_string = ' '.join(aws_tags)
    lg.info(f'AWS tag string: {aws_tag_string}')
    sam_params.extend(['--tags', aws_tag_string])

    if toolparams.get('verbose'):
        sam_params.append('--debug')

    if target_profile := deploy_ctx.get('target_profile'):
        lg.info(
            f'Using AWS profile from target: {target_profile}'
        )
        sam_params.extend(['--profile', target_profile])
    else:
        lg.warning('No AWS profile found in target. Relying on the environment to infer the profile.')

    build_dir = u.get_build_dir(directory, deploy_ctx)
    sam_build_dir = Path(build_dir, '.aws-sam')
    run_description = f'{" ".join(sam_params)} in {sam_build_dir}'

    if 'dry_run' not in toolparams:
        raise UserWarning('dry_run must be present in `toolparams`')

    if toolparams['dry_run']:
        lg.info(f'Would run: {run_description}')
        return

    try:
        lg.info(f'Running command: {run_description}')
        subprocess.run(
            sam_params,
            cwd=sam_build_dir.as_posix(),
            text=True,
            check=True,
        )
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

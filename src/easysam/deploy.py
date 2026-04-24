import logging as lg
import json
import time
import shutil
import os
import hashlib
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


def get_dir_hash(directory: Path) -> str:
    '''Calculate a deterministic hash of a directory content'''
    sha256 = hashlib.sha256()
    
    # Sort files to ensure deterministic hashing
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            # Hash path (relative) and content
            sha256.update(str(path.relative_to(directory)).encode())
            with open(path, 'rb') as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
                    
    return sha256.hexdigest()


def orchestrate_docker(cliparams, resources, deploy_ctx, directory):
    if 'services' not in resources:
        return {}

    if cliparams.get('no_docker_build_on_win') and os.name == 'nt':
        lg.info('Skipping Docker builds on Windows due to --no-docker-build-on-win')
        return {}

    image_overrides = {}
    lprefix = resources['prefix'].lower()
    stage = deploy_ctx['environment']
    
    ecr = u.get_aws_client('ecr', cliparams)
    
    for service_name, service in resources['services'].items():
        if not service.get('build'):
            continue
            
        repo_name = f"{lprefix}-{service_name}-{stage}"
        build_path = Path(directory, service['build']).resolve()
        
        # 1. Calculate Content Hash
        content_hash = get_dir_hash(build_path)
        hash_tag = f"sha256-{content_hash}"
        
        lg.info(f"Orchestrating Docker for service {service_name} (Hash: {content_hash[:8]})")
        
        # 2. Ensure ECR Repository exists
        try:
            ecr.create_repository(repositoryName=repo_name)
            lg.info(f"Created ECR repository: {repo_name}")
        except ecr.exceptions.RepositoryAlreadyExistsException:
            lg.debug(f"ECR repository {repo_name} already exists")
            
        repo_data = ecr.describe_repositories(repositoryNames=[repo_name])['repositories'][0]
        repo_uri = repo_data['repositoryUri']
        image_tag = f"{repo_uri}:{hash_tag}"
        
        # 3. Check if image with this hash already exists
        try:
            images = ecr.list_images(repositoryName=repo_name, filter={'tagStatus': 'TAGGED'})['imageIds']
            if any(img.get('imageTag') == hash_tag for img in images):
                lg.info(f"Image {hash_tag} already exists in ECR. Skipping build and push.")
                param_name = f"{lprefix}{service_name.replace('-', '')}Image"
                image_overrides[param_name] = image_tag
                continue
        except Exception as e:
            lg.warning(f"Could not check for existing image: {e}. Proceeding with build.")
        
        # 4. ECR Login
        auth = ecr.get_authorization_token()['authorizationData'][0]
        token = u.base64.b64decode(auth['authorizationToken']).decode('utf-8').split(':')[1]
        proxy_endpoint = auth['proxyEndpoint']
        
        lg.info(f"Logging into ECR: {proxy_endpoint}")
        login_cmd = ['docker', 'login', '-u', 'AWS', '-p', token, proxy_endpoint]
        subprocess.run(login_cmd, check=True, capture_output=True)
        
        # 5. Docker Build
        lg.info(f"Building Docker image: {image_tag} from {build_path}")
        build_cmd = ['docker', 'build', '-t', image_tag, '-t', f"{repo_uri}:latest", str(build_path)]
        subprocess.run(build_cmd, check=True, cwd=directory)
        
        # 6. Docker Push
        lg.info(f"Pushing Docker image: {image_tag}")
        subprocess.run(['docker', 'push', image_tag], check=True)
        subprocess.run(['docker', 'push', f"{repo_uri}:latest"], check=True)
        
        param_name = f"{lprefix}{service_name.replace('-', '')}Image"
        image_overrides[param_name] = image_tag
        
    return image_overrides


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

    # Docker Orchestration for Services
    image_overrides = orchestrate_docker(cliparams, resources, deploy_ctx, directory)

    # Deploying the application to AWS
    sam_deploy(cliparams, directory, deploy_ctx, resources, image_overrides)

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


def get_default_vpc_subnets(cliparams):
    lg.info("Discovering default VPC subnets for Fargate services")
    ec2 = u.get_aws_client('ec2', cliparams)
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])['Vpcs']
    if not vpcs:
        raise UserWarning("No default VPC found in the account/region. Fargate services require a VPC.")

    vpc_id = vpcs[0]['VpcId']
    subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['Subnets']

    # Sort subnets by availability zone to be deterministic
    subnets.sort(key=lambda x: x['AvailabilityZone'])

    if len(subnets) < 2:
        raise UserWarning(f"Default VPC {vpc_id} has fewer than 2 subnets. Fargate services require at least 2 subnets for high availability.")

    return subnets[0]['SubnetId'], subnets[1]['SubnetId']


def sam_deploy(cliparams, directory, deploy_ctx, resources, image_overrides=None):
    lg.info(f'Deploying SAM template from {directory} to\n{json.dumps(deploy_ctx, indent=4)}')
    sam_tool = cliparams['sam_tool']
    sam_params = sam_tool.split(' ')

    aws_stack = deploy_ctx['environment']

    if not aws_stack:
        raise UserWarning('No AWS stack found in deploy context')

    parameter_overrides = [f'ParameterKey=Stage,ParameterValue={aws_stack}']

    if 'services' in resources:
        subnet1, subnet2 = get_default_vpc_subnets(cliparams)
        parameter_overrides.append(f'ParameterKey=DefaultVpcPublicSubnet1,ParameterValue={subnet1}')
        parameter_overrides.append(f'ParameterKey=DefaultVpcPublicSubnet2,ParameterValue={subnet2}')

    if image_overrides:
        for key, value in image_overrides.items():
            parameter_overrides.append(f'ParameterKey={key},ParameterValue={value}')

    sam_params.extend([
        'deploy',
        '--parameter-overrides', ' '.join(parameter_overrides),
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

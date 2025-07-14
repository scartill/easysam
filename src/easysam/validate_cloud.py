import logging as lg

from easysam.utils import get_aws_client


def validate(cliparams: dict, resources_data: dict, stack: str, errors: list[str]):
    '''
    Validate the cloud resources.

    Args:
        cliparams (dict): The CLI parameters (used: aws_profile, aws_region)
        resources_data (dict): The resources data.
        stack (str): The stack/environment name.
        errors (list[str]): The list of errors.
    '''

    iam = get_aws_client('iam', cliparams)
    validate_bucket_policy(iam, resources_data, stack, errors)
    validate_path_roles(iam, resources_data, errors)


def validate_path_roles(iam, resources_data, errors):
    for path in resources_data.get('paths', {}).values():
        if role := path.get('role'):
            lg.info(f'Validating path role: {role}')

            try:
                role = iam.get_role(RoleName=role)

                if not role:
                    errors.append(
                        f"Path role '{role}' not found. "
                        'Please ensure the role exists.'
                    )

            except Exception as e:
                errors.append(f'Error validating path role "{role}": {e}')


def validate_bucket_policy(iam, resources_data, stack, errors):
    for bucket, details in resources_data.get('buckets', {}).items():
        if policy_name := details.get('extaccesspolicy'):
            full_policy_name = f'{policy_name}-{stack}'
            lg.info(f"Validating bucket policy: {full_policy_name}")

            try:
                paginator = iam.get_paginator('list_policies')
                policy = None

                for page in paginator.paginate(Scope='Local'):
                    policies = page['Policies']

                    for item in policies:
                        lg.info(f"Found policy: {item['PolicyName']}")

                        if item['PolicyName'] == full_policy_name:
                            policy = item
                            break

            except Exception as e:
                lg.error(f"Error listing policy {policy_name}: {e}")
                policy = None

            if not policy:
                errors.append(
                    f"Bucket '{bucket}' has an invalid extaccesspolicy: {policy_name}. "
                    f"Please create a policy with the name {full_policy_name}."
                )

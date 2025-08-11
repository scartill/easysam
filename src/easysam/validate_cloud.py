import logging as lg

from easysam.utils import get_aws_client


def validate(cliparams: dict, resources_data: dict, environment: str, errors: list[str]):
    '''
    Validate required external cloud resources.

    Args:
        cliparams (dict): The CLI parameters (used: aws_profile)
        resources_data (dict): The resources data.
        environment (str): The environment name.
        errors (list[str]): The list of errors.
    '''

    iam = get_aws_client('iam', cliparams)
    ssm = get_aws_client('ssm', cliparams)
    lambdas = get_aws_client('lambda', cliparams)

    validate_bucket_policy(iam, resources_data, environment, errors)
    validate_custom_layers(ssm, lambdas, resources_data, errors)


def validate_bucket_policy(iam, resources_data, environment, errors):
    for bucket, details in resources_data.get('buckets', {}).items():
        if policy_name := details.get('extaccesspolicy'):
            full_policy_name = f'{policy_name}-{environment}'
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


def validate_custom_layers(ssm, lambdas, resources_data, errors):
    for function, details in resources_data.get('functions', {}).items():
        layers = details.get('layers', {})

        for layer, layer_handle in layers.items():
            if layer_handle.startswith('{{resolve:'):
                param_uri = layer_handle.split('resolve:')[1].split('}}')[0]

                if not param_uri.startswith('ssm:'):
                    errors.append(
                        f'Custom layer {layer} by URI in ({function}) is not yet supported'
                    )
                    continue

                ssm_param = param_uri.split('ssm:')[1]
                ssm_param = ssm_param.lstrip('/')
                lg.info(f'Validating SSM layer name: {ssm_param}')

                try:
                    layer_handle = ssm.get_parameter(Name=ssm_param)['Parameter']['Value']
                    lg.info(f'Successfully resolved SSM layer name: {ssm_param}')
                    lg.info(f'Layer ARN received: {layer_handle}')

                except Exception:
                    errors.append(f'SSM parameter {ssm_param} not found')
                    continue

            if layer_handle.startswith('arn:'):
                lg.info(f'Looking for layer ARN: {layer_handle}')

                try:
                    response = lambdas.get_layer_version_by_arn(Arn=layer_handle)
                    version = response['Version']
                    lg.info(f'Layer ARN found: {layer_handle}, version: {version}')
                    continue

                except Exception:
                    errors.append(f'Layer ARN {layer_handle} not found')
                    continue

            errors.append(f"Custom layer {layer} in function {function} is not supported")

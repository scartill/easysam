import yaml
from benedict import benedict

from easysam.generate import generate


def _yaml_constructors(loader_class):
    def get_att_constructor(loader, node):
        value = loader.construct_scalar(node)
        return {'Fn::GetAtt': value.split('.')}

    def sub_constructor(loader, node):
        return {'Fn::Sub': loader.construct_scalar(node)}

    def ref_constructor(loader, node):
        return {'Ref': loader.construct_scalar(node)}

    loader_class.add_constructor('!GetAtt', get_att_constructor)
    loader_class.add_constructor('!Sub', sub_constructor)
    loader_class.add_constructor('!Ref', ref_constructor)


def test_gateway_cors_responses_present_when_paths_defined(tmp_path):
    resources_yaml = tmp_path / 'resources.yaml'
    resources_yaml.write_text(
        """
prefix: "test-prefix"
functions:
  myfunc:
    uri: "src/"
paths:
  /items:
    function: myfunc
    open: true
"""
    )

    deploy_ctx = benedict({'environment': 'dev', 'target_region': 'us-east-1'})
    _, errors = generate({}, tmp_path, [], deploy_ctx)
    assert not errors

    _yaml_constructors(yaml.SafeLoader)

    with open(tmp_path / 'template.yml', 'r') as f:
        template = yaml.safe_load(f)

    resources = template['Resources']

    for resource_name, response_type in [
        ('ApiGatewayDefault4xxGatewayResponse', 'DEFAULT_4XX'),
        ('ApiGatewayDefault5xxGatewayResponse', 'DEFAULT_5XX'),
        ('ApiGatewayUnauthorizedGatewayResponse', 'UNAUTHORIZED'),
        ('ApiGatewayAccessDeniedGatewayResponse', 'ACCESS_DENIED'),
    ]:
        assert resource_name in resources, f'{resource_name} should be present in resources'
        resource = resources[resource_name]
        assert resource['Type'] == 'AWS::ApiGateway::GatewayResponse'
        props = resource['Properties']
        assert props['ResponseType'] == response_type
        params = props['ResponseParameters']
        assert 'gatewayresponse.header.Access-Control-Allow-Origin' in params
        assert 'gatewayresponse.header.Access-Control-Allow-Headers' in params
        assert 'gatewayresponse.header.Access-Control-Allow-Methods' in params


def test_gateway_cors_responses_absent_when_no_paths(tmp_path):
    resources_yaml = tmp_path / 'resources.yaml'
    resources_yaml.write_text(
        """
prefix: "test-prefix"
functions:
  myfunc:
    uri: "src/"
"""
    )

    deploy_ctx = benedict({'environment': 'dev', 'target_region': 'us-east-1'})
    _, errors = generate({}, tmp_path, [], deploy_ctx)
    assert not errors

    _yaml_constructors(yaml.SafeLoader)

    with open(tmp_path / 'template.yml', 'r') as f:
        template = yaml.safe_load(f)

    resources = template['Resources']

    for resource_name in [
        'ApiGatewayDefault4xxGatewayResponse',
        'ApiGatewayDefault5xxGatewayResponse',
        'ApiGatewayUnauthorizedGatewayResponse',
        'ApiGatewayAccessDeniedGatewayResponse',
    ]:
        assert resource_name not in resources, f'{resource_name} should not be present without paths'

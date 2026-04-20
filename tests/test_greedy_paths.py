import yaml
from benedict import benedict

from easysam.generate import generate


def test_greedy_lambda_paths_generate_normalized_root_and_proxy_routes(tmp_path):
    resources_yaml = tmp_path / 'resources.yaml'
    resources_yaml.write_text(
        '''
prefix: "test-prefix"
functions:
  myfunc:
    uri: "src/"
paths:
  /items/:
    function: myfunc
    open: true
'''
    )

    deploy_ctx = benedict({'environment': 'dev', 'target_region': 'us-east-1'})
    results, errors = generate({}, tmp_path, [deploy_ctx])
    assert not errors
    resources_data, _ = results['default']

    def get_att_constructor(loader, node):
        value = loader.construct_scalar(node)
        return {'Fn::GetAtt': value.split('.')}

    def sub_constructor(loader, node):
        return {'Fn::Sub': loader.construct_scalar(node)}

    def ref_constructor(loader, node):
        return {'Ref': loader.construct_scalar(node)}

    yaml.SafeLoader.add_constructor('!GetAtt', get_att_constructor)
    yaml.SafeLoader.add_constructor('!Sub', sub_constructor)
    yaml.SafeLoader.add_constructor('!Ref', ref_constructor)

    template_path = tmp_path / 'build' / 'default' / 'template.yml'
    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)

    events = template['Resources']['myfuncFunction']['Properties']['Events']
    assert 'itemsRootAPI' in events
    assert 'itemsProxyAPI' in events
    assert events['itemsRootAPI']['Properties']['Path'] == '/items'
    assert events['itemsProxyAPI']['Properties']['Path'] == '/items/{proxy+}'

    swagger_path = tmp_path / 'build' / 'default' / 'swagger.yaml'
    with open(swagger_path, 'r') as f:
        swagger = yaml.safe_load(f)

    assert '/items' in swagger['paths']
    assert '/items/{proxy+}' in swagger['paths']

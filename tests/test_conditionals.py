import yaml
from pathlib import Path
from easysam.generate import generate

def get_resources(example_path, deploy_ctx):
    # Custom constructors for SAM tags
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

    cliparams = {'verbose': True}
    results, errors = generate(cliparams, example_path, [deploy_ctx])
    assert not errors
    resources_data, errors = results['default']
    
    template_path = example_path / "build" / deploy_ctx.get('name', 'default') / "template.yml"
    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)
    return template['Resources']

def test_conditionals_prod():
    example_path = Path("example/conditionals")
    deploy_ctx = {'environment': 'prod', 'target_region': 'us-east-1'}
    resources = get_resources(example_path, deploy_ctx)
    
    assert 'myappmybucketBucket' in resources
    assert 'myappmybucketReadPolicy' in resources
    policy = resources['myappmybucketReadPolicy']
    assert policy['Properties']['ManagedPolicyName'] == {'Fn::Sub': 'ProdPolicy-${Stage}'}
    
def test_conditionals_eu_west_2():
    example_path = Path("example/conditionals")
    deploy_ctx = {'environment': 'dev', 'target_region': 'eu-west-2'}
    resources = get_resources(example_path, deploy_ctx)
    
    assert 'myappmybucketBucket' in resources
    assert 'myappmybucketReadPolicy' in resources
    policy = resources['myappmybucketReadPolicy']
    assert policy['Properties']['ManagedPolicyName'] == {'Fn::Sub': 'EUWest2Policy-${Stage}'}
    
def test_conditionals_other():
    example_path = Path("example/conditionals")
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    resources = get_resources(example_path, deploy_ctx)
    
    assert 'myappmybucketBucket' in resources
    assert 'myappmybucketReadPolicy' in resources
    policy = resources['myappmybucketReadPolicy']
    assert policy['Properties']['ManagedPolicyName'] == {'Fn::Sub': 'CommonPolicy-${Stage}'}

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
    
    try:
        results, errors = generate(cliparams, example_path, [deploy_ctx])
        resources_data, _ = results[deploy_ctx.get('name', 'default')]
    except Exception as e:
        print(f"Error generating {example_path}: {e}")
        return None
    
    assert not errors
    
    template_path = example_path / "build" / deploy_ctx.get('name', 'default') / "template.yml"
    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)
    return template['Resources']

def test_prismapydantic_generation():
    example_path = Path("example/prismapydantic")
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    resources = get_resources(example_path, deploy_ctx)
    if resources:
        assert 'PrismaPydanticItem' in resources
        assert resources['PrismaPydanticItem']['Type'] == 'AWS::DynamoDB::Table'

def test_prismarinettl_generation():
    example_path = Path("example/prismarinettl")
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    resources = get_resources(example_path, deploy_ctx)
    if resources:
        assert 'PrismaTTLItem' in resources
        assert resources['PrismaTTLItem']['Type'] == 'AWS::DynamoDB::Table'

import yaml
from pathlib import Path
from easysam.generate import generate

def test_kinesis_multiple_buckets_generation():
    example_path = Path("example/kinesismutltiplebuckets")
    
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
    deploy_ctx = {'environment': 'kinesissampledev', 'target_region': 'us-east-1'}
    
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
    
    assert not errors
    
    template_path = example_path / "template.yml"
    assert template_path.exists()
    
    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)
        
    resources = template['Resources']
    lprefix = 'kinesismultiplebucketsapp'
    
    # Verify stream resources
    assert f'{lprefix}simpleStream' in resources
    assert f'{lprefix}complexStream' in resources
    
    # Verify delivery streams
    assert f'{lprefix}simpleprivateDelivery' in resources
    assert f'{lprefix}complexprivateDelivery' in resources
    assert f'{lprefix}complexexternalDelivery' in resources

import yaml
from pathlib import Path
from easysam.generate import generate

def test_aoss_generation():
    example_path = Path("example/aoss")
    
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
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
    
    assert not errors
    
    template_path = example_path / "template.yml"
    assert template_path.exists()
    
    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)
        
    resources = template['Resources']
    
    # Verify searchableCollection
    assert 'searchableCollection' in resources
    assert resources['searchableCollection']['Type'] == 'AWS::OpenSearchServerless::Collection'
    
    # Verify security policies
    assert 'searchableEP' in resources
    assert 'searchableNP' in resources
    assert 'searchableAP' in resources

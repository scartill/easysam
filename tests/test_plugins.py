import yaml
from pathlib import Path
from easysam.generate import generate

def test_plugins_generation():
    example_path = Path("example/plugins")
    
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
    
    results, errors = generate(cliparams, example_path, [deploy_ctx])
    
    assert not errors
    resources_data, _ = results['default']
    
    # Verify plugin output
    plugin_yaml = example_path / "build" / "default" / "myplugin.yaml"
    assert plugin_yaml.exists()
    
    with open(plugin_yaml, 'r') as f:
        plugin_data = yaml.safe_load(f)
        
    assert 'mycustomfunFunction' in plugin_data['Resources']

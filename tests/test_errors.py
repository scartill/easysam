import yaml
from pathlib import Path
from easysam.generate import generate

def test_app_with_errors_generation():
    example_path = Path("example/appwitherrors")
    
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
    resources_data, _ = results['default']

    assert errors
    assert any("Error loading import file" in err for err in errors)

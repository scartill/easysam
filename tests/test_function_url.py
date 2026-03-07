import yaml
from pathlib import Path
from easysam.generate import generate


def test_functionurl_generation():
    example_path = Path('example/functionurl')

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

    # Ensure build dir exists or generate handles it
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)

    assert not errors

    template_path = example_path / 'template.yml'
    assert template_path.exists()

    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)

    resources = template['Resources']
    outputs = template['Outputs']

    # Verify helloworldFunction
    hello_world = resources['helloworldFunction']
    assert hello_world['Type'] == 'AWS::Serverless::Function'
    assert hello_world['Properties']['FunctionUrlConfig']['AuthType'] == 'NONE'

    # Verify hellocustomFunction
    hello_custom = resources['hellocustomFunction']
    assert hello_custom['Type'] == 'AWS::Serverless::Function'
    assert hello_custom['Properties']['FunctionUrlConfig']['AuthType'] == 'NONE'
    assert hello_custom['Properties']['FunctionUrlConfig']['Cors']['AllowOrigins'] == [
        '*'
    ]
    assert hello_custom['Properties']['FunctionUrlConfig']['Cors']['AllowMethods'] == [
        'GET',
        'POST',
    ]

    # Verify Outputs
    assert 'helloworldFunctionUrl' in outputs
    assert outputs['helloworldFunctionUrl']['Value'] == {'Ref': 'helloworldFunctionUrl'}
    assert 'hellocustomFunctionUrl' in outputs
    assert outputs['hellocustomFunctionUrl']['Value'] == {
        'Ref': 'hellocustomFunctionUrl'
    }
    assert 'locallambdaFunctionUrl' in outputs
    assert outputs['locallambdaFunctionUrl']['Value'] == {
        'Ref': 'locallambdaFunctionUrl'
    }


def test_functionurl_validation_error():
    example_path = Path('example/functionurl')
    cliparams = {'verbose': True}
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}

    # Create invalid resources data
    from easysam.load import resources as load_resources

    errors = []
    resources_data = load_resources(example_path, [], deploy_ctx, errors)

    # Modify for error
    resources_data['functions']['hello-world']['functionurl'] = {'auth_type': 'INVALID'}

    # Remove internal values added by load_resources that are not in schema
    resources_data.pop('enable_lambda_layer', None)

    from easysam.validate_schema import validate as validate_schema

    validation_errors = []
    validate_schema(example_path, resources_data, validation_errors)

    assert any(
        'is not valid under any of the given schemas' in err
        for err in validation_errors
    )

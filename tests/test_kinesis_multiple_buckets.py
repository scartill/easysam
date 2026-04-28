import yaml
from pathlib import Path
from easysam.generate import generate


def test_kinesis_multiple_buckets_generation():
    example_path = Path('example/kinesismutltiplebuckets')

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

    template_path = example_path / 'template.yml'
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


def test_kinesis_multiple_buckets_defaults_and_validation():
    # Test our changes to process_default_streams
    from easysam.load import process_default_streams

    # Test that bucketname is properly expanded into buckets.private
    data = {
        'streams': {
            'mystream': {
                'bucketname': 'mybucket',
                'intervalinseconds': 120,
            }
        }
    }
    errors = []
    process_default_streams(data, errors)
    assert not errors
    stream = data['streams']['mystream']
    assert 'bucketname' not in stream
    assert 'bucketprefix' not in stream
    assert 'intervalinseconds' not in stream
    assert stream['buckets']['private']['bucketname'] == 'mybucket'
    assert stream['buckets']['private']['bucketprefix'] == ''
    assert stream['buckets']['private']['intervalinseconds'] == 120

    # Test that both buckets and bucketname is flagged as error
    data2 = {'streams': {'mystream2': {'bucketname': 'mybucket', 'buckets': {'private': {'bucketname': 'mybucket'}}}}}
    errors2 = []
    process_default_streams(data2, errors2)
    assert len(errors2) == 1
    assert 'cannot have both buckets and bucketname' in errors2[0]

    # Test default interval
    from easysam.load import STREAM_INTERVAL_SECONDS

    data3 = {
        'streams': {
            'mystream3': {
                'bucketname': 'mybucket',
            }
        }
    }
    errors3 = []
    process_default_streams(data3, errors3)
    assert not errors3
    assert data3['streams']['mystream3']['buckets']['private']['intervalinseconds'] == STREAM_INTERVAL_SECONDS

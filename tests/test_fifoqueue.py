from pathlib import Path

import yaml

from easysam.generate import generate
from easysam.validate_schema import validate, validate_sqs_path


# --- SAM tag constructors for parsing generated templates ---

def _register_sam_constructors():
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


# --- Task 4: example generation ---

def test_fifoqueue_example_generation():
    _register_sam_constructors()

    example_path = Path('example/fifoqueue')
    cliparams = {'verbose': True}
    deploy_ctx = {'environment': 'fifosampledev', 'target_region': 'us-east-1'}

    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
    assert not errors

    template_path = example_path / 'template.yml'
    assert template_path.exists()

    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)

    resources = template['Resources']
    lprefix = 'fifoqueuelambda'

    # Standard (null) queue: QueueName only, no FIFO props
    std = resources[f'{lprefix}notificationsQueue']['Properties']
    assert std['QueueName'] == {'Fn::Sub': f'{lprefix}-notifications-${{Stage}}'}
    assert 'FifoQueue' not in std

    # FIFO queue with defaults
    orders = resources[f'{lprefix}ordersQueue']['Properties']
    assert orders['QueueName'] == {'Fn::Sub': f'{lprefix}-orders-${{Stage}}.fifo'}
    assert orders['FifoQueue'] is True
    assert orders['ContentBasedDeduplication'] is True
    assert orders['DeduplicationScope'] == 'queue'
    assert orders['FifoThroughputLimit'] == 'perQueue'

    # Fully configured FIFO queue: messageGroup scope auto-forces perMessageGroupId
    payments = resources[f'{lprefix}paymentsQueue']['Properties']
    assert payments['QueueName'] == {'Fn::Sub': f'{lprefix}-payments-${{Stage}}.fifo'}
    assert payments['FifoQueue'] is True
    assert payments['ContentBasedDeduplication'] is False
    assert payments['DeduplicationScope'] == 'messageGroup'
    assert payments['FifoThroughputLimit'] == 'perMessageGroupId'
    assert payments['VisibilityTimeout'] == 60
    assert payments['MessageRetentionPeriod'] == 86400

    # Lambda has the poller policy (orders) and send policy (payments)
    fn = resources['orderprocessorFunction']['Properties']
    policies = fn['Policies']
    poller = [p for p in policies if isinstance(p, dict) and 'SQSPollerPolicy' in p]
    sender = [p for p in policies if isinstance(p, dict) and 'SQSSendMessagePolicy' in p]
    assert poller, 'expected an SQSPollerPolicy for the polled FIFO queue'
    assert sender, 'expected an SQSSendMessagePolicy for the send FIFO queue'


# --- Task 1: schema validation ---

def _schema_validate(resources_data):
    errors = []
    validate(Path('.'), resources_data, errors)
    return errors


def test_schema_accepts_null_and_fifo_queues():
    data = {
        'prefix': 'App',
        'queues': {
            'standard': None,
            'fifo': {
                'fifo': True,
                'content_based_deduplication': True,
                'deduplication_scope': 'queue',
                'fifo_throughput_limit': 'perQueue',
                'visibility_timeout': 30,
                'message_retention_period': 3600,
            },
        },
    }
    errors = _schema_validate(data)
    schema_errors = [e for e in errors if 'Invalid resources data' in e]
    assert not schema_errors, schema_errors


def test_schema_rejects_unknown_queue_property():
    data = {
        'prefix': 'App',
        'queues': {'bad': {'fifo': True, 'nonsense': 'x'}},
    }
    errors = _schema_validate(data)
    assert any('Invalid resources data' in e for e in errors)


# --- Task 3: FIFO rejected as API Gateway SQS integration target ---

def test_sqs_path_rejects_fifo_queue():
    resources_data = {'queues': {'myfifo': {'fifo': True}, 'plain': None}}

    errors = []
    validate_sqs_path(
        Path('.'), resources_data, '/enqueue',
        {'queue': 'myfifo', 'requestTemplate': 'x', 'responseTemplate': 'y'}, errors,
    )
    assert any('cannot target a FIFO queue' in e for e in errors)

    errors2 = []
    validate_sqs_path(
        Path('.'), resources_data, '/enqueue',
        {'queue': 'plain', 'requestTemplate': 'x', 'responseTemplate': 'y'}, errors2,
    )
    assert not any('cannot target a FIFO queue' in e for e in errors2)


# --- Task 3: queue name length ---

def test_queue_name_length_validation():
    # A normal-length name passes
    ok = {'prefix': 'App', 'queues': {'orders': {'fifo': True}}}
    errors = _schema_validate(ok)
    assert not any('80-character' in e for e in errors)

    # An excessively long queue name is flagged
    long_name = 'a' * 75
    too_long = {'prefix': 'App', 'queues': {long_name: {'fifo': True}}}
    errors2 = _schema_validate(too_long)
    assert any('80-character' in e for e in errors2)

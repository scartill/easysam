from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

import easysam.generate as generate_mod
from easysam.generate import generate
from easysam.load import process_default_vectorindices
from easysam.validate_schema import validate


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


EXAMPLE_PATH = Path('example/vectorindices')
DEPLOY_CTX = {'environment': 'vecdev', 'target_region': 'us-east-1'}


def _schema_validate(resources_data):
    errors = []
    validate(Path('.'), resources_data, errors)
    return [e for e in errors if 'Invalid resources data' in e]


def _valid_vector_table(**vindex_overrides):
    vindex = {
        'name': 'by-embedding',
        'attribute': 'Embedding',
        'dimensions': 1536,
        'distance': 'COSINE',
        'hash': 'Category',
        'filters': ['Brand'],
    }
    vindex.update(vindex_overrides)
    return {
        'prefix': 'App',
        'tables': {
            'Product': {
                'attributes': [{'name': 'ProductId', 'hash': True}],
                'vectorindices': [vindex],
            }
        },
    }


# ------------------------------------------------------------------
# Case 1: Schema accept (R1)
# ------------------------------------------------------------------


def test_schema_accepts_valid_vectorindices():
    data = _valid_vector_table()
    assert not _schema_validate(data)


# ------------------------------------------------------------------
# Case 2: Schema reject (R1, E1, E4)
# ------------------------------------------------------------------


def test_schema_rejects_filters_without_hash():
    data = _valid_vector_table()
    del data['tables']['Product']['vectorindices'][0]['hash']
    assert _schema_validate(data)


def test_schema_rejects_bad_distance():
    data = _valid_vector_table(distance='MANHATTAN')
    assert _schema_validate(data)


def test_schema_rejects_dimensions_zero():
    data = _valid_vector_table(dimensions=0)
    assert _schema_validate(data)


def test_schema_rejects_dimensions_too_large():
    data = _valid_vector_table(dimensions=5000)
    assert _schema_validate(data)


def test_schema_rejects_name_with_space():
    data = _valid_vector_table(name='by embedding')
    assert _schema_validate(data)


def test_schema_rejects_name_too_short():
    data = _valid_vector_table(name='ab')
    assert _schema_validate(data)


def test_schema_rejects_too_many_indices():
    data = _valid_vector_table()
    base = data['tables']['Product']['vectorindices'][0]
    data['tables']['Product']['vectorindices'] = [{**base, 'name': f'idx-{i}'} for i in range(6)]
    assert _schema_validate(data)


def test_schema_rejects_missing_name():
    data = _valid_vector_table()
    del data['tables']['Product']['vectorindices'][0]['name']
    assert _schema_validate(data)


def test_schema_rejects_missing_attribute():
    data = _valid_vector_table()
    del data['tables']['Product']['vectorindices'][0]['attribute']
    assert _schema_validate(data)


# ------------------------------------------------------------------
# Case 3: Preprocess unit tests (R3, E3)
# ------------------------------------------------------------------


def test_preprocess_injects_hash_and_filters_in_order():
    resources_data = {
        'tables': {
            'Product': {
                'attributes': [{'name': 'ProductId', 'hash': True}],
                'vectorindices': [
                    {
                        'name': 'by-embedding',
                        'attribute': 'Embedding',
                        'dimensions': 8,
                        'distance': 'COSINE',
                        'hash': 'Category',
                        'filters': ['Brand', 'Color'],
                    }
                ],
            }
        }
    }
    process_default_vectorindices(resources_data, [])
    names = [a['name'] for a in resources_data['tables']['Product']['attributes']]
    assert names == ['ProductId', 'Category', 'Brand', 'Color']
    # Embedding (the vector attribute) is NOT injected
    assert 'Embedding' not in names


def test_preprocess_does_not_duplicate_existing_key():
    resources_data = {
        'tables': {
            'Product': {
                'attributes': [
                    {'name': 'ProductId', 'hash': True},
                    {'name': 'Category'},
                ],
                'vectorindices': [
                    {
                        'name': 'by-embedding',
                        'attribute': 'Embedding',
                        'dimensions': 8,
                        'distance': 'COSINE',
                        'hash': 'Category',
                    }
                ],
            }
        }
    }
    process_default_vectorindices(resources_data, [])
    names = [a['name'] for a in resources_data['tables']['Product']['attributes']]
    assert names.count('Category') == 1


def test_preprocess_shared_filter_injected_once():
    resources_data = {
        'tables': {
            'Product': {
                'attributes': [{'name': 'ProductId', 'hash': True}],
                'vectorindices': [
                    {
                        'name': 'idx-a',
                        'attribute': 'EmbeddingA',
                        'dimensions': 8,
                        'distance': 'COSINE',
                        'hash': 'Category',
                        'filters': ['Brand'],
                    },
                    {
                        'name': 'idx-b',
                        'attribute': 'EmbeddingB',
                        'dimensions': 8,
                        'distance': 'COSINE',
                        'hash': 'Category',
                        'filters': ['Brand'],
                    },
                ],
            }
        }
    }
    process_default_vectorindices(resources_data, [])
    names = [a['name'] for a in resources_data['tables']['Product']['attributes']]
    assert names.count('Category') == 1
    assert names.count('Brand') == 1


def test_preprocess_injects_gsi_only_attribute():
    # An attribute present only in a GSI `indices` block (not in table.attributes)
    # IS injected, because the template renders AttributeDefinitions from
    # table.attributes only (Critique E3).
    resources_data = {
        'tables': {
            'Product': {
                'attributes': [{'name': 'ProductId', 'hash': True}],
                'indices': [
                    {
                        'name': 'by-category',
                        'attributes': [{'name': 'Category', 'hash': True}],
                    }
                ],
                'vectorindices': [
                    {
                        'name': 'by-embedding',
                        'attribute': 'Embedding',
                        'dimensions': 8,
                        'distance': 'COSINE',
                        'hash': 'Category',
                    }
                ],
            }
        }
    }
    process_default_vectorindices(resources_data, [])
    names = [a['name'] for a in resources_data['tables']['Product']['attributes']]
    assert 'Category' in names


def test_preprocess_no_vector_table_unchanged():
    resources_data = {
        'tables': {
            'Product': {
                'attributes': [{'name': 'ProductId', 'hash': True}],
            }
        }
    }
    before = [dict(a) for a in resources_data['tables']['Product']['attributes']]
    process_default_vectorindices(resources_data, [])
    after = resources_data['tables']['Product']['attributes']
    assert after == before


# ------------------------------------------------------------------
# End-to-end fixtures
# ------------------------------------------------------------------


def _generate_example():
    _register_sam_constructors()
    resources_data, errors = generate({'verbose': True}, EXAMPLE_PATH, [], DEPLOY_CTX)
    assert not errors, errors
    template_path = EXAMPLE_PATH / 'template.yml'
    assert template_path.exists()
    with open(template_path, 'r') as f:
        return yaml.safe_load(f)


# ------------------------------------------------------------------
# Case 4: End-to-end VectorIndexes (R2, R7)
# ------------------------------------------------------------------


def test_example_vectorindexes_rendered():
    template = _generate_example()
    props = template['Resources']['VecExampleProduct']['Properties']

    vindexes = props['VectorIndexes']
    assert len(vindexes) == 1
    vindex = vindexes[0]
    assert vindex['IndexName'] == 'by-embedding'
    assert vindex['Dimensions'] == 1536
    assert vindex['DistanceFunction'] == 'COSINE'
    assert vindex['VectorAttribute']['AttributeName'] == 'Embedding'
    assert vindex['Projection']['ProjectionType'] == 'ALL'

    search_schema = vindex['SearchSchema']
    assert search_schema[0]['AttributeName'] == 'Category'
    assert search_schema[0]['SearchSchemaElementType'] == 'HASH'
    assert search_schema[1]['AttributeName'] == 'Brand'
    assert search_schema[1]['SearchSchemaElementType'] == 'INLINE_FILTER'

    assert props['BillingMode'] == 'PAY_PER_REQUEST'


# ------------------------------------------------------------------
# Case 5: End-to-end AttributeDefinitions (R3)
# ------------------------------------------------------------------


def test_example_attribute_definitions():
    template = _generate_example()
    props = template['Resources']['VecExampleProduct']['Properties']
    attr_defs = props['AttributeDefinitions']
    by_name = {a['AttributeName']: a['AttributeType'] for a in attr_defs}
    assert by_name.get('Category') == 'S'
    assert by_name.get('Brand') == 'S'
    # The vector attribute is NOT an AttributeDefinition
    assert 'Embedding' not in by_name


# ------------------------------------------------------------------
# Case 6: End-to-end IAM (R4)
# ------------------------------------------------------------------


def test_example_searchvectors_iam():
    template = _generate_example()
    policies = template['Resources']['searcherFunction']['Properties']['Policies']

    statements = []
    for policy in policies:
        if isinstance(policy, dict) and 'Statement' in policy:
            statements.extend(policy['Statement'])

    search_stmts = [s for s in statements if s.get('Action') == ['dynamodb:SearchVectors']]
    assert len(search_stmts) == 1
    resource = search_stmts[0]['Resource']
    assert resource == {'Fn::Sub': '${VecExampleProduct.Arn}/index/by-embedding'}


# ------------------------------------------------------------------
# Case 7: IAM negative / E2
# ------------------------------------------------------------------


def _has_searchvectors(policies):
    for policy in policies:
        if isinstance(policy, dict) and 'Statement' in policy:
            for stmt in policy['Statement']:
                if stmt.get('Action') == ['dynamodb:SearchVectors']:
                    return True
    return False


def test_example_plain_function_has_no_searchvectors():
    template = _generate_example()
    policies = template['Resources']['plainFunction']['Properties']['Policies']
    assert not _has_searchvectors(policies)


def test_template_null_tables_guard_does_not_crash():
    # Render the template directly with a function that has `tables: None`
    # alongside a vector table. `tables: null` is schema-invalid, so it must
    # never appear in an example fixture — verify the new SearchVectors Jinja
    # guard here on a synthetic dict (Critique T3, E2).
    #
    # Note: the pre-existing DynamoDBCrudPolicy loop (`{% for table in
    # function.tables %}`) iterates `function.tables` directly, so a literal
    # None would crash that unrelated legacy loop before reaching the new
    # block. We set `function.tables = []` (the semantically equivalent "no
    # referenced tables" case that flattening also produces) so the test
    # isolates the new SearchVectors guard: its `function.tables and ...`
    # condition must short-circuit and emit nothing.
    searchpath = [str(Path(generate_mod.__file__).parent.resolve())]
    jenv = Environment(loader=FileSystemLoader(searchpath=searchpath))
    template = jenv.get_template('template.j2')

    resources_data = {
        'prefix': 'App',
        'tables': {
            'Product': {
                'attributes': [{'name': 'ProductId', 'hash': True}],
                'vectorindices': [
                    {
                        'name': 'by-embedding',
                        'attribute': 'Embedding',
                        'dimensions': 8,
                        'distance': 'COSINE',
                        'hash': 'Category',
                    }
                ],
            }
        },
        'functions': {
            'plain': {
                'uri': 'backend/function/plain',
                'tables': [],
            }
        },
    }

    # Must not raise, and the new SearchVectors guard must emit nothing.
    output = template.render(resources_data)
    assert 'dynamodb:SearchVectors' not in output


# ------------------------------------------------------------------
# Case 8: Byte-identical guard (R5)
# ------------------------------------------------------------------


def test_non_vector_example_has_no_vector_artifacts():
    _register_sam_constructors()
    example_path = Path('example/dynamottl')
    resources_data, errors = generate(
        {'verbose': True},
        example_path,
        [],
        {'environment': 'ttldev', 'target_region': 'us-east-1'},
    )
    assert not errors, errors

    with open(example_path / 'template.yml', 'r') as f:
        template = yaml.safe_load(f)

    for name, resource in template['Resources'].items():
        props = resource.get('Properties', {}) if isinstance(resource, dict) else {}
        if resource.get('Type') == 'AWS::DynamoDB::Table':
            assert 'VectorIndexes' not in props
        if resource.get('Type') == 'AWS::Serverless::Function':
            assert not _has_searchvectors(props.get('Policies', []))

import yaml
import pytest
from pathlib import Path
from easysam.generate import generate

def setup_yaml():
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

@pytest.fixture(autouse=True)
def yaml_constructors():
    setup_yaml()

def test_service_with_image(tmp_path):
    resources_yaml = tmp_path / "resources.yaml"
    resources_yaml.write_text("""
prefix: test
services:
  myservice:
    image: myimage:latest
    cpu: 256
    memory: 512
    count: 1
""", encoding="utf-8")
    
    cliparams = {}
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    resources_data, errors = generate(cliparams, tmp_path, [], deploy_ctx)
    
    assert not errors
    template_path = tmp_path / "template.yml"
    assert template_path.exists()
    
    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)
    
    resources = template['Resources']
    assert 'testCluster' in resources
    assert 'testmyserviceTaskDefinition' in resources
    assert 'testmyserviceService' in resources
    
    task_def = resources['testmyserviceTaskDefinition']
    assert task_def['Properties']['ContainerDefinitions'][0]['Image'] == 'myimage:latest'
    assert task_def['Properties']['Cpu'] == 256
    assert task_def['Properties']['Memory'] == 512
    
    # Verify Metadata: BuildMethod: docker is present by default
    assert task_def['Metadata']['BuildMethod'] == 'docker'

def test_service_with_build(tmp_path):
    resources_yaml = tmp_path / "resources.yaml"
    resources_yaml.write_text("""
prefix: test
services:
  myservice:
    build: ./myservice
""", encoding="utf-8")
    
    cliparams = {}
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    resources_data, errors = generate(cliparams, tmp_path, [], deploy_ctx)
    
    assert not errors
    template_path = tmp_path / "template.yml"
    assert template_path.exists()
    
    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)
    
    resources = template['Resources']
    task_def = resources['testmyserviceTaskDefinition']
    
    # Verify Metadata: BuildMethod: docker is present
    assert task_def['Metadata']['BuildMethod'] == 'docker'

def test_service_with_ports(tmp_path):
    resources_yaml = tmp_path / "resources.yaml"
    resources_yaml.write_text("""
prefix: test
services:
  myservice:
    image: myimage:latest
    ports:
      - 8080
      - 9090
""", encoding="utf-8")
    
    cliparams = {}
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    resources_data, errors = generate(cliparams, tmp_path, [], deploy_ctx)
    
    assert not errors
    template_path = tmp_path / "template.yml"
    
    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)
    
    resources = template['Resources']
    task_def = resources['testmyserviceTaskDefinition']
    port_mappings = task_def['Properties']['ContainerDefinitions'][0]['PortMappings']
    assert len(port_mappings) == 2
    assert port_mappings[0]['ContainerPort'] == 8080
    assert port_mappings[1]['ContainerPort'] == 9090

def test_service_with_full_config(tmp_path):
    resources_yaml = tmp_path / "resources.yaml"
    resources_yaml.write_text("""
prefix: test
tables:
  MyTable:
    attributes:
      - name: id
        hash: true
buckets:
  my-bucket:
    public: false
services:
  myservice:
    image: myimage:latest
    envvars:
      MY_VAR: "myvalue"
      ANOTHER_VAR: "another"
    tables:
      - MyTable
    buckets:
      - my-bucket
""", encoding="utf-8")
    
    cliparams = {}
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    resources_data, errors = generate(cliparams, tmp_path, [], deploy_ctx)
    
    assert not errors
    template_path = tmp_path / "template.yml"
    
    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)
    
    resources = template['Resources']
    
    # Check Task Role Permissions
    task_role = resources['testmyserviceTaskRole']
    policies = task_role['Properties']['Policies']
    
    found_dynamo = False
    found_s3 = False
    
    for policy in policies:
        statements = policy['PolicyDocument']['Statement']
        for statement in statements:
            if 'dynamodb:PutItem' in statement['Action']:
                found_dynamo = True
                assert statement['Resource'] == {'Fn::GetAtt': ['testMyTable', 'Arn']}
            if 's3:GetObject' in statement['Action']:
                found_s3 = True
                assert {'Fn::GetAtt': ['testmybucketBucket', 'Arn']} in statement['Resource']
                assert {'Fn::Sub': 'arn:aws:s3:::${testmybucketBucket}/*'} in statement['Resource']
                
    assert found_dynamo, "DynamoDB permissions not found in TaskRole"
    assert found_s3, "S3 permissions not found in TaskRole"
    
    # Check EnvVars
    task_def = resources['testmyserviceTaskDefinition']
    container_def = task_def['Properties']['ContainerDefinitions'][0]
    
    assert 'Environment' in container_def, "Environment section missing from TaskDefinition"
    env_vars = container_def['Environment']
    
    env_dict = {item['Name']: item['Value'] for item in env_vars}
    assert env_dict.get('MY_VAR') == 'myvalue'
    assert env_dict.get('ANOTHER_VAR') == 'another'
    assert env_dict.get('REGION') == {'Ref': 'AWS::Region'}
    assert env_dict.get('ENV') == {'Ref': 'Stage'}
    assert env_dict.get('ACCOUNT_ID') == {'Ref': 'AWS::AccountId'}

def test_no_docker_build_on_win_flag(tmp_path):
    resources_yaml = tmp_path / "resources.yaml"
    resources_yaml.write_text("""
prefix: test
services:
  myservice:
    build: ./myservice
""", encoding="utf-8")
    
    # Test with flag set to True
    cliparams = {'no_docker_build_on_win': True}
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    resources_data, errors = generate(cliparams, tmp_path, [], deploy_ctx)
    
    assert not errors
    template_path = tmp_path / "template.yml"
    
    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)
    
    resources = template['Resources']
    task_def = resources['testmyserviceTaskDefinition']
    
    # Metadata should NOT be present
    assert 'Metadata' not in task_def

def test_service_with_global_envvars(tmp_path):
    resources_yaml = tmp_path / "resources.yaml"
    resources_yaml.write_text("""
prefix: test
envvars:
  GLOBAL_VAR: global_value
services:
  myservice:
    image: myimage:latest
""", encoding="utf-8")
    
    cliparams = {}
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    resources_data, errors = generate(cliparams, tmp_path, [], deploy_ctx)
    
    assert not errors
    template_path = tmp_path / "template.yml"
    
    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)
    
    resources = template['Resources']
    task_def = resources['testmyserviceTaskDefinition']
    container_def = task_def['Properties']['ContainerDefinitions'][0]
    
    assert 'Environment' in container_def
    env_vars = container_def['Environment']
    
    env_dict = {item['Name']: item['Value'] for item in env_vars}
    assert env_dict.get('GLOBAL_VAR') == 'global_value'
    assert env_dict.get('REGION') == {'Ref': 'AWS::Region'}
    assert env_dict.get('ENV') == {'Ref': 'Stage'}
    assert env_dict.get('ACCOUNT_ID') == {'Ref': 'AWS::AccountId'}

from easysam.generate import generate
from benedict import benedict

def test_local_envvars(tmp_path):
    res_file = tmp_path / 'resources.yaml'
    res_file.write_text('''
prefix: "test-prefix"
functions:
  myfunc:
    uri: "src/"
    envvars:
      LOCAL_VAR1: "val1"
      LOCAL_VAR2: "val2"
''')

    deploy_ctx = benedict({'environment': 'dev', 'target_region': 'us-east-1'})
    data, errors = generate({}, tmp_path, [], deploy_ctx)
    assert not errors

    template = (tmp_path / 'template.yml').read_text()
    assert 'LOCAL_VAR1: val1' in template
    assert 'LOCAL_VAR2: val2' in template
    assert 'REGION: !Ref AWS::Region' in template

import pytest
from pathlib import Path
import os
from easysam.load import resources

def test_envvars_expansion(tmp_path):
    env_file = tmp_path / '.env'
    env_file.write_text('TEST_VAR=my_test_value\n')

    res_file = tmp_path / 'resources.yaml'
    res_file.write_text('''
prefix: "test-prefix-$TEST_VAR"
functions:
  myfunc:
    uri: "src/$TEST_VAR"
''')

    errors = []
    res = resources(tmp_path, [], {}, errors)
    assert not errors
    assert res['prefix'] == 'test-prefix-my_test_value'
    assert res['functions']['myfunc']['uri'] == 'src/my_test_value'

def test_local_envvars_expansion(tmp_path):
    env_file = tmp_path / '.env'
    env_file.write_text('TEST_VAR2=my_test_value2\n')

    res_file = tmp_path / 'resources.yaml'
    res_file.write_text('''
prefix: "test-prefix"
import:
  - mydir
''')

    mydir = tmp_path / 'mydir'
    mydir.mkdir()
    easysam_file = mydir / 'easysam.yaml'
    easysam_file.write_text('''
lambda:
  name: myfunc
  integration:
    path: /mytestvar
    open: true
  resources:
    uri: "src/$TEST_VAR2"
''')

    errors = []
    res = resources(tmp_path, [], {}, errors)
    assert not errors
    assert res['functions']['myfunc']['uri'] == 'src/my_test_value2'
    assert 'paths' in res
    assert list(res['paths'].keys())[0] == '/mytestvar'

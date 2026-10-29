import yaml

from easysam.generate import generate


def _load_template(path):
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
    return yaml.safe_load(path.read_text())


def _collect_policy_actions(policies):
    actions = []
    for policy in policies:
        statements = policy.get('Statement', [])
        if isinstance(statements, dict):
            statements = [statements]
        for statement in statements:
            action = statement.get('Action', [])
            if isinstance(action, str):
                actions.append(action)
            else:
                actions.extend(action)
    return actions


def test_function_schedules_target_generates_targeted_scheduler_resources(tmp_path):
    res_file = tmp_path / 'resources.yaml'
    res_file.write_text(
        """
prefix: "test-prefix"
functions:
  my-func:
    uri: src/
    schedules:
      target: target-lambda
  target-lambda:
    uri: target/
"""
    )

    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    _, errors = generate({}, tmp_path, [], deploy_ctx)
    assert not errors

    template = _load_template(tmp_path / 'template.yml')
    resources = template['Resources']

    assert 'myfuncSchedulerRole' in resources
    assert 'myfuncFunction' in resources
    assert 'targetlambdaFunction' in resources
    assert resources['targetlambdaFunction']['Properties']['FunctionName'] == {
        'Fn::Sub': 'target-lambda-${Stage}'
    }

    scheduler_role = resources['myfuncSchedulerRole']
    assert scheduler_role['Type'] == 'AWS::IAM::Role'

    function_env = resources['myfuncFunction']['Properties']['Environment']['Variables']
    assert 'SCHEDULER_TARGET_ARN' in function_env
    assert 'SCHEDULER_ROLE_ARN' in function_env
    target_function_arn = {
        'Fn::Sub': 'arn:${AWS::Partition}:lambda:${AWS::Region}:${AWS::AccountId}:function:target-lambda-${Stage}'
    }
    assert function_env['SCHEDULER_TARGET_ARN'] == target_function_arn
    assert function_env['SCHEDULER_ROLE_ARN'] == {'Fn::GetAtt': ['myfuncSchedulerRole', 'Arn']}

    scheduler_policy = scheduler_role['Properties']['Policies'][0]
    scheduler_statement = scheduler_policy['PolicyDocument']['Statement'][0]
    assert scheduler_statement['Action'] == ['lambda:InvokeFunction']
    assert scheduler_statement['Resource'] == target_function_arn

    assert scheduler_statement['Resource'] == function_env['SCHEDULER_TARGET_ARN']

    function_policies = resources['myfuncFunction']['Properties']['Policies']
    function_actions = _collect_policy_actions(function_policies)
    assert 'scheduler:CreateSchedule' in function_actions
    assert 'scheduler:UpdateSchedule' in function_actions
    assert 'scheduler:DeleteSchedule' in function_actions
    assert 'scheduler:GetSchedule' in function_actions
    assert 'scheduler:ListSchedules' in function_actions
    assert 'iam:PassRole' in function_actions


def test_function_schedules_self_target_uses_function_arn_substitution(tmp_path):
    res_file = tmp_path / 'resources.yaml'
    res_file.write_text(
        """
prefix: "test-prefix"
functions:
  my-func:
    uri: src/
    schedules:
      target: my-func
"""
    )

    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    _, errors = generate({}, tmp_path, [], deploy_ctx)
    assert not errors

    template = _load_template(tmp_path / 'template.yml')
    resources = template['Resources']
    scheduler_role = resources['myfuncSchedulerRole']
    function_env = resources['myfuncFunction']['Properties']['Environment']['Variables']

    expected_target_arn = {
        'Fn::Sub': 'arn:${AWS::Partition}:lambda:${AWS::Region}:${AWS::AccountId}:function:my-func-${Stage}'
    }
    self_function_arn = {'Fn::GetAtt': ['myfuncFunction', 'Arn']}
    scheduler_statement = scheduler_role['Properties']['Policies'][0]['PolicyDocument']['Statement'][0]

    assert scheduler_statement['Resource'] == expected_target_arn
    assert scheduler_statement['Resource'] != self_function_arn
    assert function_env['SCHEDULER_TARGET_ARN'] == expected_target_arn
    assert function_env['SCHEDULER_TARGET_ARN'] != self_function_arn
    assert function_env['SCHEDULER_ROLE_ARN'] == {'Fn::GetAtt': ['myfuncSchedulerRole', 'Arn']}


def test_function_without_schedules_does_not_add_scheduler_resources(tmp_path):
    res_file = tmp_path / 'resources.yaml'
    res_file.write_text(
        """
prefix: "test-prefix"
functions:
  my-func:
    uri: src/
"""
    )

    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    _, errors = generate({}, tmp_path, [], deploy_ctx)
    assert not errors

    template = _load_template(tmp_path / 'template.yml')
    resources = template['Resources']

    assert 'myfuncSchedulerRole' not in resources
    function_env = resources['myfuncFunction']['Properties']['Environment']['Variables']
    assert 'SCHEDULER_TARGET_ARN' not in function_env
    assert 'SCHEDULER_ROLE_ARN' not in function_env

    function_policies = resources['myfuncFunction']['Properties']['Policies']
    function_actions = _collect_policy_actions(function_policies)
    assert all('scheduler:' not in action for action in function_actions)
    assert all('iam:PassRole' != action for action in function_actions)

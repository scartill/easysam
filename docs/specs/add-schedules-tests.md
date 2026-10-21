# Add schedules tests coverage

## Problem Statement

EasySAM supports Lambda definitions with a `schedules` block, and the generator creates scheduler-related CloudFormation resources and environment variables when `functions.<name>.schedules.target` is defined. The main purpose of this work is to add regression test coverage for that scheduler path. During investigation, a production template issue was also identified and corrected: the scheduler target ARN must reference the generated target Lambda, rather than a hard-coded or incorrectly constructed ARN. The tests must verify this corrected target-based behavior.

The missing tests must confirm that:

- when `schedules.target` is present, the generated CloudFormation output includes the expected scheduler-related role and permissions for the function
- `schedules.target` refers to an EasySAM function key under `functions`
- `SCHEDULER_TARGET_ARN` must resolve to the generated CloudFormation ARN of the target function identified by `function.schedules.target`
- the SchedulerRole's `lambda:InvokeFunction` `Resource` must resolve to that same generated target-function ARN
- the two target ARNs must remain consistent in the generated template
- Lambda definitions without `schedules` continue to behave exactly as before
- the tests match the repository's existing YAML-generation testing patterns

This regression coverage protects EasySAM against incorrect scheduler policy or environment-variable generation in the generated CloudFormation for Lambda functions that opt into scheduling and explicitly rejects preserving the previous hard-coded target ARN as the expected behavior.

## Requirements

1. Add test coverage for the `schedules.target` configuration so the generated CloudFormation output is asserted.
2. When `functions.<name>.schedules.target` is defined, the resulting template must include the scheduler-aware IAM role and related IAM permissions for the target integration.
3. The generated function environment variables must include scheduler metadata such as `SCHEDULER_TARGET_ARN` and `SCHEDULER_ROLE_ARN` when a target is configured.
4. `schedules.target` must identify a function key defined under `functions`.
5. `SCHEDULER_TARGET_ARN` must resolve to the generated CloudFormation ARN of the target function identified by `function.schedules.target`.
6. The SchedulerRole's `lambda:InvokeFunction` `Resource` must resolve to the same generated target-function ARN as `SCHEDULER_TARGET_ARN`.
7. Tests must verify that the two generated target ARNs are consistent and must not preserve the previous hard-coded target ARN as expected behavior.
8. A function without a `schedules` block must continue to generate the same output as before, without scheduler resources or env vars.
9. Tests must validate compiled templates using the same project conventions as the existing generator tests: write temp resource YAML, call `generate(...)`, then parse the generated `template.yml` and assert on `Resources` and environment variables.
10. The tests must not require deployment or live AWS resources.

## Background

### Current implementation shape

The repository generates CloudFormation from resource definitions via `generate(...)` and writes the result to `template.yml`. Existing tests cover generation for features such as function URLs, local env vars, and custom resource mappings.

Relevant implementation details from the current codebase:

- `src/easysam/load.py` copies any `schedules` definition from a lambda definition into the loaded resource metadata.
- `src/easysam/schemas.json` validates `functions.<name>.schedules` as an object with a required `target` string.
- `src/easysam/template.j2` contains scheduler-specific generation when `function.schedules` is defined:
  - scheduler execution role generation
  - permission to pass the scheduler role
  - scheduler permissions such as `CreateSchedule`, `UpdateSchedule`, `DeleteSchedule`, `GetSchedule`, and `ListSchedules`
  - function environment variables `SCHEDULER_TARGET_ARN` and `SCHEDULER_ROLE_ARN`

### Why tests are needed

This path is triggered by a template conditional (`if function.schedules is defined and function.schedules.target is defined`), so the risk is not only missing behavior, but also leaking scheduler-specific generation into ordinary functions. The regression test should lock in both the positive and negative cases.

## Proposed Solution

### Test strategy

Add a focused regression test module under `tests/`, or extend the nearest existing template-generation test file if the repository's style is more consistent there. The tests should follow the same pattern already used across the project:

```python
from easysam.generate import generate


def test_schedules_target_generation(tmp_path):
    res_file = tmp_path / 'resources.yaml'
    res_file.write_text('''
prefix: test-prefix
functions:
  my-func:
    uri: src/
    schedules:
      target: target-lambda
  target-lambda:
    uri: target/
''')

    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
    data, errors = generate({}, tmp_path, [], deploy_ctx)

    assert not errors
    template = (tmp_path / 'template.yml').read_text()
    # yaml.safe_load(...) then assert on Resources / Environment values
```

### Positive-case assertions

For a function with `schedules.target` defined, the test should assert the following using the generated YAML structure:

- the generated function resource exists and is named using the standard `FunctionName` convention
- the generated template includes a scheduler role resource associated with the function, such as `Resources['myfuncSchedulerRole']`
- the function role includes the scheduler management actions and the `iam:PassRole` permission
- the function environment variables include `SCHEDULER_TARGET_ARN` and `SCHEDULER_ROLE_ARN`
- `SCHEDULER_TARGET_ARN` must resolve to the generated CloudFormation ARN for the target function key
- the SchedulerRole `lambda:InvokeFunction` `Resource` must resolve to the same generated target-function ARN as `SCHEDULER_TARGET_ARN`
- when the target function key is `target-lambda`, both values must be `!GetAtt targetlambdaFunction.Arn`; the target resource's `FunctionName` remains `target-lambda-${Stage}`
- the exact YAML keys and values are asserted at the template level rather than via a brittle full-file snapshot

Concrete template-level checks should look like:

- `Resources['myfuncFunction']['Properties']['Environment']['Variables']['SCHEDULER_TARGET_ARN']`
- `Resources['myfuncFunction']['Properties']['Environment']['Variables']['SCHEDULER_ROLE_ARN']`
- `Resources['targetlambdaFunction']['Properties']['FunctionName']` retains the hyphenated physical function name
- `Resources['myfuncSchedulerRole']['Properties']['Policies'][0]['PolicyDocument']['Statement'][0]['Resource']`
- `Resources['myfuncFunction']['Properties']['Policies']` contains the scheduler IAM policy with actions such as `scheduler:CreateSchedule`, `scheduler:UpdateSchedule`, `scheduler:DeleteSchedule`, `scheduler:GetSchedule`, and `scheduler:ListSchedules`
- `Resources['myfuncFunction']['Properties']['Policies']` contains the `iam:PassRole` statement for the scheduler role

The test must define the target function under `functions` and explicitly verify that the scheduler role's `Resource` and `SCHEDULER_TARGET_ARN` both reference its generated CloudFormation ARN. Hyphens are removed only when constructing the CloudFormation logical resource ID; the test must not accept a physical ARN constructed by stripping hyphens from the function key or the previous hard-coded Lambda ARN as expected behavior.

### Negative-case assertions

For a function with no `schedules` block, the test should assert that:

- no `{{function_name}}SchedulerRole` resource exists
- no `SCHEDULER_TARGET_ARN` or `SCHEDULER_ROLE_ARN` keys are present in the function environment variables
- no scheduler IAM actions appear in the Lambda policies
- the generated template remains equivalent to the pre-scheduler baseline behavior

### Example expected template behavior

The test should validate the generated CloudFormation contract rather than a full snapshot. Representative assertions include:

- `SCHEDULER_TARGET_ARN` and `SCHEDULER_ROLE_ARN` are present when scheduling is configured
- the scheduler role resource exists for the current function
- the Lambda policies include the scheduler actions and the pass-role permission
- for functions without `schedules`, none of those keys or resources are present

This keeps the tests stable while still enforcing the intended output generated by the implementation.

## Task Breakdown

### Task 1: Review existing generator test conventions

- Objective: Reuse the repository's proven YAML-generation assertion style instead of inventing a new one.
- Implementation guidance: inspect existing generator tests such as `tests/test_function_url.py` and `tests/test_local_envvars.py` to confirm the project pattern for `tmp_path`, `generate(...)`, and YAML assertions.
- Test requirements: use the same `generate` and `yaml.safe_load` flow established by the project.
- Demo command: `pytest tests/test_function_url.py tests/test_local_envvars.py -q`

### Task 2: Add positive regression test for `schedules.target`

- Objective: Validate the generated CloudFormation output for a function configured with `schedules.target`.
- Implementation guidance:
  - create a minimal temp resources file with a scheduled function and a target function under `functions`; use a hyphenated target key such as `target-lambda`
  - call `generate(...)`
  - parse the generated template YAML
  - assert specific CloudFormation keys and policy statements for the scheduler path
- Test requirements:
  - assert `Resources['myfuncSchedulerRole']` exists
  - assert `Resources['myfuncFunction']['Properties']['Environment']['Variables']['SCHEDULER_TARGET_ARN']` and `SCHEDULER_ROLE_ARN` are present
  - assert `SCHEDULER_TARGET_ARN` and the SchedulerRole policy `Resource` both reference `targetlambdaFunction.Arn`
  - assert `Resources['targetlambdaFunction']['Properties']['FunctionName']` preserves the key's hyphens in its physical name
  - assert the Lambda policies include the scheduler actions and the `iam:PassRole` grant
  - keep the assertions tied to the generated YAML structure rather than a full-file snapshot
- Demo command: `pytest tests/test_schedules.py -q`

### Task 3: Add safeguard test for functions without `schedules`

- Objective: Prevent scheduler logic from affecting ordinary Lambda definitions.
- Implementation guidance:
  - generate a function without any `schedules` block
  - inspect the resulting template
  - assert absence of the scheduler role resource, scheduler env vars, and scheduler IAM actions
- Test requirements: no scheduler metadata is present when the feature is not configured.
- Demo command: `pytest tests/test_schedules.py -q`

### Task 4: Validate only the new coverage

- Objective: Ensure the added tests pass without touching unrelated parts of the codebase.
- Implementation guidance: run only the schedules-focused test file or the minimal subset covering the new assertions.
- Test requirements: the new tests pass and match the repository's established patterns.
- Demo command: `pytest tests/test_schedules.py -q`

## Acceptance Criteria

- A regression test exists for `functions.<name>.schedules.target` generation.
- The test asserts the expected scheduler-specific CloudFormation output using precise YAML keys and resource names.
- The test confirms no scheduler resources, env vars, or IAM statements are created for a Lambda without `schedules`.
- The assertions are tied to the generated CloudFormation structure rather than a brittle full-file snapshot.
- The new tests follow the repository's current YAML-generation test conventions.
- The scheduler target references in the production template resolve to the generated target Lambda ARN, and the regression tests verify this behavior.
- The positive and negative test cases pass without requiring live AWS resources.

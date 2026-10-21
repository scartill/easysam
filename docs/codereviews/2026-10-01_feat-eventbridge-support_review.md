# Code Review: feat/eventbridge-support
- **Date**: 2026-10-01
- **Target Branch**: `main`
- **Files Reviewed**: 4 (scheduler template, schedules tests, schema, schedules specification)

## 1. Architectural & Design Overview

The scheduler configuration is generated from the `functions` mapping. `schedules.target` is treated as an EasySAM function key: both the SchedulerRole invoke policy and `SCHEDULER_TARGET_ARN` construct a CloudFormation `GetAtt` to that key's generated function resource. Removing hyphens for the logical ID matches the template's existing function resource convention, while `FunctionName` retains the original key and stage.

The positive test defines a hyphenated target function and verifies its generated physical name plus both `GetAtt` references. The negative test verifies that an unscheduled function gets no scheduler role, scheduler environment variables, or scheduler/PassRole actions.

## 2. Security & Performance Audit

- **Security Concerns**: No new security issue was found in the template change. The SchedulerRole is scoped to the target function ARN rather than a wildcard.
- **Performance & Scalability**: Not applicable to this static template-generation change.

## 3. Detailed File-by-File Findings

### `src/easysam/template.j2`

No defect found in the reviewed target-reference changes. `replace('-', '')` is used to construct the target function's logical resource ID; `!GetAtt` resolves the ARN for the generated Lambda resource, whose `FunctionName` preserves hyphens.

### `tests/test_schedules.py`

No defect found in the positive/negative assertions for the requested contract. The positive fixture defines `target-lambda` as a real function and verifies both scheduler references equal `{'Fn::GetAtt': ['targetlambdaFunction', 'Arn']}`. The negative test continues to assert absence of scheduler-specific resources, environment variables, and IAM actions.

### `src/easysam/schemas.json`

- **[Severity: Medium]** The `schedules.target` schema validates only that the value is a string; it does not validate that the key exists under `functions`.
  - **Context**: The template now emits `!GetAtt <target-logical-id>Function.Arn`. A typo or unknown target passes the current schema validation and can produce a template with a reference to a nonexistent resource, failing later during CloudFormation validation/deployment.
  - **Suggested Fix**: Add cross-field validation during resource validation/loading (where both `functions` and each `schedules.target` are available) to report an explicit error when the target key is not defined. Keep the JSON schema's basic string validation.

### `docs/specs/add-schedules-tests.md`

- **[Severity: Low]** The specification's scope statements still say the work is validation-only and that no production runtime code is modified, while the confirmed fix changes `src/easysam/template.j2`.
  - **Context**: These statements no longer accurately describe the current implementation/review scope and could mislead a future implementer or reviewer.
  - **Suggested Fix**: Revise the scope/acceptance wording to distinguish the production template correction from the regression-test-only portion, without changing the target-ARN contract.

## 4. Test Coverage & Edge Cases

- **Verified**: `uv run pytest tests/test_schedules.py -q` — `2 passed`.
- **Covered**: Target configured; target function key is hyphenated; generated target `FunctionName` retains hyphens; environment target ARN and SchedulerRole policy use the same generated target function ARN; scheduler permissions and `iam:PassRole`; no-schedules behavior.
- **Missing**: A negative configuration test where `schedules.target` names no function. This should assert a clear validation error once cross-field validation is implemented.
- **Edge Cases**: Hyphen-to-logical-ID conversion follows the current template convention. This review did not assess broader logical-ID collisions among distinct function names that normalize to the same ID.

## 5. Actionable Next Steps

- [ ] **Medium**: Validate that every `schedules.target` refers to a key in `functions`, and add a test for a missing target key.
- [ ] **Low**: Update the specification's stale validation-only/no-production-change scope wording.

## Review Verdict

The requested scheduler ARN implementation and positive/negative regression tests are correct and pass the targeted test run. The principal follow-up is early validation of unknown target function keys; the specification also needs a small scope clarification.

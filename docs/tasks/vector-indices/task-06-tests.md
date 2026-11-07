---
generated-by: "Split Tasks"
source: docs/specs/vector-indices.md
generated-at: 2026-11-07T13:30:00+02:00
inputs-ready: false
completed: false
status: not-started
---

# Task 06: Tests — `tests/test_vectorindices.py`

- [ ] **Completion**
- **Source spec**: `docs/specs/vector-indices.md`
- **Depends on**: `task-01-schema.md`, `task-02-preprocess.md`, `task-03-template-vectorindexes.md`, `task-04-template-iam.md`, `task-05-example-app.md`
- **Blocks**: `None`
- **Parallelism**: `Run last; verifies all prior tasks`

## Objective
Verify R1–R7 and the three Must-Address fixes (E1, E2, E3) with schema unit tests,
preprocessing unit tests, and end-to-end generation assertions.

## Scope & Traceability
- **Requirements / acceptance criteria**: R1–R7.
- **Testing & risk strategy items**: E1, E2, E3, E4, R5 (all from spec Testing & Risk Strategy).
- **Out of scope**: `sam validate` is optional (include only if the SAM CLI is reliably present
  in the test env; otherwise skip with a clear marker).

## Implementation Guidance
- **Files to create or modify**:
  - `tests/test_vectorindices.py`. Follow `tests/test_fifoqueue.py` conventions: register SAM
    tag constructors (`!GetAtt`, `!Sub`, `!Ref`) via a local `_register_sam_constructors()`,
    call `generate(cliparams, Path('example/vectorindices'), [], deploy_ctx)`, assert
    `not errors`, `yaml.safe_load` the `template.yml`, and assert on the parsed dict.
- **Automated tests** (cases):
  1. **Schema accept** (R1): `validate(Path('.'), <data with valid vectorindices>, errors)` →
     no "Invalid resources data" errors.
  2. **Schema reject** (R1, E1, E4): separate cases for `filters` without `hash`; bad
     `distance`; `dimensions` 0 and 5000; `name` with a space and `name` length 2; 6 vector
     indexes (`maxItems`). Each yields a schema error.
  3. **Preprocess unit** (R3, E3): call `process_default_vectorindices` on hand-built dicts —
     hash+filters injected in order; existing key not duplicated; two indexes sharing a filter
     inject once; a GSI-only attribute (absent from `table.attributes`) IS injected; no-vector
     table unchanged.
  4. **End-to-end VectorIndexes** (R2, R7): on the example `template.yml`, assert
     `Resources['VecExampleProduct']['Properties']['VectorIndexes'][0]` has the mapped fields,
     `Projection.ProjectionType == 'ALL'`, `BillingMode == 'PAY_PER_REQUEST'`, and
     `SearchSchema` ordered HASH then INLINE_FILTER.
  5. **End-to-end AttributeDefinitions** (R3): `Category` and `Brand` present in the table's
     `AttributeDefinitions` with `AttributeType: S`; `Embedding` (the vector attribute) is
     ABSENT.
  6. **End-to-end IAM** (R4): the `searcher` function role `Policies` contains a statement with
     `Action == ['dynamodb:SearchVectors']` and `Resource` resolving (via the `!Sub`
     constructor) to a dict `{'Fn::Sub': '${VecExampleProduct.Arn}/index/by-embedding'}`.
  7. **IAM negative / E2**: the second function (no `tables` / `tables: null`) generates with
     no errors and has NO `SearchVectors` statement.
  8. **Byte-identical guard** (R5): generate an existing non-vector example (e.g.
     `example/dynamottl` or `example/myapp`) and assert its table has NO `VectorIndexes` key and
     its functions have no `SearchVectors` statement. (Dict-level guard; a stricter string
     snapshot of the pre-change section is optional.)
- **Established patterns to follow**: `tests/test_fifoqueue.py` (schema unit tests +
  end-to-end), `tests/test_dynamottl.py` (parsed-dict assertions on `template.yml`).
- **Constraints and non-goals**: tests must be hermetic (`uv run pytest`, no AWS calls).

## Verification Requirements
- **Automated tests**: the cases above.
- **Manual / integration checks**: full suite stays green (`uv run pytest`).
- **Risk coverage**: E1, E2, E3, E4, R5, and R1–R7 acceptance.
- **Demo command**: `uv run pytest tests/test_vectorindices.py -q`
- **Expected result**: all new tests pass; no regression in the existing suite.

## Handoff Notes
Table logical id in assertions = `{{ prefix }}{{ table_name }}` with raw prefix, e.g.
`VecExampleProduct` (no dash-strip). Keep the deploy context consistent with the example.

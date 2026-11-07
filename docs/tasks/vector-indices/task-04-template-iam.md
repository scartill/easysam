---
generated-by: "Split Tasks"
source: docs/specs/vector-indices.md
generated-at: 2026-11-07T13:30:00+02:00
inputs-ready: false
completed: false
status: not-started
---

# Task 04: Emit `dynamodb:SearchVectors` IAM for referencing functions

- [ ] **Completion**
- **Source spec**: `docs/specs/vector-indices.md`
- **Depends on**: `task-01-schema.md`
- **Blocks**: `task-05-example-app.md`, `task-06-tests.md`
- **Parallelism**: `Same file as task-03 (template.j2) — sequence after task-03`

## Objective
Grant a function that references a vector-indexed table `dynamodb:SearchVectors` permission
scoped to each vector index ARN (R4), without crashing when a function has no `tables`.

## Scope & Traceability
- **Requirements / acceptance criteria**: R4.
- **Testing & risk strategy items**: Critique E2 (guard null/undefined `function.tables`).
- **Out of scope**: `VectorIndexes` rendering (Task 3); IAM policy consolidation across
  indexes (Critique E5 is a 💡 Recommendation, retained in the critique report — NOT applied
  here; emit one statement per index as specified).

## Implementation Guidance
- **Files to create or modify**:
  - `src/easysam/template.j2`, function `Policies:` block: **after** the
    `{% for table in function.tables %}- DynamoDBCrudPolicy:...{% endfor %}` loop, add:
    ```jinja
    {% if tables is defined %}
    {% for table_name, table in tables.items() %}
    {% if function.tables and table.vectorindices and table_name in function.tables %}
    {% for vindex in table.vectorindices %}
    - Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Action:
            - dynamodb:SearchVectors
          Resource: !Sub "${{ '{' }}{{ prefix }}{{ table_name }}.Arn}/index/{{ vindex.name }}"
    {% endfor %}
    {% endif %}
    {% endfor %}
    {% endif %}
    ```
- **Data/API/UI behaviour**: the `{% if function.tables and ... %}` guard is MANDATORY —
  functions need not declare `tables`, and `tables: null` is a common YAML idiom; an unguarded
  `table_name in function.tables` raises `TypeError: argument of type 'NoneType' is not
  iterable` and crashes generation (Critique E2). The `${{ '{' }}...}` renders a literal
  `!Sub "${Prefix<Table>.Arn}/index/<name>"`; `{{ prefix }}{{ table_name }}` is the table
  logical id (raw `prefix`, no dash-strip). One statement per vector index.
- **Established patterns to follow**: the existing stream-trigger inline policy in the same
  `Policies:` block (iterates `tables.items()`, matches on `function_name`, scopes by
  `!GetAtt {{ prefix }}{{ table_name }}.StreamArn`). This task mirrors that cross-reference.
- **Constraints and non-goals**: do not alter the `DynamoDBCrudPolicy`, stream-trigger,
  bucket/queue/stream/service/search policy blocks. A function referencing only non-vector
  tables must emit no `SearchVectors` statement (R4).

## Verification Requirements
- **Automated tests**: Task 6 end-to-end — the example's referencing function's `Policies`
  contains an inline statement with `Action: ['dynamodb:SearchVectors']` and `Resource` equal
  to the index-ARN `!Sub` (parsed via the SAM `!Sub` constructor); a function with
  `tables: null` (or no `tables`) + a vector table in the project generates with NO errors and
  NO `SearchVectors` statement (Critique E2); a non-vector-only function has no such statement.
- **Manual / integration checks**: `generate(...)` on the example; inspect the rendered role.
- **Risk coverage**: E2, R4.
- **Demo command**: `uv run pytest tests/test_vectorindices.py -q -k iam`
- **Expected result**: scoped `SearchVectors` statement present for referencing functions,
  absent otherwise, and null-`tables` functions do not crash generation.

## Handoff Notes
Depends on Task 3 touching the same file; sequence 03 → 04. E5 (consolidate statements) is
intentionally deferred as a human-review recommendation; do not consolidate here.

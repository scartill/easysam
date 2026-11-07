---
generated-by: "Split Tasks"
source: docs/specs/vector-indices.md
generated-at: 2026-11-07T13:30:00+02:00
inputs-ready: false
completed: false
status: not-started
---

# Task 03: Render the `VectorIndexes` block in `template.j2`

- [ ] **Completion**
- **Source spec**: `docs/specs/vector-indices.md`
- **Depends on**: `task-01-schema.md`
- **Blocks**: `task-05-example-app.md`, `task-06-tests.md`
- **Parallelism**: `Same file as task-04 (template.j2) — coordinate / sequence with it`

## Objective
Emit the native `AWS::DynamoDB::Table` `VectorIndexes` property for any table carrying
`vectorindices`, mapping Prismarine's lowercase keys to CloudFormation casing (R2, R7).

## Scope & Traceability
- **Requirements / acceptance criteria**: R2, R7.
- **Testing & risk strategy items**: Critique E1 (SearchSchema only when `hash`); R5
  (byte-identical when no vector indexes).
- **Out of scope**: IAM (Task 4); AttributeDefinitions injection (Task 2).

## Implementation Guidance
- **Files to create or modify**:
  - `src/easysam/template.j2`, `# Tables` section: insert a `VectorIndexes` block **after**
    the `{% if table.indices %}...{% endif %}` GSI block and **before** `BillingMode:
    PAY_PER_REQUEST` (keeps billing/PITR/stream/ttl ordering intact). Match the surrounding
    indentation: under `Properties:` (4 spaces), table properties sit at **6 spaces** and
    nested list items at **8 spaces** (Critique T1). Exact Jinja:
    ```jinja
          {% if table.vectorindices %}
          VectorIndexes:
            {% for vindex in table.vectorindices %}
            - IndexName: {{ vindex.name }}
              Dimensions: {{ vindex.dimensions }}
              DistanceFunction: {{ vindex.distance }}
              VectorAttribute:
                AttributeName: {{ vindex.attribute }}
              Projection:
                ProjectionType: ALL
              {% if vindex.hash %}
              SearchSchema:
                - AttributeName: {{ vindex.hash }}
                  SearchSchemaElementType: HASH
                {% for f in vindex.filters %}
                - AttributeName: {{ f }}
                  SearchSchemaElementType: INLINE_FILTER
                {% endfor %}
              {% endif %}
            {% endfor %}
          {% endif %}
    ```
- **Data/API/UI behaviour**: `SearchSchema` guarded by `{% if vindex.hash %}` only — never
  rendered for `filters` alone (Critique E1; also schema-blocked by Task 1). HASH precedes
  INLINE_FILTER. Indentation must match the surrounding `Properties:` block (2-space YAML;
  `write_result` strips blank lines, so guard with `{% if %}` to avoid stray lines).
- **Established patterns to follow**: the adjacent `{% if table.indices %}GlobalSecondaryIndexes:
  ...{% endif %}` block (same guard-and-loop idiom, `Projection: ProjectionType: ALL` hardcoded).
- **Constraints and non-goals**: fully guarded by `{% if table.vectorindices %}` so a
  non-vector table emits nothing new (R5). Do not change `AttributeDefinitions`, `KeySchema`,
  `GlobalSecondaryIndexes`, `BillingMode`, `StreamSpecification`, or `TimeToLiveSpecification`.

## Verification Requirements
- **Automated tests**: Task 6 end-to-end — parse `template.yml`, assert the table's
  `VectorIndexes[0]` has `IndexName`, `Dimensions`, `DistanceFunction`,
  `VectorAttribute.AttributeName`, `Projection.ProjectionType == 'ALL'`, and a `SearchSchema`
  whose first element is `HASH` followed by `INLINE_FILTER`(s); and a no-`hash` index emits NO
  `SearchSchema`.
- **Manual / integration checks**: `generate(...)` on the example; optional `sam validate`.
- **Risk coverage**: E1, R5.
- **Demo command**: `uv run pytest tests/test_vectorindices.py -q -k vectorindexes`
- **Expected result**: `VectorIndexes` renders with correct casing and SearchSchema ordering.

## Handoff Notes
Task 4 edits the same file (`template.j2`) in the function `Policies:` block. If implemented
by separate agents, sequence Task 3 then Task 4 (or one agent does both) to avoid a merge
conflict. The two edits touch disjoint sections (Tables vs Functions).

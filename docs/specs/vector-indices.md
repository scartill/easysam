---
generated-by: "Plan Spec"
source: docs/seed/vector-indices.md
generated-at: 2026-11-07T13:05:00+02:00
status: draft
critiqued-revision:
---

# Spec: EasySAM CloudFormation Support for DynamoDB Vector Indexes

_Derived from `docs/seed/vector-indices.md` (brainstorm recommended Approach C, hybrid).
Planning decisions in `docs/plans/vector-indices.questions.md` (all defaults applied,
non-interactive Autoflow run)._

## Problem Statement

Prismarine (PR #4, "Vector Indices") emits a `vectorindices` block into the EasySAM table
dict, but EasySAM silently ignores it. EasySAM must consume that block and render DynamoDB
**native vector indexes** into CloudFormation via the official `AWS::DynamoDB::Table`
`VectorIndexes` property, grant functions that reference a vector-indexed table permission to
call `SearchVectors` on the index, and ship a working end-to-end example. Tables without a
vector index must continue to generate byte-identical CloudFormation.

EasySAM does **not** generate embeddings and does **not** implement the `SearchVectors`
runtime call (that lives in Prismarine's generated client). This change is provisioning +
IAM access only.

## Requirements

User-observable acceptance criteria:

- **R1 — Schema accepts `vectorindices`.** A table definition (in `resources.yaml`, an
  imported `easysam.yaml`, or a Prismarine-synthesized table) may carry a `vectorindices`
  array. Each entry requires `name`, `attribute`, `dimensions`, `distance`; optional `hash`
  (string) and `filters` (array of strings). `distance` ∈ {`COSINE`, `EUCLIDEAN`,
  `DOT_PRODUCT`}; `dimensions` is an integer in `[1, 4096]`. The key is accepted in **both**
  `schemas.json` and `local_schemas.json`. A table without `vectorindices` is unaffected.
- **R2 — `VectorIndexes` rendered.** For a table with `vectorindices`, the generated
  `AWS::DynamoDB::Table` `Properties` includes a `VectorIndexes` list. Each entry maps:
  `name`→`IndexName`, `dimensions`→`Dimensions`, `distance`→`DistanceFunction`,
  `attribute`→`VectorAttribute.AttributeName`, plus `Projection: {ProjectionType: ALL}`. When
  `hash` and/or `filters` are present, a `SearchSchema` list is emitted:
  `hash`→`{AttributeName, SearchSchemaElementType: HASH}` and each `filters` entry →
  `{AttributeName, SearchSchemaElementType: INLINE_FILTER}`. The HASH element (when present)
  precedes the INLINE_FILTER elements.
- **R3 — SearchSchema attributes appear in `AttributeDefinitions`.** Every `hash` and
  `filters` attribute name is present in the table's `AttributeDefinitions` with
  `AttributeType: S`, deduplicated against existing table/GSI attributes (an attribute that
  is already a key keeps its existing definition and is not duplicated). The vector
  `attribute` itself is **not** added to `AttributeDefinitions` (the embedding is not a key
  attribute).
- **R4 — `SearchVectors` IAM.** A function whose `resources.tables` list includes a
  vector-indexed table receives an inline IAM statement granting `dynamodb:SearchVectors`,
  scoped to each vector index ARN of that table
  (`!Sub "${<TableLogicalId>.Arn}/index/<index-name>"`). A function that references only
  non-vector tables gets no such statement.
- **R5 — Byte-identical for non-vector tables.** Generating a project with no `vectorindices`
  anywhere produces output identical to the pre-change template for the DynamoDB and function
  sections.
- **R6 — Working example.** A new `example/vectorindices/` app generates successfully via
  `generate(...)`, producing a table with `VectorIndexes` and a function with the
  `SearchVectors` permission.
- **R7 — On-demand billing.** Vector-indexed tables render `BillingMode: PAY_PER_REQUEST`
  (already EasySAM's hardcoded default; no regression).

## Background (codebase internals)

- **Rendering** is pure Jinja2 over a plain dict. `generate.py::generate` loads
  `resources_data`, builds a Jinja `Environment` (search path = package dir + project dir),
  renders `template.j2` with the whole dict as context, then `write_result` strips blank
  lines. There is no troposphere/Mako.
- **Tables** are rendered in `template.j2`'s `# Tables` section (~lines 406–470):
  `table.attributes` → `AttributeDefinitions` (default `AttributeType: S` when no `type`) +
  two-pass HASH-then-RANGE `KeySchema`; `table.indices` → `GlobalSecondaryIndexes` (guarded
  by `{% if table.indices %}`, `Projection: ProjectionType: ALL` hardcoded);
  `BillingMode: PAY_PER_REQUEST` hardcoded; `table.trigger` → `StreamSpecification`;
  `table.ttl` → `TimeToLiveSpecification`. Table logical id = `{{ prefix }}{{ table_name }}`
  (raw `prefix`, no dash-strip); physical name `!Sub {{ prefix }}{{ table_name }}-${Stage}`.
- **Functions**: `template.j2` function `Policies:` block emits, per `function.tables`,
  `- DynamoDBCrudPolicy: {TableName: !Ref {{ prefix }}{{ table }}}`. An established inline
  precedent is the **stream-trigger** block, which iterates `tables.items()`, matches
  `table.trigger.function == function_name`, and emits an inline statement scoped by
  `!GetAtt {{ prefix }}{{ table_name }}.StreamArn`. The `SearchVectors` statement follows this
  exact cross-reference idiom.
- **Preprocessing**: `load.py::preprocess_defaults` calls a series of
  `process_default_*(resources_data, errors)` steps (searches, functions, streams, tables,
  paths). `process_default_tables` already normalizes triggers in place. Prismarine tables are
  merged into `resources_data['tables']` by `preprocess_prismarine` **before**
  `preprocess_defaults` runs, so a defaults step sees both literal and Prismarine tables.
- **Validation**: `validate_schema.py::validate` runs Draft7 against `schemas.json`;
  imported files validate against `local_schemas.json`. `tables_schema` has
  `additionalProperties: false` in both files, so a new `vectorindices` key must be declared
  or validation rejects it. Note: `schemas.json`'s `table_attribute_schema` lacks a `type`
  field while `local_schemas.json`'s already has the `S`/`N`/`B` enum — injected attributes
  use the default-`S` path and need no `type`, so this asymmetry does not block R3.
- **Tests**: `pytest` via `uv run pytest`. `test_fifoqueue.py` / `test_dynamottl.py` register
  SAM-tag YAML constructors (`!GetAtt`, `!Sub`, `!Ref`), call `generate(cliparams,
  example_path, [], deploy_ctx)` against an `example/` fixture, assert `not errors`, then
  `yaml.safe_load` the written `template.yml` and assert on the parsed dict. `test_fifoqueue.py`
  also unit-tests schema acceptance/rejection via `validate(...)` directly.

### CloudFormation `VectorIndexes` (verified against AWS docs)

`AWS::DynamoDB::Table` has a native `VectorIndexes` property (array of `VectorIndex`):

```yaml
VectorIndexes:
  - IndexName: <string>            # 3..255, [a-zA-Z0-9_.-]+
    Dimensions: <int>             # 1..4096
    DistanceFunction: COSINE | DOT_PRODUCT | EUCLIDEAN
    VectorAttribute:
      AttributeName: <string>
    Projection:
      ProjectionType: ALL
    SearchSchema:                 # optional; >=1 when present
      - AttributeName: <string>   # MUST also be in AttributeDefinitions
        SearchSchemaElementType: HASH | INLINE_FILTER
```

Two load-bearing constraints: (1) every `SearchSchema` attribute must also be declared in
`AttributeDefinitions` (drives R3; overturns Prismarine's Critique E5 at the CloudFormation
layer); (2) CloudFormation permits only one index change (a GSI **or** a vector index, not
both) per single stack operation — a documented operational caveat, not an EasySAM-enforced
rule. Vector indexes require `BillingMode: PAY_PER_REQUEST`.

## Constraints to respect

- Byte-identical output for non-vector tables and functions (R5).
- Vector indexes require on-demand billing — already satisfied by the hardcoded
  `PAY_PER_REQUEST`.
- Up to 5 vector indexes per table; `1 <= dimensions <= 4096` (schema-enforced).
- Injected `hash`/`filters` attributes default to `AttributeType: S`; numeric filters are a
  documented limitation.
- Relative paths only in all artifacts.

## Architecture

```mermaid
flowchart TD
  P[Prismarine vectorindices block] --> T[resources_data tables]
  L[literal tables: block] --> T
  T --> D["load.py: process_default_vectorindices<br/>(inject hash/filters into attributes, dedup)"]
  D --> J[template.j2]
  J --> V["AWS::DynamoDB::Table<br/>VectorIndexes + AttributeDefinitions"]
  J --> I["Function Policies:<br/>dynamodb:SearchVectors on index ARN"]
```

Hybrid split (brainstorm Approach C): the attribute-injection/dedup is done in Python
(`load.py`), where set logic is natural and unit-testable; the `VectorIndexes` rendering and
the `SearchVectors` IAM cross-reference live in `template.j2`, reusing the stream-trigger
precedent.

## Proposed Solution

1. **Schema (both files).** Add a `vector_index_schema` definition and a `vectorindices`
   array property to `tables_schema` in `schemas.json` and `local_schemas.json`:

   ```json
   "vector_index_schema": {
     "type": "object",
     "properties": {
       "name": {"type": "string"},
       "attribute": {"type": "string"},
       "dimensions": {"type": "integer", "minimum": 1, "maximum": 4096},
       "distance": {"type": "string", "enum": ["COSINE", "EUCLIDEAN", "DOT_PRODUCT"]},
       "hash": {"type": "string"},
       "filters": {"type": "array", "items": {"type": "string"}}
     },
     "required": ["name", "attribute", "dimensions", "distance"],
     "additionalProperties": false
   }
   ```
   and inside `tables_schema.properties`:
   `"vectorindices": {"type": "array", "items": {"$ref": "#/definitions/vector_index_schema"}}`.

2. **Preprocessing (`load.py`).** Add `process_default_vectorindices(resources_data, errors)`
   and call it from `preprocess_defaults` (after `process_default_tables`). For each table
   with a non-empty `vectorindices`: collect existing attribute names (`table['attributes']`
   plus any GSI `indices[].attributes[].name`); for each index's `hash` and each `filters`
   entry, if the name is not already present, append `{'name': <attr>}` to `table['attributes']`
   (the template defaults missing `type` to `S`). Idempotent and dedup-safe; no change when
   `vectorindices` is absent.

3. **Template — `VectorIndexes` (`template.j2`).** After the GSI block and before
   `BillingMode`, add:

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
       {% if vindex.hash or vindex.filters %}
       SearchSchema:
         {% if vindex.hash %}
         - AttributeName: {{ vindex.hash }}
           SearchSchemaElementType: HASH
         {% endif %}
         {% for f in vindex.filters %}
         - AttributeName: {{ f }}
           SearchSchemaElementType: INLINE_FILTER
         {% endfor %}
       {% endif %}
     {% endfor %}
   {% endif %}
   ```

4. **Template — `SearchVectors` IAM (`template.j2`).** In the function `Policies:` block,
   after the `DynamoDBCrudPolicy` loop, cross-reference the global `tables` map (mirroring the
   stream-trigger block) and, for each table the function references that has `vectorindices`,
   emit one statement per vector index:

   ```jinja
   {% if tables is defined %}
   {% for table_name, table in tables.items() %}
   {% if table.vectorindices and table_name in function.tables %}
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
   (The `${{ '{' }}...}` escaping yields a literal `!Sub "${Prefix<Table>.Arn}/index/<name>"`.)

5. **Example `example/vectorindices/`.** Self-contained (hermetic) literal `tables:` block
   with one vector-indexed table plus a function referencing it, modeled on `example/aoss/`
   structure. Generates without a Prismarine dependency so EasySAM's own tests stay hermetic.

6. **Docs.** README + `docs/CLI_REFERENCE.md`: the `vectorindices` block, on-demand
   requirement, string-only filter-type limitation, one-index-per-stack-operation caveat, and
   the coordinated Prismarine release note. CHANGELOG entry.

## Testing & Risk Strategy

**Critical paths / acceptance-layer coverage:**
- End-to-end generation of `example/vectorindices/`: parse `template.yml`, assert the table's
  `VectorIndexes` entry (IndexName/Dimensions/DistanceFunction/VectorAttribute/Projection and
  SearchSchema order HASH→INLINE_FILTER), assert `hash`/`filters` names present in
  `AttributeDefinitions` with `AttributeType: S` and no duplicates, assert the vector
  `attribute` is **absent** from `AttributeDefinitions` (R2, R3).
- Assert the referencing function's `Policies` contains a `dynamodb:SearchVectors` statement
  whose `Resource` is the index-ARN `!Sub`, and that a non-vector-only function has none (R4).
- Schema unit tests via `validate(...)`: a valid `vectorindices` passes; a bad `distance`,
  out-of-range `dimensions`, or missing `name`/`attribute` is rejected (R1).
- Byte-identical guard: an existing non-vector example (e.g. `example/myapp` or
  `example/dynamottl`) still generates the same DynamoDB/function output (R5).

**Edge/failure cases:** a vector index with no `hash`/`filters` (no `SearchSchema` emitted);
a `hash`/`filter` attribute that is also a table key (dedup — not duplicated); multiple vector
indexes on one table (multiple `SearchVectors` statements); a function referencing both a
vector and a non-vector table (statement only for the vector table).

**Test levels:** `load`-level unit tests for `process_default_vectorindices` (dedup, type
default, no-op without `vectorindices`); schema unit tests; end-to-end generation tests.

**Risks & mitigations:**
- *Byte-identical regression (Jinja whitespace / blank-line strip)* → fully guard every new
  block with `{% if ... %}`; dedicated R5 test.
- *Duplicate AttributeDefinitions* → dedup in `process_default_vectorindices`; unit test.
- *Wrong attribute type (numeric filter as S)* → documented limitation (seed Q2a).
- *One-index-per-stack-operation CloudFormation limit* → documented caveat, no blocking code.
- *Prismarine branch coupling* → example/tests are hermetic (literal `tables:`); Prismarine
  end-to-end verified out of band; CHANGELOG notes coordinated release.
- *Index ARN shape wrong* → assert the rendered `Resource` in the R4 test.

**Test-data needs:** the new `example/vectorindices/` fixture only.

## Task Outline

1. **Schema** — add `vector_index_schema` + `vectorindices` property to `tables_schema` in
   `schemas.json` and `local_schemas.json`. Outcome: R1; schema unit tests pass.
   Depends on: none.
2. **Preprocessing** — add `process_default_vectorindices` to `load.py`, wired into
   `preprocess_defaults`. Outcome: R3 attribute injection + dedup; `load`-level unit tests.
   Depends on: Task 1 (shape).
3. **Template `VectorIndexes`** — render the `VectorIndexes` block in `template.j2`. Outcome:
   R2, R7. Depends on: Task 1.
4. **Template `SearchVectors` IAM** — emit the index-scoped `SearchVectors` statement in the
   function `Policies` block. Outcome: R4. Depends on: Task 1.
5. **Example app** — `example/vectorindices/` (table + function). Outcome: R6; fixture for
   end-to-end tests. Depends on: Tasks 1–4 (so it generates).
6. **Tests** — `tests/test_vectorindices.py`: schema accept/reject, end-to-end
   `VectorIndexes`/`AttributeDefinitions`/`SearchVectors`, byte-identical guard. Outcome:
   R1–R7 verification. Depends on: Tasks 1–5.
7. **Docs** — README, `docs/CLI_REFERENCE.md`, CHANGELOG. Outcome: documented caveats + release
   note. Depends on: Tasks 1–5.

## Resolved Decisions

| Decision | Source | Choice |
|----------|--------|--------|
| Architecture (hybrid) | seed / brainstorm Approach C | attribute injection in `load.py`; VectorIndexes + IAM in `template.j2` |
| Key mapping | seed Q1 | consume Prismarine lowercase keys, map to CFN casing in template |
| AttributeDefinitions for schema attrs | seed Q2(a) / R3 | inject, dedup, default `AttributeType: S`; string-only limitation documented |
| One-index-per-op limit | seed Q3 | document only, no blocking validation |
| IAM `SearchVectors` | seed Q4 | emit index-scoped statement for referencing functions + ship working example |
| Projection | seed Q5 | hardcode `ProjectionType: ALL` |
| Release coordination | seed Q6 | track Prismarine `vector-indices` branch; publish together |
| Injection location | questionnaire Q1 (default-applied) | `load.py::process_default_vectorindices` via `preprocess_defaults` |
| Validate distance/dimensions | questionnaire Q2 (default-applied) | enforce in JSON Schema |
| Index ARN form | questionnaire Q3 (default-applied) | `!Sub "${<TableLogicalId>.Arn}/index/<name>"` |
| Example type | questionnaire Q4 (default-applied) | hermetic literal `tables:` block (no Prismarine dep in tests) |
| Injected attr type | questionnaire Q5 (default-applied) | fixed `S`; no `type` field added to `vectorindices` this pass |

## Out of Scope

- Generating embeddings; the `SearchVectors` runtime call (Prismarine's generated client).
- Provisioned-throughput billing; configurable projection types; numeric/binary filter types.
- Changing existing GSI (`indices`) semantics.
- Blocking validation for the one-index-per-stack-operation CloudFormation limit.

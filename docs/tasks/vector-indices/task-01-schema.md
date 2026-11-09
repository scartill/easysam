---
generated-by: "Split Tasks"
source: docs/specs/vector-indices.md
generated-at: 2026-11-07T13:30:00+02:00
inputs-ready: false
completed: false
status: done
---

# Task 01: Add `vectorindices` to the table schema (both schema files)

- [x] **Completion**
- **Source spec**: `docs/specs/vector-indices.md`
- **Depends on**: `None`
- **Blocks**: `task-02-preprocess.md`, `task-03-template-vectorindexes.md`, `task-04-template-iam.md`, `task-05-example-app.md`, `task-06-tests.md`
- **Parallelism**: `Run first; all other tasks depend on the shape it defines`

## Objective
Teach EasySAM's JSON Schema validation to accept a `vectorindices` array on a table
definition, enforcing the CloudFormation/DynamoDB contract (R1).

## Scope & Traceability
- **Requirements / acceptance criteria**: R1.
- **Testing & risk strategy items**: Critique E1 (filters-requires-hash), E4 (name
  pattern/length + `maxItems` bounds).
- **Out of scope**: Rendering (Task 3), IAM (Task 4), attribute injection (Task 2).

## Implementation Guidance
- **Files to create or modify**:
  - `src/easysam/schemas.json`: add a `vector_index_schema` definition under `definitions`
    (near `table_attribute_schema` / `tables_schema`), and add a `vectorindices` property to
    `tables_schema.properties`. Exact shape:
    ```json
    "vector_index_schema": {
      "type": "object",
      "properties": {
        "name": {"type": "string", "pattern": "^[a-zA-Z0-9_.-]+$", "minLength": 3, "maxLength": 255},
        "attribute": {"type": "string"},
        "dimensions": {"type": "integer", "minimum": 1, "maximum": 4096},
        "distance": {"type": "string", "enum": ["COSINE", "EUCLIDEAN", "DOT_PRODUCT"]},
        "hash": {"type": "string"},
        "filters": {"type": "array", "items": {"type": "string"}, "maxItems": 18}
      },
      "required": ["name", "attribute", "dimensions", "distance"],
      "dependencies": {"filters": ["hash"]},
      "additionalProperties": false
    }
    ```
    and in `tables_schema.properties`:
    `"vectorindices": {"type": "array", "maxItems": 5, "items": {"$ref": "#/definitions/vector_index_schema"}}`.
  - `src/easysam/local_schemas.json`: mirror the **same** `vector_index_schema` definition and
    the `vectorindices` property on its `tables_schema` (used for imported `easysam.yaml`).
- **Data/API/UI behaviour**: `tables_schema` has `"additionalProperties": false` in both
  files — the new key MUST be declared or every vector table fails validation. The
  `"dependencies": {"filters": ["hash"]}` keyword (JSON Schema Draft 7) makes a block with
  `filters` but no `hash` invalid (Critique E1).
- **Established patterns to follow**: the existing `indices` array property on `tables_schema`
  and the `table_attribute_schema` definition; the Draft7 validator in
  `src/easysam/validate_schema.py::validate`.
- **Constraints and non-goals**: do not alter `table_attribute_schema`, `indices`, `trigger`,
  or `ttl`. Keep both files byte-consistent for the shared definition.

## Verification Requirements
- **Automated tests**: covered in Task 6 (`tests/test_vectorindices.py`) via `validate(...)`:
  a valid `vectorindices` passes; an entry with `filters` but no `hash` is rejected; a bad
  `distance`; out-of-range `dimensions`; a `name` with a space / <3 chars; >5 indices; missing
  `name`/`attribute`.
- **Manual / integration checks**: load the Task 5 example — `generate(...)` reports no schema
  errors.
- **Risk coverage**: E1, E4.
- **Demo command**: `uv run pytest tests/test_vectorindices.py -q`
- **Expected result**: schema accept/reject unit tests pass.

## Handoff Notes
The `vector_index_schema` key names (`name`, `attribute`, `dimensions`, `distance`, `hash`,
`filters`) are the Prismarine contract and are consumed verbatim by Tasks 2–4. Do not rename.

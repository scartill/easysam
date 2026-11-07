---
generated-by: "Split Tasks"
source: docs/specs/vector-indices.md
generated-at: 2026-11-07T13:30:00+02:00
inputs-ready: false
completed: false
status: not-started
---

# Task 02: Inject SearchSchema attributes into `AttributeDefinitions` (preprocessing)

- [ ] **Completion**
- **Source spec**: `docs/specs/vector-indices.md`
- **Depends on**: `task-01-schema.md`
- **Blocks**: `task-05-example-app.md`, `task-06-tests.md`
- **Parallelism**: `Safe with task-03 and task-04 (different file: load.py)`

## Objective
Ensure every `hash`/`filters` attribute of a vector index is present in the table's
`attributes` list (so the template renders it into `AttributeDefinitions`), deduplicated
strictly against `table['attributes']` and across all indexes on the table (R3).

## Scope & Traceability
- **Requirements / acceptance criteria**: R3.
- **Testing & risk strategy items**: Critique E3 (dedup scope + cross-index dedup); R5
  (no-op for non-vector tables).
- **Out of scope**: rendering `VectorIndexes` (Task 3); the vector `attribute` is NOT injected.

## Implementation Guidance
- **Files to create or modify**:
  - `src/easysam/load.py`: add `process_default_vectorindices(resources_data: dict, errors: list[str])`
    and call it from `preprocess_defaults(...)` **after** `process_default_tables(...)`.
    Logic:
    ```python
    def process_default_vectorindices(resources_data: dict, errors: list[str]):
        for table_name, table in resources_data.get('tables', {}).items():
            vindices = table.get('vectorindices')
            if not vindices:
                continue
            attributes = table.setdefault('attributes', [])
            seen = {a['name'] for a in attributes}        # table.attributes ONLY (Critique E3)
            for vindex in vindices:
                schema_attrs = []
                if vindex.get('hash'):
                    schema_attrs.append(vindex['hash'])
                schema_attrs.extend(vindex.get('filters', []) or [])
                for attr in schema_attrs:
                    if attr not in seen:
                        attributes.append({'name': attr})   # template defaults type -> S
                        seen.add(attr)                       # cross-index dedup
    ```
- **Data/API/UI behaviour**: mutates `table['attributes']` in place. The vector `attribute`
  (embedding) is deliberately NOT added. `seen` seeds from `table['attributes']` only — NOT
  from GSI `indices` — because the template renders `AttributeDefinitions` solely from
  `table.attributes`; seeding from GSI attributes would wrongly skip injecting an attribute
  that is only a GSI key (Critique E3). Updating `seen` as we append makes a filter shared by
  two indexes inject once.
- **Established patterns to follow**: `process_default_tables` (same file) — same signature,
  same in-place mutation style, same registration in `preprocess_defaults`. Prismarine tables
  are merged into `resources_data['tables']` before `preprocess_defaults`, so this step covers
  both literal and Prismarine tables.
- **Constraints and non-goals**: strictly no-op when a table has no `vectorindices`
  (preserves R5 byte-identical output). Do not touch `indices`, `trigger`, `ttl`.

## Verification Requirements
- **Automated tests**: in `tests/test_vectorindices.py`, unit-test `process_default_vectorindices`
  directly on a hand-built `resources_data` dict:
  - hash + filters not already present → appended as `{'name': ...}` in order;
  - an attribute already in `table['attributes']` (e.g. a key) → NOT duplicated;
  - two vector indexes sharing a filter attribute → injected exactly once (Critique E3);
  - an attribute present only in a GSI `indices` block (not in `table.attributes`) → IS
    injected (Critique E3);
  - a table with no `vectorindices` → `attributes` unchanged (R5).
- **Manual / integration checks**: covered by Task 6 end-to-end (attribute appears in rendered
  `AttributeDefinitions`).
- **Risk coverage**: E3, R5.
- **Demo command**: `uv run pytest tests/test_vectorindices.py -q -k preprocess`
- **Expected result**: all preprocessing unit tests green.

## Handoff Notes
Injected attributes carry only `{'name': ...}` so the template's existing `{% if 'type' in
attribute %}... {% else %} AttributeType: S` path applies (default `S`). Users who need `N`/`B`
pre-declare the attribute in `table.attributes` (documented in Task 7, Critique P1).

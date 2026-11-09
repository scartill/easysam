# Task Summary: EasySAM Vector Index Support

- **Source spec**: `docs/specs/vector-indices.md`
- **Task directory**: `docs/tasks/vector-indices/`
- **Status**: `ready`

## Execution Order
1. `task-01-schema.md` — schema in both files; defines the shape everything else consumes.
2. `task-02-preprocess.md` — `load.py` attribute injection (independent file; can run alongside 03/04).
3. `task-03-template-vectorindexes.md` — render `VectorIndexes` in `template.j2` (Tables section).
4. `task-04-template-iam.md` — `SearchVectors` IAM in `template.j2` (Functions section); sequence after 03 (same file).
5. `task-05-example-app.md` — `example/vectorindices/` fixture; needs 01–04 to generate.
6. `task-06-tests.md` — `tests/test_vectorindices.py`; verifies everything; run last.
7. `task-07-docs.md` — README / CLI reference / CHANGELOG; docs-only, parallel with 06.

## Dependencies & Parallel Work
- **Sequential constraints**: 01 → {02, 03, 04} → 05 → 06. 03 → 04 (same file `template.j2`).
- **Safe parallel groups**:
  - Group A after 01: `task-02` (edits `load.py`) can proceed in parallel with the
    `template.j2` pair; within the template pair, do 03 then 04 (or one agent does both).
  - After 05: `task-06` (tests) and `task-07` (docs) are safe in parallel (disjoint files).
- **Shared-file / integration warnings**:
  - `template.j2` is touched by BOTH task-03 (Tables) and task-04 (Functions). Disjoint
    sections, but to avoid a merge conflict have ONE agent own `template.j2` (do 03+04
    together), or strictly sequence 03 then 04.
  - `schemas.json` and `local_schemas.json` are both edited only by task-01.
  - `load.py` is edited only by task-02.

## Coverage Map
| Spec requirement / acceptance criterion | Risk / testing-strategy item | Task(s) | Verification evidence |
|---|---|---|---|
| R1 schema accepts `vectorindices` | E1 (filters⇒hash), E4 (bounds) | 01, 06 | schema accept/reject unit tests |
| R2 `VectorIndexes` rendered | E1 (SearchSchema only w/ hash) | 03, 06 | parsed `template.yml` VectorIndexes assertions |
| R3 SearchSchema attrs in AttributeDefinitions | E3 (dedup scope + cross-index) | 02, 06 | preprocess unit tests + end-to-end AttributeDefinitions |
| R4 `SearchVectors` IAM scoped to index ARN | E2 (null tables guard) | 04, 06 | end-to-end IAM statement + null-tables negative case |
| R5 byte-identical for non-vector tables | R5 | 02, 03, 04, 06 | no-vector guard test |
| R6 working example | — | 05, 06 | `generate(...)` on `example/vectorindices` |
| R7 on-demand billing | — | 03, 06 | `BillingMode == PAY_PER_REQUEST` assertion |
| numeric filter workaround | P1 (recommendation, doc only) | 07 | README note |
| one-index-per-op caveat | P2 (recommendation, doc only) | 07 | CLI reference note |

## Shared Test and Demo Setup
- Runner: `uv run pytest`. New tests: `tests/test_vectorindices.py` (hermetic, no AWS).
- Fixture: `example/vectorindices/` (Task 5). Deploy context: `{'environment': 'vecdev',
  'target_region': 'us-east-1'}`, matching `tests/test_fifoqueue.py`.
- Register SAM tag constructors (`!GetAtt`, `!Sub`, `!Ref`) before `yaml.safe_load`.

## Integration Checkpoint
After all tasks: `uv run pytest -q` (full suite green, no regressions) and
`uv run ruff check` / `uv run ruff format --check` on changed files. Manually inspect
`example/vectorindices/template.yml` for the `VectorIndexes` block and the `searcher`
function's scoped `SearchVectors` policy.

## Open Questions
- None blocking. Deferred (human-review 💡 from critique, NOT applied): E5 (consolidate IAM
  statements), E6 (validate `attribute` disjoint from `hash`/`filters`), P3 (explicit
  Prismarine-output verification checkpoint). These remain in `docs/critiques/vector-indices.md`.

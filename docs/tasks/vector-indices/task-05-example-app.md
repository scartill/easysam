---
generated-by: "Split Tasks"
source: docs/specs/vector-indices.md
generated-at: 2026-11-07T13:30:00+02:00
inputs-ready: false
completed: false
status: not-started
---

# Task 05: Add the `example/vectorindices/` fixture app

- [ ] **Completion**
- **Source spec**: `docs/specs/vector-indices.md`
- **Depends on**: `task-01-schema.md`, `task-02-preprocess.md`, `task-03-template-vectorindexes.md`, `task-04-template-iam.md`
- **Blocks**: `task-06-tests.md`
- **Parallelism**: `Run after 01–04 so it generates; new directory, no file conflicts`

## Objective
Provide a self-contained (hermetic) example app that exercises vector-index provisioning and
`SearchVectors` IAM end-to-end, with no Prismarine runtime dependency (R6).

## Scope & Traceability
- **Requirements / acceptance criteria**: R6; fixture for R1–R5, R7 tests.
- **Testing & risk strategy items**: hermetic test isolation (questionnaire Q4).
- **Out of scope**: Prismarine-sourced generation (verified out of band per seed Q6).

## Implementation Guidance
- **Files to create or modify** (model structure on `example/aoss/` and `example/myapp/`):
  - `example/vectorindices/resources.yaml`: top-level `prefix:` (e.g. `VecExample`) plus a
    literal `tables:` block and a `functions:` block (central form, like
    `example/appwitherrors/resources.yaml`). Define one vector-indexed table, e.g.:
    ```yaml
    prefix: VecExample
    tables:
      Product:
        attributes:
          - name: ProductId
            hash: true
        vectorindices:
          - name: by-embedding
            attribute: Embedding
            dimensions: 1536
            distance: COSINE
            hash: Category
            filters:
              - Brand
    functions:
      searcher:
        resources:
          tables:
            - Product
    ```
    Include a second function that references no vector table (or declares no `tables`) to
    prove the negative/guard cases (Critique E2, R4) — e.g. `plain:` with `resources: {}` or
    `tables: null`.
  - Minimal Lambda source so generation succeeds — mirror `example/myapp/backend/function/
    myfunction/` layout (an `index.py`/handler + any `easysam.yaml`/`uri` EasySAM expects).
    Check how `example/appwitherrors` or `example/myapp` satisfy the `uri`/handler requirement
    and replicate the lightest working form.
- **Data/API/UI behaviour**: must `generate(...)` cleanly with a deploy context like
  `{'environment': 'vecdev', 'target_region': 'us-east-1'}` (match the pattern in
  `tests/test_fifoqueue.py` / `tests/test_dynamottl.py`).
- **Established patterns to follow**: `example/aoss/` (function + table + a search capability)
  and `example/myapp/` (minimal function/table). Keep it as small as possible.
- **Constraints and non-goals**: no Prismarine import; no `thirdparty/` layer unless required.
  Self-contained so `uv run pytest` needs no external services.

## Verification Requirements
- **Automated tests**: Task 6 drives `generate(cliparams, Path('example/vectorindices'), [],
  deploy_ctx)` and asserts on the emitted `template.yml`.
- **Manual / integration checks**: run `generate` and eyeball `example/vectorindices/template.yml`
  for the `VectorIndexes` block and the `searcher` function's `SearchVectors` policy.
- **Risk coverage**: R6; supports E2/E3/R5 negative cases.
- **Demo command**: `uv run pytest tests/test_vectorindices.py -q -k example`
- **Expected result**: example generates with a `VectorIndexes` block and a scoped
  `SearchVectors` policy; no errors.

## Handoff Notes
The generated `example/vectorindices/template.yml` (and any `build/`) is a generation
artifact; follow repo convention (other examples commit `template.yml`? check `.gitignore`
and existing examples) when deciding what to commit.

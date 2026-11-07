---
generated-by: "Split Tasks"
source: docs/specs/vector-indices.md
generated-at: 2026-11-07T13:30:00+02:00
inputs-ready: false
completed: false
status: done
---

# Task 05: Add the `example/vectorindices/` fixture app

- [x] **Completion**
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
- **Files to create or modify** (use the **imported-backend layout**, matching
  `example/fifoqueue/` — NOT a central `functions:` block, and NOT `example/appwitherrors`,
  which is an intentional-failure fixture; Critique T2):
  - `example/vectorindices/resources.yaml`: top-level `prefix:`, `import: [backend]`, and a
    literal `tables:` block with one vector-indexed table:
    ```yaml
    prefix: VecExample
    import:
      - backend
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
    ```
  - `example/vectorindices/backend/function/searcher/easysam.yaml` — a function that
    references the vector table (the imported form flattens `lambda.resources` into
    `functions['searcher']`, so `function.tables` is populated and both `DynamoDBCrudPolicy`
    and `SearchVectors` are emitted; Critique T2):
    ```yaml
    lambda:
      name: searcher
      resources:
        tables:
          - Product
    ```
  - `example/vectorindices/backend/function/searcher/index.py`:
    ```python
    def handler(event, context):
        return {'statusCode': 200, 'body': 'ok'}
    ```
  - `example/vectorindices/backend/function/plain/easysam.yaml` — a second function that
    references **no** tables (proves the negative/guard case for R4/E2). Use `resources: {}`,
    **NOT `tables: null`** — `schemas.json` declares `tables` as `type: array`, so `null`
    fails validation and `scripts/test_examples_generation.py` would fail the whole suite
    (Critique T3):
    ```yaml
    lambda:
      name: plain
      resources: {}
    ```
  - `example/vectorindices/backend/function/plain/index.py`:
    ```python
    def handler(event, context):
        return {'statusCode': 200, 'body': 'ok'}
    ```
  - `example/vectorindices/.gitignore` (so local generation does not dirty the repo; matches
    `example/fifoqueue/.gitignore`, Critique T9):
    ```gitignore
    build
    template.yml
    .aws-sam
    ```
  - The `tables: null` / missing-`tables` Jinja guard (E2) is exercised as a **template unit
    test** on a synthetic dict in Task 6 (bypassing schema validation), not via an example
    fixture (Critique T3).
- **Data/API/UI behaviour**: must `generate(...)` cleanly with a deploy context like
  `{'environment': 'vecdev', 'target_region': 'us-east-1'}` (match the pattern in
  `tests/test_fifoqueue.py` / `tests/test_dynamottl.py`).
- **Established patterns to follow**: `example/fifoqueue/` (imported-backend layout:
  `resources.yaml` with `import: [backend]` + `backend/function/<name>/easysam.yaml`). Keep it
  as small as possible. Do NOT model on `example/appwitherrors` (intentional-failure fixture).
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
The generated `example/vectorindices/template.yml` (and `build/`, `.aws-sam/`) are generation
artifacts ignored by the example's `.gitignore` (mirroring `example/fifoqueue/.gitignore`).
`scripts/test_examples_generation.py` runs `easysam generate` across **every** `example/`
subdir and fails CI if any (except `appwitherrors`) fails — so this fixture MUST validate and
generate cleanly. Do not use `tables: null` anywhere in it (Critique T3).

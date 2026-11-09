# Session: vector-indices
**Started**: 2026-11-07 20:30
**Status**: Active

## Objective
- Add EasySAM CloudFormation support for DynamoDB native vector indexes — the coordinated
  EasySAM-side change for Prismarine PR #4 (which emits a `vectorindices` table-dict block
  that EasySAM previously ignored). Consume that block, render the native
  `AWS::DynamoDB::Table VectorIndexes` property, inject `SearchSchema` attributes into
  `AttributeDefinitions`, and grant referencing functions an index-scoped
  `dynamodb:SearchVectors` IAM statement. Driven end-to-end via the scartill-sdd-lite
  `Autoflow` pipeline.

## Environment
- Shell: PowerShell on Windows (use `;` to chain, not `&&`).
- Generate hermetic example: `uv run easysam --environment vecdev --target-region us-east-1 generate "example\vectorindices\"`
- Generate reacher example: `uv run easysam --environment reacherdev --target-region us-east-1 generate "example\reacher\"`
- Test (feature): `uv run pytest tests/test_vectorindices.py -q`  (33 tests, all pass)
- Test (full suite): `uv run pytest -q`
- Examples harness: `uv run python scripts/test_examples_generation.py`  (22/22 pass)
- Lint/format: `uv run ruff check src/easysam/load.py tests/test_vectorindices.py` ; `uv run ruff format <files>`
- EasySAM branch: `vector-indices` — **pushed** to origin (HEAD `d526608`). Prismarine source pinned to its `vector-indices` git branch via `[tool.uv.sources]`.
- Prismarine checkout: `c:\Users\boris\projects\var\prismarine` on branch `vector-indices`, **pushed** (HEAD `8b5c53c`). The reacher lambda layer installs Prismarine from a local `file://` path (NOT a committed wheel, NOT a git URL — SAM's pip builder accepts `file://` but not git VCS URLs). After editing Prismarine, no rebuild step is needed; just redeploy and SAM reinstalls from `example/reacher/thirdparty/requirements.txt` → `prismarine[vectors] @ file:///C:/Users/boris/projects/var/prismarine`.
- AWS: profile `easysam-a` (account 849099337443), region us-east-1. Live stacks still up:
  `vecidxtest` (hermetic example) and `reacherdev` (reacher). Delete when done:
  `uv run easysam --aws-profile easysam-a --environment <env> delete --await`
- Lambda invoke pattern: `aws lambda invoke --function-name reacher-reacherdev --cli-binary-format raw-in-base64-out --payload file://<json> --profile easysam-a --region us-east-1 <out.json>`
- Orca orchestration run: `run_1f8b875c9c6b` — all Antigravity workers settled/released.

## Key Changes
### EasySAM (branch vector-indices, pushed)
- `src/easysam/schemas.json` + `src/easysam/local_schemas.json`: new `vector_index_schema`
  (name pattern/len, dimensions 1–4096, distance enum, `dependencies: {filters: [hash]}`,
  `filters` `maxItems:18`+`uniqueItems`) and a `vectorindices` array (`maxItems:5`) on
  `tables_schema`.
- `src/easysam/load.py`: `process_default_vectorindices` (wired into `preprocess_defaults`) —
  injects `hash`/`filters` into `table['attributes']` (default `S`), dedup vs `table.attributes`,
  cross-index dedup; defensive vs null tables/attributes; records duplicate-index-name and
  hash-in-filters errors.
- `src/easysam/template.j2`: renders `VectorIndexes` (SearchSchema only when `hash`, HASH
  before INLINE_FILTER) + index-scoped `dynamodb:SearchVectors` policy
  (`!Sub "${<Prefix><Table>.Arn}/index/<name>"`, guarded by `{% if tables %}`).
- `tests/test_vectorindices.py`: 33 tests (incl. imported-local path, flat index, dedup,
  collision rejection, null guard, byte-identical guard).
- `example/vectorindices/`: hermetic fixture (central `Product` + imported `Review` tables,
  `searcher`/`reviewsearcher`/`plain` functions).
- `example/reacher/`: **full Prismarine + Bedrock example** — a `@c.vector_index` Product model, a lambda that embeds via Bedrock Titan (`services: - bedrock`) and indexes/searches through the generated `ProductModel.ByEmbedding.search()`. The lambda layer installs Prismarine from a local `file://` path in `thirdparty/requirements.txt` (no committed wheel; a prior vendored-wheel approach was removed in `d526608`).
- `pyproject.toml`: `[tool.uv.sources]` pins prismarine to the git branch; `boto3>=1.43.89`;
  `numpy` dev dep.
- Docs + SDD artifacts: brainstorm, seed, questionnaire, spec (finalized), 7 tasks + summary,
  2 critiques, code review, feedback.
- Key EasySAM commits: `ac43149` plan, `acf5c49` spec critique, `bbab334` split, `12bf545` task critique, `2a7f60e` implement, `65d1dcf` code review, `2f1e87d` finalize, `c5825ba` imported-path test, `24964ad` reacher example, `80ebe15` reacher finalize, `d526608` wheel → `file://` local path (HEAD, pushed).

### Prismarine (branch vector-indices, pushed — THREE runtime fixes found via live testing)
- `runtime/dynamo_vectors.py` `_format_vector`: emit plain decimal (`Decimal(repr(x))`,
  `format 'f'`) not `str(x)` — scientific notation was rejected by SearchVectors.
- `runtime/dynamo_access.py` `get_client()`: return a standalone low-level dynamodb client,
  NOT `resource.meta.client` (whose `copy_dynamodb_params` handler corrupted the SearchVector).
- `runtime/dynamo_vectors.py` `_search_vectors`: resolve the PHYSICAL table name via
  `get_table(table).name` (like CRUD) instead of the logical model name.
- Prismarine commits: `dcbc24e` decimal format, `f957948` get_client + physical-name, `8b5c53c` uv.lock boto3>=1.43.89 (HEAD, pushed).

## Blockers / Open Questions
- None blocking. Both branches pushed; vector search validated live (Bedrock → Prismarine
  search → correct semantic ranking on two queries in the deployed reacher lambda).
- Two pre-existing, unrelated EasySAM full-suite failures (confirmed on baseline):
  `example/prismapydantic/.../test_item_crud.py` (boto3 NoRegionError, needs creds) and
  `scripts/test_examples_generation.py` (harness `sys.exit(0)` → pytest SystemExit; all
  examples PASS).
- Deferred items in `docs/feedback/2026-11-07-vector-indices.md` (D5 Prismarine→EasySAM
  joint-release integration check; D2 embedding-attribute-disjoint validation).
- Release/versioning deferred: both repos stay on `vector-indices` branches for external
  testing; releases decided later (user to test more first).

## Immediate Next Step
- User performs external testing against the live `reacherdev` / `vecidxtest` stacks, then
  decides on Prismarine + EasySAM releases/versions.
- When testing is done, tear down the stacks:
  `uv run easysam --aws-profile easysam-a --environment reacherdev delete --await` ;
  `uv run easysam --aws-profile easysam-a --environment vecidxtest delete --await`

## Log
- 2026-11-07 20:30: Session captured from ongoing CLI session. Autoflow pipeline for the
  vector-indices feature completed end-to-end (plan → spec critique → split tasks →
  task-level critique → implement → code review → finalize), 7 commits on branch
  `vector-indices`, 30 feature tests passing, product guidance posted to PR #41, all Orca
  workers settled.
- 2026-11-07 22:18: Added imported-local-path test coverage (33 tests). Built the full
  `example/reacher/` Prismarine+Bedrock example (vector index declared via `@c.vector_index`,
  lambda embeds via Bedrock Titan and indexes/searches through the generated client).
  Deployed both `vecidxtest` and `reacherdev` to `easysam-a` and validated live: index +
  vector search work, semantic ranking correct. Found & fixed THREE Prismarine runtime bugs
  (scientific-notation vector formatting; resource-bound get_client corrupting the vector;
  logical-vs-physical table name) with regression tests — Prismarine suite 57 pass. Pinned
  EasySAM to the Prismarine git branch, vendored the fixed wheel for the lambda layer.
  **Pushed both branches** (easysam `80ebe15`, prismarine `f957948`). Releases/versions
  deferred pending further external testing by the user.
- 2026-11-10 00:36: Replaced the committed binary wheel with a local `file://` Prismarine reference in `example/reacher/thirdparty/requirements.txt` (SAM's pip builder accepts `file://` but not git VCS URLs; same pattern as `botobuddy @ file:///...`). Removed the wheel and the `.gitignore` override. Verified the layer builds with all three fixes and the live `reacherdev` search still returns correct rankings. Committed+pushed EasySAM `d526608`. Also committed+pushed Prismarine `8b5c53c` (uv.lock bump to boto3 1.43.126 for the `[vectors]` boto3>=1.43.89 floor). Both repos clean and synced with origin; both `reacherdev` + `vecidxtest` stacks still live on `easysam-a` for user testing. Awaiting user feedback; releases/versions still deferred.

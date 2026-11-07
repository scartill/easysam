# Code Review: DynamoDB Vector Indexes (`vector-indices`)

**Reviewed**: 2026-11-07
**Author**: Boris Resnick
**Branch**: vector-indices → main (commit 2a7f60e)
**Decision**: REQUEST CHANGES

> **Resolution (coordinator, Autoflow `--auto`)**: Applied HIGH #1 (defensive null/empty
> handling in `process_default_vectorindices`) and MEDIUM #2 (`uniqueItems` on `filters`),
> #3 (reject hash-in-filters), #4 (reject duplicate index names), #5 (`{% if tables %}` guard).
> Also applied LOW #6 (`validate_local` + flat-index tests), #7 (clarified test name/docstring),
> #8 (`errors` param now used by #3/#4), #9 (README single-index caveat cross-reference).
> 9 new tests added (30 total, all passing); full suite shows only the two pre-existing,
> unrelated failures (`prismapydantic` NoRegionError; `test_examples_generation` SystemExit:0
> harness quirk — all 21 examples PASS).

## QA & Verification Guidance
- **Risk Assessment & Migration Notes**:
  - **Single Index Change Per Stack Operation**: While initial table creation allows multiple vector indexes and GSIs simultaneously, AWS CloudFormation only permits one index addition or deletion per stack update operation on an existing table. Adding multiple vector indexes or combining a vector index addition with a GSI modification on an active stack will cause CloudFormation stack rollback.
  - **Billing Mode Prerequisite**: DynamoDB native vector indexes require on-demand capacity (`BillingMode: PAY_PER_REQUEST`). EasySAM already hardcodes on-demand billing, so no billing mode drift occurs.
  - **Attribute Type Default**: Injected `hash` and `filters` attributes default to string (`S`). For numeric (`N`) or binary (`B`) filters, users must explicitly pre-declare the attribute with `type: N` or `type: B` in `table.attributes`.
- **Behavioral Changes to Verify**:
  - Tables declaring a `vectorindices` block produce an `AWS::DynamoDB::Table` resource with a valid `VectorIndexes` property and updated `AttributeDefinitions`.
  - Lambdas that list a vector-indexed table in `tables` receive an inline IAM policy statement with `Action: [dynamodb:SearchVectors]` scoped strictly to the index ARN (`${TableLogicalId.Arn}/index/${IndexName}`).
  - Lambdas referencing non-vector tables, or tables without vector indexes, generate byte-identical output with no `dynamodb:SearchVectors` permissions.
- **Testing Hints for QA**:
  1. *Flat Vector Index*: Verify that a vector index defined without `hash` and `filters` (a flat similarity index) generates a valid `VectorIndexes` block without a `SearchSchema` property, and does not inject spurious attributes into `AttributeDefinitions`.
  2. *Cross-Index Dedup*: Verify that two vector indexes on the same table sharing identical partition or filter attributes only declare that attribute once in `AttributeDefinitions`.
  3. *Null/Empty Defensiveness*: Verify that functions without `tables` (or with `resources: {}`) generate cleanly without Jinja errors, and functions referencing vector tables obtain proper index-scoped permissions.

## Technical Summary
The implementation cleanly consumes Prismarine's `vectorindices` table block and renders native DynamoDB `VectorIndexes` and scoped `dynamodb:SearchVectors` IAM policies following established EasySAM idioms (Approach C hybrid split). However, changes are requested to address an unhandled `TypeError` crash in `process_default_vectorindices` when table attributes or tables are null, along with schema validation gaps that permit duplicate filter names, duplicate index names, and collision between `hash` and `filters` to emit invalid CloudFormation.

## Findings

### CRITICAL
None

### HIGH

1. **Unhandled `TypeError` / `AttributeError` in `process_default_vectorindices` on `null` attributes or tables**
   - **File**: `src/easysam/load.py#L388-L393`
   - **Description**: In `process_default_vectorindices`:
     ```python
     attributes = table.setdefault('attributes', [])
     seen = {a['name'] for a in attributes}
     ```
     If a table defines `attributes: null` (or has an empty `attributes:` key in YAML), `table.setdefault('attributes', [])` returns `None` because the key already exists in `table`. Line 393 then executes `{a['name'] for a in attributes}`, raising an unhandled `TypeError: 'NoneType' object is not iterable`. Furthermore, if a table entry is empty (e.g. `Product:` with no sub-keys in YAML), line 389 raises `AttributeError: 'NoneType' object has no attribute 'get'`. Because `preprocess_defaults` executes before JSON Schema validation, this causes `easysam generate` to crash with an unhandled Python traceback instead of producing a friendly schema validation error.
   - **Recommendation**: Guard defensively (as recommended in Task Critique T4):
     ```python
     for table_name, table in (resources_data.get('tables') or {}).items():
         if not isinstance(table, dict):
             continue
         vindices = table.get('vectorindices')
         if not vindices:
             continue
         attributes = table.get('attributes')
         if attributes is None:
             attributes = []
             table['attributes'] = attributes
         seen = {a['name'] for a in attributes if isinstance(a, dict) and 'name' in a}
     ```

### MEDIUM

2. **Missing `uniqueItems: true` on `filters` produces invalid CloudFormation on duplicate filters**
   - **Files**: `src/easysam/schemas.json#L524`, `src/easysam/local_schemas.json#L245`
   - **Description**: The `filters` schema is declared as `"filters": {"type": "array", "items": {"type": "string"}, "maxItems": 18}` without `"uniqueItems": true`. If a user enters duplicate filter names (e.g. `filters: ["Brand", "Brand"]`), schema validation passes. While `load.py` deduplicates when injecting into `table.attributes`, `src/easysam/template.j2` (lines 470–473) iterates `vindex.filters` directly:
     ```yaml
     - AttributeName: Brand
       SearchSchemaElementType: INLINE_FILTER
     - AttributeName: Brand
       SearchSchemaElementType: INLINE_FILTER
     ```
     CloudFormation rejects templates with duplicate attribute names in `SearchSchema` during stack deployment.
   - **Recommendation**: Add `"uniqueItems": true` to the `filters` schema definition in both `schemas.json` and `local_schemas.json`.

3. **Collision between `hash` partition key and `filters` is not validated**
   - **Files**: `src/easysam/load.py#L394-L402`, `src/easysam/template.j2#L466-L473`
   - **Description**: Neither schema validation nor `process_default_vectorindices` checks whether the `hash` partition key is also included in `filters`. If a user specifies `hash: Category` and `filters: ["Category"]`, validation succeeds, and `template.j2` emits `Category` twice in `SearchSchema` (once as `HASH` and once as `INLINE_FILTER`). DynamoDB rejects this with a `ValidationException` because an attribute cannot simultaneously act as an index partition key and an inline filter.
   - **Recommendation**: In `process_default_vectorindices` or `validate_schema.py::validate_tables`, check that `vindex.get('hash') not in (vindex.get('filters') or [])` and raise/record an error.

4. **Duplicate vector index names on the same table are not rejected**
   - **Files**: `src/easysam/schemas.json#L602-L607`, `src/easysam/local_schemas.json#L323-L328`
   - **Description**: The `vectorindices` array definition allows multiple vector indexes with identical `name` values on the same table. If two indexes share the same name, EasySAM generates duplicate `VectorIndex` entries under `VectorIndexes` in CloudFormation and emits duplicate `dynamodb:SearchVectors` policy statements with identical ARNs in referencing functions. DynamoDB requires index names to be unique within a table.
   - **Recommendation**: In `validate_schema.py::validate_tables`, verify that vector index names are unique per table and do not collide with GSI names.

5. **`tables is defined` in `template.j2` raises `UndefinedError` if `tables` is `None`**
   - **File**: `src/easysam/template.j2#L623`
   - **Description**: Line 623 uses `{% if tables is defined %}` before executing `{% for table_name, table in tables.items() %}`. In Jinja2, if `tables` is in context with a value of `None` (for instance, when `resources.yaml` contains `tables: null`), `tables is defined` evaluates to `True`, but `tables.items()` raises `jinja2.exceptions.UndefinedError: 'None' has no attribute 'items'`.
   - **Recommendation**: Change line 623 to `{% if tables %}` or `{% if tables is defined and tables %}`.

### LOW

6. **Missing test coverage for `local_schemas.json` and flat vector indexes**
   - **File**: `tests/test_vectorindices.py#L35-L39, L67-L126`
   - **Description**: All schema acceptance/rejection tests in `test_vectorindices.py` run against `schemas.json` via `validate()`. `local_schemas.json` (tested via `validate_local()`) has zero test coverage for the new `vector_index_schema` definition. Additionally, there is no unit test verifying that a vector index without `hash` (a flat vector index without `SearchSchema`) passes schema validation and renders correctly with `SearchSchema` omitted.
   - **Recommendation**: Add test cases in `tests/test_vectorindices.py` for `validate_local()` and for a flat vector index without `hash`.

7. **Synthetic `tables: None` test does not test `tables: None`**
   - **File**: `tests/test_vectorindices.py#L357-L401`
   - **Description**: `test_template_null_tables_guard_does_not_crash` is documented as verifying the Jinja null-guard on a synthetic dictionary where a function has `tables: None`. However, the test actually passes `'tables': []` because the legacy `DynamoDBCrudPolicy` loop (`template.j2#L619`) crashes on `None`. The test name and docstring are misleading relative to the assertion executed.
   - **Recommendation**: Clarify the docstring and test name, or guard line 619 with `{% if function.tables %}` so `tables: None` can be tested directly.

8. **Unused `errors` parameter in `process_default_vectorindices`**
   - **File**: `src/easysam/load.py#L387`
   - **Description**: `process_default_vectorindices(resources_data: dict, errors: list[str])` accepts `errors`, but never uses it.
   - **Recommendation**: Either use `errors` to record semantic issues (such as duplicate index names or hash-in-filter collisions) or document why it remains unused for signature consistency with other `process_default_*` methods.

9. **Single-index stack update caveat omitted from `README.md`**
   - **File**: `README.md#L250-L304`
   - **Description**: `docs/CLI_REFERENCE.md` documents the critical DynamoDB/CloudFormation operational caveat that only one index can be added or removed per stack update on an existing table. `README.md` details the vector indices syntax and numeric type workaround, but omits this operational constraint, leaving developers updating existing stacks unaware of update rollbacks.
   - **Recommendation**: Add a brief operational note or cross-reference to `docs/CLI_REFERENCE.md` in `README.md` under `### Vector indices`.

## Validation Results

| Check | Result |
|---|---|
| Type check | Pass (`uv run pytest tests/test_vectorindices.py -q`: 21 passed) |
| Lint | Pass (`uv run ruff check src/easysam/load.py tests/test_vectorindices.py`: all checks passed) |
| Tests | Pass (21/21 vector-indices unit and end-to-end tests pass in 0.94s) |
| Build / Generation | Pass (`easysam generate example/vectorindices/` succeeds and emits valid SAM YAML) |

## Files Reviewed
- `src/easysam/schemas.json` — Modified (Added `vector_index_schema` definition and `vectorindices` property)
- `src/easysam/local_schemas.json` — Modified (Added `vector_index_schema` definition and `vectorindices` property)
- `src/easysam/load.py` — Modified (Added `process_default_vectorindices` and wired into `preprocess_defaults`)
- `src/easysam/template.j2` — Modified (Rendered `VectorIndexes` in Tables section and scoped `SearchVectors` IAM statement in Functions section)
- `tests/test_vectorindices.py` — Added (21 unit and end-to-end test cases)
- `example/vectorindices/` — Added (Hermetic fixture app with `plain` and `searcher` functions and vector-indexed `Product` table)
- `README.md` — Modified (Documented `vectorindices` syntax and numeric filter workaround)
- `docs/CLI_REFERENCE.md` — Modified (Documented `vectorindices` reference and single-index stack update caveat)
- `CHANGELOG.md` — Modified (Added release notes for DynamoDB vector index support)
- `example/README.md` — Modified (Documented `vectorindices` example app)

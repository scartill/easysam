---
generated-by: "Brainstorm"
generated-at: 2026-11-07T12:00:00+02:00
status: recommended
---

# Technical Brainstorm: EasySAM CloudFormation Support for DynamoDB Vector Indexes

## Problem Statement & Scope

- **Core Objective:** Teach EasySAM to render DynamoDB **native vector indexes** into
  CloudFormation. Prismarine PR #4 ("Vector Indices") now emits a `vectorindices` block
  into the EasySAM table dict, but EasySAM silently ignores it. We must consume that block
  and emit the official `AWS::DynamoDB::Table` `VectorIndexes` property so declared vector
  indexes actually get provisioned.
- **Scope Boundaries:**
  - **IN:** schema (`schemas.json` + `local_schemas.json`) acceptance of a `vectorindices`
    key on a table; Jinja (`template.j2`) rendering of `VectorIndexes` + required
    `AttributeDefinitions` for `hash`/`filters` attributes; `BillingMode` handling (vector
    indexes require `PAY_PER_REQUEST`, already hardcoded); custom validation; an
    `example/` fixture; tests mirroring `test_fifoqueue.py`/`test_dynamottl.py`; a
    README/CLI-reference note.
  - **OUT:** Generating embeddings; the `SearchVectors` runtime path (that lives in
    Prismarine's generated client, not EasySAM); IAM policy wiring for
    `dynamodb:SearchVectors` (open question — see Q4); provisioned-throughput billing;
    changing GSI (`indices`) semantics; multi-region/global-table vector replication
    specifics beyond what a single `AWS::DynamoDB::Table` renders.
- **Key Constraints:**
  - The Prismarine→EasySAM contract is a list of dicts under `table['vectorindices']`, each:
    `{name, attribute, dimensions, distance, hash?, filters?}` (see Background for the exact
    emitter). EasySAM owns the CloudFormation mapping.
  - Models/tables **without** a vector index must produce **byte-identical** template output
    to today (the `write_result` blank-line strip + Jinja whitespace mean any new block must
    be fully guarded by `{% if table.vectorindices %}`).
  - Vector indexes require on-demand billing (`BillingMode: PAY_PER_REQUEST`) — EasySAM
    already hardcodes this, so the invariant holds, but see the single-index CloudFormation
    caveat (Q3).

## Technical Baseline & External Research

### Current Architecture (local codebase audit)

- **Rendering is pure Jinja2 over a plain dict.** `src/easysam/generate.py::generate`
  loads `resources_data`, builds a Jinja `Environment`, and renders `src/easysam/template.j2`
  with the whole dict as context. No troposphere/Mako; the DynamoDB table block lives in
  `template.j2` (the `# Tables` section). It reads `table.attributes` →
  `AttributeDefinitions` + `KeySchema`, `table.indices` → `GlobalSecondaryIndexes` (guarded
  by `{% if table.indices %}`, `Projection: ProjectionType: ALL` hardcoded), `BillingMode:
  PAY_PER_REQUEST` **hardcoded**, `PointInTimeRecoverySpecification` hardcoded on,
  `table.trigger` → `StreamSpecification`, `table.ttl` → `TimeToLiveSpecification`.
- **Two entry paths for the table dict.** (a) A literal `tables:` block in
  `resources.yaml`/imported `easysam.yaml`; (b) synthesized from Prismarine models via
  `load.py::preprocess_prismarine` → `prismarine_dynamo_tables` →
  `prisma_easysam.build_dynamo_tables`. Both converge on the same shape, so EasySAM must
  accept `vectorindices` from both the schema (`tables_schema`) and the local schema
  (`local_schemas.json`, for imported files).
- **Validation is JSON Schema (Draft7) + custom Python.** `schemas.json` defines
  `tables_schema` (with `"additionalProperties": false`, so a new `vectorindices` key **must**
  be added or validation rejects it), `table_attribute_schema`, and the `indices` structure.
  `local_schemas.json` duplicates the `indices`/table structure for imported files.
  `validate_schema.py::validate_tables` holds custom rules (currently only checks trigger
  function existence).
- **Testing conventions.** `pytest`, invoked `uv run pytest`. Generation tests
  (`test_fifoqueue.py`, `test_dynamottl.py`) register SAM-tag YAML constructors, call
  `generate(cliparams, example_path, [], deploy_ctx)` against an `example/` fixture, assert
  `not errors`, then `yaml.safe_load` the written `template.yml` and assert on the parsed
  **dict** structure. `test_fifoqueue.py` additionally unit-tests schema acceptance/rejection
  by calling `validate(...)` directly. This is the pattern to copy.

### State of the Art — DynamoDB Native Vector Search (GA 2026-08-05)

DynamoDB native vector search went GA August 2026. Vector indexes are managed through the
same `CreateTable`/`UpdateTable` APIs via a `VectorIndexes` parameter, and queried with the
separate `SearchVectors` API. Key facts verified against AWS docs:

- Up to 5 vector indexes per table; `1 <= dimensions <= 4096`; `TopK <= 100`; results are
  eventually consistent; **on-demand billing required**.
- `SearchVectors` uses a dedicated vector endpoint and needs `dynamodb:SearchVectors`
  permission on the **index** ARN (`.../table/<t>/index/<i>`), not the table ARN.
  (Rephrased from AWS docs for licensing compliance.)

### CloudFormation support — the decisive finding

**CloudFormation *does* natively support vector indexes.** `AWS::DynamoDB::Table` has a
`VectorIndexes` property (array of `VectorIndex`). The official reference
(`aws-properties-dynamodb-table-vectorindex`) gives this shape:

```yaml
VectorIndexes:
  - IndexName: <string>            # required; pattern [a-zA-Z0-9_.-]+, len 3..255
    Dimensions: <int>             # required; 1..4096
    DistanceFunction: <string>    # required; COSINE | DOT_PRODUCT | EUCLIDEAN
    VectorAttribute:              # required
      AttributeName: <string>     #   the item attribute holding the embedding
    Projection:                   # required (same Projection type as a GSI)
      ProjectionType: ALL         #   e.g. ALL / KEYS_ONLY / INCLUDE
    SearchSchema:                 # optional; array, min 1 when present
      - AttributeName: <string>   #   must ALSO be in table AttributeDefinitions
        SearchSchemaElementType: HASH | INLINE_FILTER
```

Two load-bearing constraints straight from the CloudFormation docs, both of which shape the
design (rephrased for licensing compliance):

1. **Every `SearchSchema` attribute must also be declared in the table's
   `AttributeDefinitions`** — exactly like GSI key attributes — or the request fails with a
   `ValidationException`. **This directly contradicts Prismarine's Critique E5**, which
   assumed vector `hash`/`filters` attributes must be kept *out* of `AttributeDefinitions`.
   For CloudFormation that assumption is wrong: they must be *added*. (See Q2.)
2. **"In a single stack operation, you can create or delete one index — a GSI or a vector
   index, but not one of each."** So a stack update that simultaneously adds a GSI *and* a
   vector index (or two indexes at once) will be rejected by CloudFormation. This is an
   operational caveat for users, and a candidate for a documented warning. (See Q3.)

- `VectorIndexes` is `Update requires: No interruption`, but each sub-property is
  `Update requires: Updates are not supported` — i.e. index definitions are effectively
  immutable once created (add/remove, not mutate).
- `BillingMode: PAY_PER_REQUEST` is required for vector indexes; EasySAM already hardcodes it.

### The Prismarine→EasySAM contract (exact)

`prisma_easysam.build_dynamo_tables` emits, per table, when vector indexes exist:

```python
result[short_name]['vectorindices'] = [
  { 'name': <str>, 'attribute': <str>, 'dimensions': <int>, 'distance': <str>,
    'hash': <str>,            # present only when truthy
    'filters': [<str>, ...]   # present only when non-empty
  }, ...
]
```

Note the field-name mapping EasySAM must perform:
`name`→`IndexName`, `attribute`→`VectorAttribute.AttributeName`, `dimensions`→`Dimensions`,
`distance`→`DistanceFunction`, `hash`→`SearchSchema[HASH]`, each `filters` entry →
`SearchSchema[INLINE_FILTER]`. Prismarine deliberately did **not** add `hash`/`filters` to
`attributes`; per finding #1 above, EasySAM must inject them into `AttributeDefinitions`
itself.

## Open Questions & User Clarifications

#### Q1: Field-name convention in the EasySAM `vectorindices` dict
- **Context:** Prismarine emits keys `name`, `attribute`, `dimensions`, `distance`, `hash`,
  `filters`. The alternative is to have EasySAM's schema speak CloudFormation's own
  vocabulary (`IndexName`, `DistanceFunction`, …). Since EasySAM must accept whatever
  Prismarine emits (the whole point of the coordinated change), I propose the EasySAM schema
  and template consume Prismarine's lowercase keys verbatim and do the CFN mapping inside
  `template.j2`. Confirm, or state if you'd prefer EasySAM to also accept a
  CloudFormation-cased hand-written form.
- **User Input:**
    <!-- USER_INPUT_START:Q1 -->
    accept Prismarine style and map
    <!-- USER_INPUT_END:Q1 -->

#### Q2: AttributeDefinitions for `hash` / `filters` (resolve the E5 contradiction)
- **Context:** CloudFormation requires every `SearchSchema` attribute to also appear in the
  table's `AttributeDefinitions` (type `S`/`N`/`B`), like GSI keys. Prismarine's E5 kept them
  out. EasySAM must therefore add them. But their **type** matters: a `HASH`/`INLINE_FILTER`
  attribute could be `S` (string) or `N` (number), and the Prismarine `vectorindices` block
  carries **no type information** for these. Options:
  (a) default all injected vector-schema attributes to `AttributeType: S` (matching EasySAM's
      existing default for GSI attributes; simplest, and strings are the common filter case);
  (b) extend the contract so Prismarine emits a type per `hash`/`filter` attribute (requires
      another coordinated Prismarine change);
  (c) require the attribute to already be declared as a table/GSI key (reuse its type) and
      only inject when absent, defaulting to `S`.
  I lean (a) for this pass with a documented limitation, since EasySAM already defaults GSI
  attributes to `S`. Confirm the default type and whether numeric filters are needed now.
- **User Input:**
    <!-- USER_INPUT_START:Q2 -->
    (a)
    <!-- USER_INPUT_END:Q2 -->

#### Q3: The CloudFormation "one index per stack operation" caveat
- **Context:** CloudFormation rejects a single stack operation that creates/deletes more than
  one index, or mixes a GSI and a vector index in the same operation. A user who adds a vector
  index and a GSI to an existing table in one `easysam deploy` will get a CloudFormation
  error. Options: (a) document the caveat only (no code); (b) add a custom validation
  *warning* in `validate_schema.py` when a table declares both new GSIs and vector indexes in
  a way we can detect (note: EasySAM generates full templates and can't easily know the
  *current* deployed state, so true detection is limited to "has both `indices` and
  `vectorindices`"); (c) nothing. I lean (a) — document it in the README/CLI reference — since
  EasySAM is declarative and can't see deployed state. Confirm.
- **User Input:**
    <!-- USER_INPUT_START:Q3 -->
    (a)
    <!-- USER_INPUT_END:Q3 -->

#### Q4: IAM permissions for `dynamodb:SearchVectors`
- **Context:** Searching a vector index needs `dynamodb:SearchVectors` on the **index** ARN
  (`arn:aws:dynamodb:<region>:<acct>:table/<t>/index/<i>`), which differs from normal table
  IAM. Does EasySAM currently auto-generate table-access IAM policies for functions (e.g. a
  `DynamoDBCrudPolicy` per function/table), and if so, should this change also emit a
  `SearchVectors` permission for functions that use a vector-indexed table? Or is IAM for
  vector search out of scope for this pass (caller wires it manually)? I lean **out of scope**
  for the first pass to keep the change focused on provisioning, with a documented follow-up.
  Confirm.
- **User Input:**
    <!-- USER_INPUT_START:Q4 -->
    No, if function definitions reference tables with vertor indices, the functins shall be able to use them. This pass shall yield a simple one-function vector index access working example.
    <!-- USER_INPUT_END:Q4 -->

#### Q5: Projection type
- **Context:** `VectorIndex.Projection` is required. EasySAM hardcodes `ProjectionType: ALL`
  for GSIs. Prismarine's `vectorindices` block carries no projection info. I propose hardcode
  `ProjectionType: ALL` for vector indexes too (consistent, simplest, matches GSI behavior).
  Confirm, or specify if KEYS_ONLY/INCLUDE must be configurable now.
- **User Input:**
    <!-- USER_INPUT_START:Q5 -->
    accept
    <!-- USER_INPUT_END:Q5 -->

#### Q6: Version floor / coordination with Prismarine
- **Context:** The Prismarine spec says to document "requires EasySAM ≥ X". What EasySAM
  version should this land as (for the README note and CHANGELOG), and should we also bump the
  `aws-sam-cli`/CloudFormation toolchain floor to ensure `VectorIndexes` is recognized at
  `sam validate`/deploy time? (The property is new; older SAM CLIs may warn.) I can check the
  installed `aws-sam-cli` version if helpful.
- **User Input:**
    <!-- USER_INPUT_START:Q6 -->
    We will publish Prismarine/EasySAM simultaneously when the feature is ready. This branch shall use corresponding Prismarine branch while the feature is in development.
    <!-- USER_INPUT_END:Q6 -->

### Baseline assumptions if questions are left at defaults

- **Q1:** EasySAM schema + template consume Prismarine's lowercase keys (`name`, `attribute`,
  `dimensions`, `distance`, `hash`, `filters`) and map to CloudFormation casing in the template.
- **Q2:** Inject `hash`/`filters` attributes into `AttributeDefinitions` as `AttributeType: S`
  when not already declared; document the string-only limitation. (Overturns Prismarine E5 for
  the CloudFormation layer, as the official docs require.)
- **Q3:** Document the "one index per stack operation" CloudFormation caveat; no blocking
  validation.
- **Q4:** IAM `SearchVectors` wiring is **out of scope** for this pass; documented follow-up.
- **Q5:** Hardcode `Projection: ProjectionType: ALL` for vector indexes.
- **Q6:** Land as the next minor version; verify (not necessarily bump) the SAM CLI floor.

---

## Resolved Decisions (from user answers)

| Q | Decision |
|---|----------|
| Q1 | EasySAM accepts Prismarine's lowercase keys (`name`, `attribute`, `dimensions`, `distance`, `hash`, `filters`) and maps to CloudFormation casing inside `template.j2`. |
| Q2 | Option (a): inject `hash`/`filters` attributes into `AttributeDefinitions` as `AttributeType: S` when not already present; string-only limitation documented. |
| Q3 | Document the CloudFormation "one index change per stack operation" caveat; no blocking validation. |
| Q4 | **IAM in scope.** A function that references a vector-indexed table must receive `dynamodb:SearchVectors` on the index ARN. This pass must ship a working single-function vector-index access example. |
| Q5 | Hardcode `Projection: ProjectionType: ALL` for vector indexes (matches GSI behavior). |
| Q6 | Ship EasySAM + Prismarine together when ready; during development this EasySAM branch tracks the corresponding Prismarine `vector-indices` branch. No standalone version floor; coordinate at publish time. |

## Architectural Approaches Evaluated

All approaches share the same skeleton (the only realistic CloudFormation target is the
native `AWS::DynamoDB::Table` `VectorIndexes` property). They differ in **where the
attribute-injection and IAM cross-referencing logic lives** — in the Jinja template vs. in
Python preprocessing (`load.py`). This is the real design axis, because EasySAM's philosophy
is "plain dict in, Jinja out," and the vector feature needs two derived facts the raw
Prismarine block does not contain: (1) the `AttributeDefinitions` entries for `hash`/`filters`,
and (2) which functions reference a vector-indexed table.

### Approach A: Template-centric (all logic in `template.j2`)

- **Concept:** Add `vectorindices` to the schema as-is. Do everything else in Jinja: render
  `VectorIndexes` from `table.vectorindices`; in the `AttributeDefinitions` loop, additionally
  emit `hash`/`filters` names (deduped against existing attributes via a Jinja `namespace`);
  in the function `Policies:` loop, cross-reference `tables.items()` to find vector-indexed
  tables the function lists in `function.tables` and emit a `SearchVectors` inline statement.
- **Component Changes:** `schemas.json` + `local_schemas.json` (`vectorindices` property +
  `vector_index_schema`); `template.j2` (VectorIndexes block, AttributeDefinitions dedup,
  SearchVectors policy); new `example/` app; `tests/test_vectorindices.py`; docs.
- **Dependencies Introduced:** None.

### Approach B: Preprocess-centric (derive in `load.py`, thin template)

- **Concept:** Keep Jinja dumb. In `load.py` preprocessing, after tables are assembled
  (covering both the Prismarine path and literal `tables:`), (1) merge each vector index's
  `hash`/`filters` into the table's `attributes` list as `{name, type: 'S'}` when absent, so
  the existing `AttributeDefinitions` loop renders them with zero template change; and (2)
  compute a per-function derived list (e.g. `function._vector_access = [{table, index}, ...]`)
  by cross-referencing `function.tables` against vector-indexed tables. The template then only
  adds a straightforward `VectorIndexes` block and a simple `SearchVectors` loop over the
  precomputed list.
- **Component Changes:** `schemas.json` + `local_schemas.json`; `load.py` (new
  `process_default_vectorindices` / attribute-merge + function-access derivation step wired
  into `preprocess_defaults`); `template.j2` (VectorIndexes block + simple SearchVectors loop);
  new `example/` app; tests (both `load`-level unit tests and end-to-end generation); docs.
- **Dependencies Introduced:** None.

### Approach C: Hybrid — attributes in preprocessing, IAM + VectorIndexes in template

- **Concept:** Do the one genuinely awkward-in-Jinja thing (injecting `AttributeDefinitions`
  entries without duplicates, respecting the existing `attributes` list) in `load.py`, where
  Python set logic is natural and testable. Leave the two things that are natural in Jinja —
  rendering the `VectorIndexes` block and the `SearchVectors` policy cross-reference (the
  template already does exactly this kind of `tables.items()` cross-reference for stream
  triggers) — in `template.j2`.
- **Component Changes:** `schemas.json` + `local_schemas.json`; `load.py` (small, focused
  attribute-merge preprocessing step with unit tests); `template.j2` (VectorIndexes block +
  SearchVectors policy loop mirroring the stream-trigger precedent); new `example/` app;
  tests; docs.
- **Dependencies Introduced:** None.

## Structured Comparison & Methodology

### SWOT Matrix

| Approach | Strengths | Weaknesses | Opportunities | Threats/Risks |
|---|---|---|---|---|
| **A: Template-centric** | One file to change; no new Python path; matches "dict in, Jinja out" purity | AttributeDefinitions dedup in Jinja is fiddly (`namespace` + nested loops), hard to unit-test, easy to break byte-identical output; whitespace risk | Keeps load.py untouched | Dedup bugs surface only in rendered YAML; low testability of the trickiest logic |
| **B: Preprocess-centric** | Highly testable (pure-dict unit tests at load level); template stays trivial; reuses existing `attributes` rendering untouched | Mutating `attributes` in preprocessing blurs the Prismarine contract (EasySAM now edits the table dict); two-place reasoning; slightly more code | Establishes a clean pattern for future derived table facts | Mutating shared table dict could interact with other preprocessing/sorting; must preserve byte-identical output for non-vector tables |
| **C: Hybrid** | Python handles the one hard thing (attribute dedup) with real unit tests; IAM cross-ref stays in Jinja where an identical precedent (stream trigger) already exists; minimal, legible template diff | Logic in two places (but each where it's most natural) | Mirrors existing EasySAM idioms on both sides; easiest to review against precedent | Must still guard non-vector output byte-identically (shared by all approaches) |

## Recommendation

**Adopt Approach C (Hybrid).**

The decisive factors:

1. **Attribute injection belongs in Python.** CloudFormation requires every `SearchSchema`
   attribute to also be in `AttributeDefinitions`, deduplicated against the table's existing
   key/GSI attributes. Expressing "add these names if not already present" in Jinja needs a
   `namespace` accumulator and nested loops that are brittle and nearly untestable; the same
   logic in `load.py` is a few lines of set arithmetic with direct unit tests. This is exactly
   the kind of derived fact preprocessing exists for (`process_default_tables` already
   normalizes triggers there).

2. **IAM cross-referencing belongs in the template.** EasySAM *already* emits a per-function
   DynamoDB inline policy by iterating `tables.items()` and matching `table.trigger.function ==
   function_name` (the stream-trigger block). The `SearchVectors` permission is the same shape:
   iterate tables, keep those with `vectorindices` that the function lists in `function.tables`,
   emit a statement scoped to `!Sub "${TableLogicalId.Arn}/index/<name>"`. Reusing an existing,
   reviewed idiom minimizes risk and reviewer surprise, and keeps the derived-state surface in
   `load.py` small.

3. **The `VectorIndexes` block itself is pure, guarded rendering** — trivially Jinja, fully
   guarded by `{% if table.vectorindices %}`, preserving byte-identical output for every
   existing table.

Approach A loses on testability of its hardest part; Approach B is clean but pushes the
easy-and-precedented IAM logic into Python for no benefit and does *all* attribute mutation in
preprocessing. C splits along the natural grain.

### Key Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| **Byte-identical regression** for non-vector tables (Jinja whitespace + `write_result` blank-line strip). | Fully guard every new block with `{% if table.vectorindices %}` / `{% if ... %}`; add a test asserting an existing example's `template.yml` is unchanged, and assert on parsed-dict equality for a no-vector table. |
| **`AttributeDefinitions` duplication** (a `hash`/`filter` attr that is already a table/GSI key) → CloudFormation rejects duplicate AttributeName. | Dedup in `load.py` against the union of existing table + GSI attribute names before injecting; unit-test the dedup (attr already present → not re-added; type preserved). |
| **Wrong attribute type** (numeric filter emitted as `S`). | Per Q2(a), default `S` and document the string-only limitation; leave a seam to extend the contract later (Prismarine could emit types). |
| **CloudFormation "one index per stack operation"** → deploy fails when adding a GSI and a vector index together, or two indexes at once. | Per Q3, document the caveat prominently in README/CLI reference; note it's a CloudFormation/service limit, not EasySAM. |
| **Vacuous/partial Prismarine contract** (a `vectorindices` entry missing `attribute`/`dimensions`). | Schema `required: [name, attribute, dimensions, distance]` on `vector_index_schema` catches it at validation time with a clear error. |
| **Stale Prismarine branch coupling** (Q6: develop against a branch, publish together). | Pin the dev dependency to the Prismarine `vector-indices` branch during development; add a CHANGELOG entry noting the coordinated release; verify the end-to-end example regenerates against that branch. |
| **SAM CLI / CloudFormation not recognizing `VectorIndexes`** at validate time. | Verify the installed `aws-sam-cli` accepts the property during the example test (generation + optional `sam validate`); document a minimum toolchain if a problem surfaces. |
| **IAM ARN construction wrong** (index sub-resource ARN). | Scope via `!Sub "${{TableLogicalId}.Arn}/index/<name>"`; validate the rendered ARN shape in the example test (parse `template.yml`, assert the `Resource` string/intrinsic). |

### Phased Execution Plan

1. **Schema** — Add `vector_index_schema` (`name`, `attribute`, `dimensions`, `distance`
   required; optional `hash` string, `filters` string array) and a `vectorindices` array
   property to `tables_schema` in **both** `schemas.json` and `local_schemas.json`. Unit-test
   accept/reject via `validate(...)` (mirror `test_fifoqueue.py`).
2. **Preprocessing (attribute injection)** — Add a focused step in `load.py` (wired into
   `preprocess_defaults`) that, for each table with `vectorindices`, merges each `hash` and
   each `filters` entry into the table's `attributes` as `{name, type: 'S'}` when not already
   present (dedup against existing attribute names). Pure-dict unit tests.
3. **Template (provisioning)** — In `template.j2`, after the GSI block, add
   `{% if table.vectorindices %}VectorIndexes: ...{% endif %}` mapping lowercase→CFN casing:
   `name`→`IndexName`, `attribute`→`VectorAttribute.AttributeName`, `dimensions`→`Dimensions`,
   `distance`→`DistanceFunction`, `Projection: ProjectionType: ALL`, and a `SearchSchema` built
   from `hash` (`HASH`) + each `filters` (`INLINE_FILTER`).
4. **Template (IAM)** — In the function `Policies:` loop, after the `DynamoDBCrudPolicy` block,
   add a `SearchVectors` inline statement by cross-referencing `tables.items()` (mirroring the
   stream-trigger block): for each vector-indexed table the function references, emit
   `Action: dynamodb:SearchVectors`, `Resource: !Sub "${{ "{" }}{{ prefix }}{{ table_name }}.Arn}/index/<index_name>"`.
5. **Example** — Add `example/vectorindices/` (model on `example/aoss/`): a vector-indexed
   table (ideally via the Prismarine `vector-indices` branch, per Q6, or a literal `tables:`
   block as a fallback) plus a single function referencing it, demonstrating end-to-end vector
   index provisioning + `SearchVectors` access.
6. **Tests** — `tests/test_vectorindices.py`: end-to-end `generate(...)` on the example,
   asserting the parsed `VectorIndexes`, the injected `AttributeDefinitions`, the
   `SearchVectors` policy + ARN shape, and a byte-identical/no-vector-key guard for a
   non-vector table. Run `uv run pytest` + `ruff`.
7. **Docs** — README + `docs/CLI_REFERENCE.md`: the `vectorindices` block, the on-demand
   requirement, the string-only filter-type limitation (Q2), the one-index-per-stack-operation
   caveat (Q3), and the coordinated Prismarine release note (Q6). CHANGELOG entry.

### Summary Table

| Decision | Choice | Rationale |
|----------|--------|-----------|
| CloudFormation target | Native `AWS::DynamoDB::Table` `VectorIndexes` | Official, GA; no GSI hack needed |
| Architecture | Hybrid (C): attribute injection in `load.py`, VectorIndexes + IAM in `template.j2` | Each piece lives where it's most natural and testable; IAM reuses the stream-trigger precedent |
| Key field mapping | Consume Prismarine lowercase keys, map to CFN casing in template | Q1; EasySAM owns the CFN vocabulary |
| `AttributeDefinitions` for schema attrs | Inject, dedup, default `AttributeType: S` | Q2(a); CFN requires them (overturns Prismarine E5 at the CFN layer) |
| Projection | Hardcode `ProjectionType: ALL` | Q5; consistent with GSI behavior |
| IAM | Emit `dynamodb:SearchVectors` on index ARN for referencing functions + ship a working example | Q4; scoped via `!Sub` over the table `.Arn` |
| One-index-per-op limit | Document only | Q3; CloudFormation service limit, EasySAM can't see deployed state |
| Release coordination | Track Prismarine `vector-indices` branch; publish together | Q6 |
| Billing | Rely on existing hardcoded `PAY_PER_REQUEST` | Vector indexes require on-demand; invariant already holds |

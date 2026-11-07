---
generated-by: "Brainstorm"
generated-at: 2026-11-07T12:00:00+02:00
status: drafting
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

## Architectural Approaches Evaluated

_(Phase 3 — to be completed after the questions above are answered.)_

## Structured Comparison & Methodology

_(Phase 3.)_

## Recommendation

_(Phase 4.)_

### Key Risks & Mitigations

_(Phase 4.)_

### Summary Table

_(Phase 4.)_

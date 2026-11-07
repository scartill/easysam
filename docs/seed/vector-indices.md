---
generated-by: "Seed"
source: docs/brainstorms/VECTOR_INDICES.md
generated-at: 2026-11-07T12:30:00+02:00
draft: true
consumed: false
consumed-at:
---

# Seed: EasySAM CloudFormation Support for DynamoDB Vector Indexes

## Intent

Prismarine (PR #4, "Vector Indices") now emits a `vectorindices` block into the EasySAM
table dict, but EasySAM silently ignores it. Teach EasySAM to consume that block and render
DynamoDB **native vector indexes** into CloudFormation via the official
`AWS::DynamoDB::Table` `VectorIndexes` property, and grant functions that use a
vector-indexed table permission to search it. This is the "coordinated EasySAM-side change"
the Prismarine spec explicitly deferred to us.

Scope is provisioning + access only. EasySAM does not generate embeddings and does not
implement the `SearchVectors` runtime call (that lives in Prismarine's generated client).

## The contract from Prismarine

`prisma_easysam.build_dynamo_tables` emits, per table, when vector indexes exist:

```python
table['vectorindices'] = [
  { 'name': <str>, 'attribute': <str>, 'dimensions': <int>, 'distance': <str>,
    'hash': <str>,            # present only when truthy
    'filters': [<str>, ...]   # present only when non-empty
  }, ...
]
```

EasySAM consumes these lowercase keys verbatim and maps them to CloudFormation casing.

## What I want

### 1. Render `VectorIndexes` into CloudFormation

Map each `vectorindices` entry to the native `AWS::DynamoDB::Table VectorIndexes` property:

```yaml
VectorIndexes:
  - IndexName: <name>
    Dimensions: <dimensions>
    DistanceFunction: <distance>          # COSINE | DOT_PRODUCT | EUCLIDEAN
    VectorAttribute:
      AttributeName: <attribute>
    Projection:
      ProjectionType: ALL
    SearchSchema:                         # only when hash and/or filters present
      - AttributeName: <hash>
        SearchSchemaElementType: HASH
      - AttributeName: <filter>           # one per filters entry
        SearchSchemaElementType: INLINE_FILTER
```

The whole block is emitted only when the table has `vectorindices`. Tables without a vector
index must produce **byte-identical** template output to today.

### 2. Inject SearchSchema attributes into AttributeDefinitions

CloudFormation requires every `SearchSchema` attribute (`hash`, each `filters` entry) to
also appear in the table's `AttributeDefinitions`, like GSI keys — otherwise it fails with a
`ValidationException`. EasySAM must inject them, deduplicated against the table's existing
key/GSI attributes. Default `AttributeType: S` (string) for injected attributes (matches
EasySAM's existing default for GSI attributes). Numeric filter types are a documented
limitation for now.

### 3. Grant functions `dynamodb:SearchVectors`

A function that references a vector-indexed table (via its existing
`resources.tables: [TableName]` list) must receive `dynamodb:SearchVectors` permission
scoped to the vector index ARN — not the table ARN. Mirror the existing stream-trigger IAM
idiom: cross-reference the global `tables` map against `function.tables`, and for each
vector-indexed table emit an inline statement:

```yaml
- Version: "2012-10-17"
  Statement:
    - Effect: Allow
      Action:
        - dynamodb:SearchVectors
      Resource: !Sub "${<TableLogicalId>.Arn}/index/<index-name>"
```

This pass must ship a **working single-function vector-index access example**.

### 4. Schema

Add a `vector_index_schema` (required: `name`, `attribute`, `dimensions`, `distance`;
optional: `hash` string, `filters` string array) and a `vectorindices` array property to
`tables_schema` in **both** `schemas.json` and `local_schemas.json` (the latter has
`additionalProperties: false`, so the key must be declared or validation rejects it).

## Design decisions (resolved in brainstorm)

- **Architecture: Hybrid.** Attribute injection (dedup into `AttributeDefinitions`) happens
  in `load.py` preprocessing where set logic is natural and unit-testable; the `VectorIndexes`
  rendering and the `SearchVectors` IAM cross-reference live in `template.j2`, reusing the
  existing stream-trigger precedent.
- **Field mapping:** consume Prismarine lowercase keys, map to CloudFormation casing in the
  template. (Q1)
- **AttributeDefinitions:** inject `hash`/`filters` as `AttributeType: S`, dedup against
  existing attributes; string-only limitation documented. This overturns Prismarine's
  Critique E5 at the CloudFormation layer — the official CFN docs require it. (Q2)
- **Projection:** hardcode `ProjectionType: ALL`. (Q5)
- **Billing:** rely on EasySAM's existing hardcoded `BillingMode: PAY_PER_REQUEST` — vector
  indexes require on-demand, and the invariant already holds.

## Out of scope

- Generating embeddings (caller's job).
- The `SearchVectors` runtime call (lives in Prismarine's generated client).
- Provisioned-throughput billing; configurable projection types.
- Changing existing GSI (`indices`) semantics.
- Blocking validation for the CloudFormation "one index per stack operation" limit — see
  caveat below (documentation only).

## Constraints / caveats to document

- Vector indexes require on-demand billing (`PAY_PER_REQUEST`); up to 5 per table;
  `1 <= dimensions <= 4096`.
- **CloudFormation allows only one index change per stack operation** — a single `easysam
  deploy` cannot add a GSI and a vector index together (or two indexes at once). This is a
  CloudFormation/service limit, not EasySAM; document it. (Q3)
- Injected filter/hash attributes default to string (`S`) type; numeric filters are a known
  limitation. (Q2)

## Follow-up tasks

- README + `docs/CLI_REFERENCE.md`: the `vectorindices` block, on-demand requirement,
  string-only filter-type limitation, one-index-per-stack-operation caveat, and the
  coordinated Prismarine release note.
- CHANGELOG entry.
- `example/vectorindices/` app (model on `example/aoss/`): a vector-indexed table plus a
  single function referencing it, demonstrating end-to-end provisioning + `SearchVectors`
  access.
- `tests/test_vectorindices.py`: end-to-end `generate(...)` asserting the parsed
  `VectorIndexes`, injected `AttributeDefinitions`, `SearchVectors` policy + ARN shape, and a
  no-vector-table byte-identical guard.

## Release coordination

EasySAM and Prismarine ship together when the feature is ready. During development this
EasySAM branch tracks the corresponding Prismarine `vector-indices` branch; pin the dev
dependency to that branch and verify the end-to-end example regenerates against it. (Q6)

---

_Derived from `docs/brainstorms/VECTOR_INDICES.md` (recommended Approach C)._

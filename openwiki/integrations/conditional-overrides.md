---
type: Integration
title: Conditionals and Deploy Overrides
description: How EasySAM resolves `!Conditional` YAML tags and context-file overrides against the deploy context, and how these two mechanisms interact with loading, validation, and template generation.
tags: [conditionals, overrides, deploy-context, load, integration]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-19T15:38:50.328Z
sources:
  - id: openwiki-source-4f5f656648e2abe6360b1c10
    resource: repo://example/conditionals/deploy-context.yaml
  - id: openwiki-source-7fefde8fd6f2a5ddc6bf04e3
    resource: repo://example/conditionals/resources.yaml
  - id: openwiki-source-3225566694929dc59804d606
    resource: repo://src/easysam/load.py
  - id: openwiki-source-4460f5ab958f712b5013c18b
    resource: repo://tests/test_conditionals.py
generated: { by: "openwiki/0.5.2", at: "2026-09-19T15:38:50.328Z" }
---

# Conditionals and Deploy Overrides

EasySAM has two cross-cutting mechanisms that let one `resources.yaml` describe many deploy targets without duplicating resource definitions: **conditional resources** (`!Conditional`) and **deploy-time overrides** (`--context-file`).

Both are resolved in `load.py`, before resources are validated or handed to the Jinja template. Together they decide the actual shape of `resources_data` that feeds generate/deploy.

## What problem this solves

Without conditionals, every environment or region variant would need its own `resources.yaml`, or a messy set of commented-out sections. Without overrides, environment-specific patches would have to live in the resource definitions themselves, blurring "what is the canonical resource" from "what is deploy-specific".

Conditionals and overrides split that concern:

- **Conditionals** decide *which resources exist at all* for a given environment/region.
- **Overrides** patch *properties of resources that already exist* for the current deploy context.

This page documents the semantics, ordering, edge cases, and the concrete example that exercises both.

## Deploy context

Both mechanisms consume the same deploy context dictionary:

- `environment` — maps to the conditional's `environment` check
- `target_region` — maps to the conditional's `region` check (note the rename: the YAML uses `region`, the code looks up `target_region`)
- `overrides` — optional map of dot-path patches loaded from a context file

The context is threaded through CLI option parsing, stored in `cli.easysam`, and passed into generation/deployment. For example:

```bash
easysam --environment prod --target-region eu-west-2 --context-file example/conditionals/deploy-context.yaml generate example/conditionals
```

From the user perspective, `--environment` and `--target-region` are the main drivers of conditional resolution; `--context-file` optionally adds overrides on top.

## Conditional resources

### What `!Conditional` looks like

Conditional keys use a custom YAML tag:

```yaml
buckets:
  ? !Conditional
    key: my-bucket
    environment: prod
    region: eu-west-2
  :
    public: true
```

Several constraints follow from how `conditional_constructor` is written:

- Every `!Conditional` must declare `key`. If `key` is missing, `conditional_constructor` raises `ValueError` **at parse time**, before any context resolution.
- The parsed tag becomes a `Conditional` object with `key`, `environment` (default `'any'`), and `region` (default `'any'`).

Source: `repo://src/easysam/load.py#L421-L443`

### Resolution semantics

`resolve_conditionals` recursively walks a data structure. When it encounters a `Conditional` key it:

1. Checks `environment` against `deploy_ctx['environment']` via `check_condition`
2. Checks `target_region` against `deploy_ctx['target_region']` via `check_condition`
3. Requires **both** to be true (AND logic) for the entry to be included
4. If included, stores the resolved value under `key.key`

Source: `repo://src/easysam/load.py#L471-L497`

A few consequences worth stating explicitly:

- The conditional's own `region` field is matched against `target_region` in the deploy context, not against a field named `region`. This is a frequent source of confusion because the YAML says `region` but the context lookup uses `target_region`.
- `key` is the actual resource key after resolution. The `!Conditional` block is not a resource key in the final data — it is a selector. In the example, three different conditional blocks all declare `key: my-bucket`, so exactly one of them wins for a given context.

### Match rules

`check_condition` implements the matching rules:

- `'any'` (the default) matches all values
- A **list** is OR-matched: e.g. `environment: [prod, staging]`
- A leading `~` negates: e.g. `environment: ~prod` matches anything except `prod`
- If the required deploy-context key is missing entirely, `check_condition` raises `FatalError`

Source: `repo://src/easysam/load.py#L446-L468`

`FatalError` is important: it is not a normal validation warning, it aborts the load pipeline immediately. That means a missing `environment` or `target_region` is fatal at resolve time, before schema validation or template generation.

### Where resolution happens

Conditionals are resolved at multiple points, with the same deploy context:

- **Root `resources.yaml`**: after env var expansion, before overrides/imports/defaults — `repo://src/easysam/load.py#L91-L95`
- **Each `easysam.yaml`**: after loading and env var expansion, before local schema validation — `repo://src/easysam/load.py#L273-L277`
- **Prismarine `conditional-tables`**: inside `preprocess_prismarine`, after popping from the prismarine config — `repo://src/easysam/load.py#L143-L148`

The important ordering constraint is that conditionals are resolved **before** schema validation and before imports are processed. That means only applicable resources enter the validation pipeline.

### Negation and overlapping keys

The conditionals example makes the negation and overlap behavior concrete.

```yaml
buckets:
  ? !Conditional
    key: my-bucket
    environment: prod
  :
    extaccesspolicy: ProdPolicy
    public: true

  ? !Conditional
    key: my-bucket
    region: eu-west-2
  :
    extaccesspolicy: EUWest2Policy
    public: false

  ? !Conditional
    key: my-bucket
    environment: ~prod
    region: ~eu-west-2
  :
    extaccesspolicy: CommonPolicy
    public: false

  simple-bucket:
    public: false
```

What this means in practice:

- For `environment=prod` and `target_region=us-east-1`, the first block wins (`ProdPolicy`, public bucket).
- For `environment=dev` and `target_region=eu-west-2`, the second block wins (`EUWest2Policy`, private bucket).
- For `environment=dev` and `target_region=us-east-1`, the third block wins (`CommonPolicy`, private bucket).
- `simple-bucket` is unconditional, so it always exists.

See `repo://example/conditionals/resources.yaml` and `repo://tests/test_conditionals.py`.

### Test coverage of conditionals

The dedicated test module exercises the three principal branches directly:

- `test_conditionals_prod` — `environment=prod`, `target_region=us-east-1` → `ProdPolicy`
- `test_conditionals_eu_west_2` — `environment=dev`, `target_region=eu-west-2` → `EUWest2Policy`
- `test_conditionals_other` — `environment=dev`, `target_region=us-east-1` → `CommonPolicy`

Source: `repo://tests/test_conditionals.py`

## Deploy context overrides

### What they are

A YAML context file passed via `--context-file` can patch any resource property using a `/`-separated dot-path in an `overrides` map.

Example from the conditionals example:

```yaml
overrides:
  buckets/simple-bucket/public: true
  buckets/new-bucket:
    public: false
```

Source: `repo://example/conditionals/deploy-context.yaml`

### Semantics and ordering

`apply_overrides` runs during `resources()`:

1. Conditionals are resolved first
2. Then `apply_overrides` patches `resources_data` using the context's `overrides` map
3. Overrides are applied **after** conditionals, so they affect only resources that survived conditional resolution
4. The override path uses `/` as a separator, which `apply_overrides` converts to `.` for `benedict` key assignment

Source: `repo://src/easysam/load.py#L97-L98`, `repo://src/easysam/load.py#L500-L505`

That ordering matters: overrides cannot resurrect a resource excluded by conditionals, and conditionals cannot see override-modified values because they run first.

### Override shape

Overrides are not restricted to scalars. The context file can set nested maps:

```yaml
overrides:
  buckets/new-bucket:
    public: false
```

This is why the YAML override syntax in the reference doc shows both leaf and map forms.

Source: `repo://docs/RESOURCE_REFERENCE.md`

## How they interact

A practical deploy context file can combine conditionals and overrides in the same invocation:

```bash
easysam --environment prod --target-region eu-west-2 --context-file example/conditionals/deploy-context.yaml generate example/conditionals
```

The effective pipeline for that invocation is:

1. Parse `resources.yaml` with `!Conditional` constructor
2. Expand env vars
3. Resolve conditionals using `environment=prod`, `target_region=eu-west-2`
4. Apply overrides from `deploy-context.yaml`
5. Preprocess imports, Prismarine, defaults
6. Validate
7. Generate template

Source: `repo://src/easysam/load.py#L56-L110`, `repo://openwiki/workflows/generate-deploy.md`

For the conditionals example specifically:

- With `--environment prod --target-region eu-west-2`, the resolved bucket is the `region: eu-west-2` variant (`EUWest2Policy`, private).
- The context override `buckets/simple-bucket/public: true` would additionally make the unconditional `simple-bucket` public for this deploy.
- Overrides do not change which conditional block won; they only patch resolved properties.

## Lifecycle and ordering summary

The full resource lifecycle is documented in `Resource Model`. For conditionals/overrides the relevant slice is:

1. Load `resources.yaml`
2. Load `.env` if present
3. Register `!Conditional` constructor and parse
4. Expand environment variables
5. Resolve conditionals against deploy context
6. Apply overrides from context file
7. Preprocess resources (imports, Prismarine, defaults, sorting)
8. Validate
9. Render template

Sources: `repo://src/easysam/load.py#L56-L110`, `repo://openwiki/domain/resource-model.md`

### Failure modes

- **Missing `key` in `!Conditional`** → `ValueError` at YAML parse time
- **Missing deploy-context key** (`environment` or `target_region`) → `FatalError` during conditional resolution, aborting the load
- **Duplicate resolved keys across conditionals** are not separately enforced by `load.py`; the semantics are "last matching include wins" because `resolve_conditionals` writes into `resolved[key.key]`. The provided example avoids conflicts by using the same key with mutually exclusive contexts, but overlapping non-exclusive conditionals can silently overwrite each other
- **Overrides to non-existent paths** are applied through `benedict` and may create intermediate structures depending on how that access behaves; the documented use is patching existing resource properties

## Extension points

- **Conditional resolution** is centralized in `resolve_conditionals` and `check_condition`. If a new deploy dimension is needed, the natural extension point is adding another context key and another `check_condition` call inside `resolve_conditionals`.
- **Overrides** are applied by `apply_overrides` and are keyed by `/`-separated paths. Any deploy-specific patch that can be expressed as a path→value map can go through the same mechanism.
- **Local `easysam.yaml`** files participate in the same conditional model; each imported file is independently parsed, expanded, and resolved against the same deploy context.

Sources: `repo://src/easysam/load.py#L421-L497`, `repo://src/easysam/load.py#L500-L505`, `repo://src/easysam/load.py#L259-L290`

## Example anchor

The canonical example for this feature is `example/conditionals`:

- `repo://example/conditionals/resources.yaml`
- `repo://example/conditionals/deploy-context.yaml`
- `repo://example/conditionals/README.md`
- `repo://tests/test_conditionals.py`

A simpler unconditional comparison point is `example/onelambda`:

- `repo://example/onelambda`
- `repo://tests/test_onelambda.py`

For error-path behavior in the loading/validation boundary, see `example/appwitherrors`:

- `repo://example/appwitherrors`
- `repo://tests/test_errors.py`

## Related pages

- `repo://openwiki/domain/resource-model.md` — full resource lifecycle and defaults/validation
- `repo://openwiki/architecture/source-map.md` — where `load.py`, `generate.py`, and `deploy.py` sit in the codebase
- `repo://openwiki/workflows/generate-deploy.md` — end-to-end generate/deploy sequence

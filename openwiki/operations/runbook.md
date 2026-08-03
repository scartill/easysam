---
type: Playbook
title: Operations Runbook
description: Validation, cloud checks, deployment safety, common errors, and production hardening guidance for EasySAM projects.
tags: [operations, runbook, validation, deployment, production]
---

# Operations Runbook

## Validation pipeline

EasySAM provides two validation stages that should run before every deployment:

### 1. Schema validation (`inspect schema`)

Source: `src/easysam/validate_schema.py`

Validates the resolved resource model (after conditionals, imports, and defaults) against JSON Schema Draft 7:

- **`schemas.json`** — global `resources.yaml` structure
- **`local_schemas.json`** — per-file `easysam.yaml` structure

Custom validators catch domain-specific rules:

| Validator | What it checks |
| --- | --- |
| `validate_buckets` | Private bucket cannot be public |
| `validate_tables` | Trigger function must exist in `functions` |
| `validate_streams` | Each bucket destination must have exactly one of `bucketname`/`extbucketarn`; referenced buckets must exist |
| `validate_lambda` | Lambda function configuration correctness |
| `validate_paths` | `open` and `authorizer` are mutually exclusive; path structure |
| `validate_import` | Import directories exist and contain valid `easysam.yaml` |
| `validate_prismarine` | Prismarine config: base directory, package existence, prefix match |
| `validate_authorizers` | Authorizer identity style (token/query/headers) |
| `validate_mqtt` | MQTT authorizer function exists |

```bash
easysam --environment dev inspect schema .
easysam --environment dev inspect schema . --select functions.myfunction
```

### 2. Cloud validation (`inspect cloud`)

Source: `src/easysam/validate_cloud.py`

Checks live AWS resources that EasySAM references but does not manage:

- **IAM policies** — bucket `extaccesspolicy` must exist as `<PolicyName>-<environment>` in IAM
- **SSM parameters** — custom Lambda layers via `{{resolve:ssm:/param-name}}` must resolve
- **Lambda layer ARNs** — direct ARN references must be valid layer versions

Requires AWS credentials (`--aws-profile`) and `--environment`.

```bash
easysam --environment dev --aws-profile my-profile inspect cloud .
```

## Deployment checks

Source: `src/easysam/deploy.py`

Before `sam deploy`, EasySAM verifies:

| Check | Minimum version | Source |
| --- | --- | --- |
| pip | 25.1.1 | `PIP_VERSION` constant |
| SAM CLI | 1.138.0 | `SAM_CLI_VERSION` constant |

Both checks run `--version` via subprocess and compare string-wise.

## Common dependency packaging

During deploy, `commondep.py` traces `common.*` imports using AST analysis and copies only needed modules into each Lambda directory. This ensures:

- Lambda packages include transitively-required shared code
- No manual packaging of `common/` into each function
- Cleanup after deploy (unless `--no-cleanup`)

Inspect dependencies without deploying:

```bash
easysam inspect common-deps backend/function/myfunction
```

## Common errors and solutions

### `FatalError: Condition "environment" not found in deployment context`

A `!Conditional` resource references `environment` or `region`, but the corresponding CLI option was not provided. Fix: pass `--environment` and/or `--target-region`.

### `Import directory X not found`

An `import` entry in `resources.yaml` or `easysam.yaml` points to a non-existent directory. Check relative paths.

### `Duplicate lambda name` / `Duplicate path` / `Duplicate table`

Two `easysam.yaml` files define the same resource name. Names must be unique across all imports.

### `Bucket 'X' has an invalid extaccesspolicy`

The IAM policy `<PolicyName>-<environment>` was not found in the target AWS account. Create the policy or remove the `extaccesspolicy` reference.

### `SSM parameter X not found`

A custom Lambda layer references an SSM parameter that doesn't exist. Create the parameter or fix the reference.

### `Prismarine Cluster prefix must start with the master prefix`

The Prismarine `Cluster('Prefix')` in the model file doesn't match the `prefix` in `resources.yaml`. The cluster prefix must start with the EasySAM prefix.

## Production hardening checklist

From `docs/PRODUCTION_HARDENING.md`:

### IAM and access
- [ ] No unnecessary admin-like permissions
- [ ] Public API routes are intentionally public (`open: true`)
- [ ] Protected paths use `authorizer`, not `open`
- [ ] Function resource lists are explicit (`tables`, `buckets`, `queues`, `streams`)
- [ ] Review `services` permissions: `bedrock`, `mqtt`, `budget`, `comprehend`
- [ ] Review `searches` permissions for AOSS collection access

### API security and CORS
- [ ] Default CORS is permissive (`*`) — restrict for internet-facing APIs
- [ ] CORS settings align with frontend domains
- [ ] Sensitive routes require authorization
- [ ] GatewayResponse CORS headers are configured (v1.12.1+) for 401/403 pre-Lambda responses

### Data protection
- [ ] Buckets are private by default (`public: false`)
- [ ] DynamoDB TTL only on data that should expire
- [ ] Stream consumers are idempotent (triggers may retry)
- [ ] OpenSearch collections are scoped to expected principals

### Secrets
- [ ] No plaintext secrets in `resources.yaml`, handlers, or tests
- [ ] Runtime config from environment/SSM/Secrets Manager
- [ ] Use `--aws-profile` in local workflows

### CI/CD
- [ ] Context file is versioned and reviewed
- [ ] Deploys are environment-specific (`--environment`)
- [ ] CI Python version matches `python:` in `resources.yaml`
- [ ] Pipeline: `inspect schema` → `inspect cloud` → `generate` → `deploy`

## Recent operational changes

From `CHANGELOG.md` and git history:

- **OpenWiki automation** — Added GitHub Actions workflow (`.github/workflows/openwiki-update.yml`) for scheduled wiki updates (commit 55213b6)
- **v1.12.1** — Added `GatewayResponse` CORS headers for API Gateway 401/403 responses (commit 7476b73)
- **v1.12.0** — `!Conditional` support in local `easysam.yaml` files and Prismarine conditional tables (commits 08f51f8, 3a0b35d, 2bf1d55)
- **v1.11.0** — Environment variable expansion, `.env` support, `budget` service
- **v1.10.0** — Local JSON schema validation for `easysam.yaml`, configurable Python runtime, timeout support

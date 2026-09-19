---
type: Playbook
title: Operations Runbook
description: Validation, cloud checks, deployment safety, common errors, and production hardening guidance for EasySAM projects.
tags: [operations, runbook, validation, deployment, production]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-19T15:38:50.328Z
sources:
  - id: openwiki-source-053b10c5214178e0f68451a7
    resource: repo://docs/PRODUCTION_HARDENING.md
  - id: openwiki-source-4ac1c0d195c62c553ac66f88
    resource: repo://src/easysam/cli.py
  - id: openwiki-source-5b82eb053aaed886997a474d
    resource: repo://src/easysam/commondep.py
  - id: openwiki-source-76059441794faf322fc854f9
    resource: repo://src/easysam/deploy.py
  - id: openwiki-source-6a998f9c09695c437759a6e6
    resource: repo://src/easysam/inspect.py
  - id: openwiki-source-e7decf94ff906feb67d942e6
    resource: repo://src/easysam/local_cli.py
  - id: openwiki-source-c15458a8ff9ea3d6838e74e7
    resource: repo://src/easysam/validate_cloud.py
  - id: openwiki-source-205687dd76d7516f212885a8
    resource: repo://src/easysam/validate_schema.py
generated: { by: "openwiki/0.5.2", at: "2026-09-19T15:38:50.328Z" }
---

# Operations Runbook

This runbook covers day-to-day operational concerns for EasySAM projects: validation commands, deploy safety checks, local development flow, cleanup behavior, delete semantics, and the production hardening checklist.

<!-- openwiki: broken internal link [workflows/generate-deploy.md] file "workflows/generate-deploy.md" does not exist. Fix the href or restore the target, then delete this comment. -->
All commands are anchored to `src/easysam/cli.py` and the `inspect`, `deploy`, `delete`, and `cleanup` paths. For the end-to-end lifecycle see [Generate and Deploy Workflow](workflows/generate-deploy.md).

## CLI entrypoint and context

The top-level `easysam` CLI (`src/easysam/cli.py`) accepts shared options that feed the deployment context used by every subcommand:

| Option | Purpose | Default / envvar |
| --- | --- | --- |
| `--environment` | AWS stack / environment name used in generation and deploy | `dev` (`EASYSAM_ENVIRONMENT`) |
| `--target-region` | Region used for generation and deploy | none (`EASYSAM_TARGET_REGION`) |
| `--aws-profile` | AWS profile for cloud inspection and deploy | none (`EASYSAM_AWS_PROFILE`) |
| `--context-file` | YAML file providing additional deploy context (e.g. overrides) | none |
| `--verbose` | Enable debug logging | off |

Context files are loaded into `deploy_ctx` and merged with the CLI options, so `--environment`, `--target-region`, and any context-file keys form the deployment context passed to `generate`, `deploy`, `inspect cloud`, and `delete`.

## Validation pipeline

EasySAM provides two validation stages that should run before every deployment. Both are implemented under the `inspect` command group (`src/easysam/inspect.py`).

### 1. Schema validation (`inspect schema`)

Source: `src/easysam/validate_schema.py`

`inspect schema` loads and resolves the full resource model (after conditionals, imports, and defaults) and validates it against JSON Schema Draft 7:

- **`schemas.json`** — global `resources.yaml` structure
- **`local_schemas.json`** — per-file `easysam.yaml` structure

Custom validators enforce domain-specific rules that the JSON Schema cannot express:

| Validator | What it checks |
| --- | --- |
| `validate_buckets` | A bucket named `private` cannot be public |
| `validate_tables` | A table trigger function must exist in `functions` |
| `validate_streams` | Each bucket destination must have exactly one of `bucketname`/`extbucketarn`; referenced buckets must exist; external bucket ARNs must be valid |
| `validate_lambda` | Lambda references to buckets, tables, queues, streams, searches, and services must resolve; MQTT service requires `mqtt` defined |
| `validate_paths` | `open` and `authorizer` are mutually exclusive; lambda paths must have one or the other; authorizer must exist; SQS/dynamo paths must have valid request/response templates |
| `validate_import` | Import directories exist and contain valid `easysam.yaml` |
| `validate_prismarine` | Prismarine default base directory exists; per-table base directories exist |
| `validate_authorizers` | Authorizer identity style has exactly one of `token`/`query`/`headers`; authorizer function must exist |
| `validate_mqtt` | MQTT authorizer function must exist (if defined) |

```bash
easysam --environment dev inspect schema .
easysam --environment dev inspect schema . --select functions.myfunction
```

Use `--select` to render a specific subsection of the resolved resources for debugging after validation succeeds.

### 2. Cloud validation (`inspect cloud`)

Source: `src/easysam/validate_cloud.py`

`inspect cloud` checks live AWS resources that EasySAM references but does not manage:

- **IAM policies** — bucket `extaccesspolicy` references must exist as `<PolicyName>-<environment>` in IAM (scoped to `Local` policies)
- **SSM parameters** — custom Lambda layers referenced via `{{resolve:ssm:/param-name}}` must resolve to a value
- **Lambda layer ARNs** — direct ARN references must correspond to a valid layer version

The command requires `--environment` and normally `--aws-profile` (or equivalent credentials). It loads and validates the model first; if schema errors exist it stops and asks you to fix them with `inspect schema`.

```bash
easysam --environment dev --aws-profile my-profile inspect cloud .
```

## Deployment checks

Source: `src/easysam/deploy.py`

Before `sam deploy`, EasySAM verifies tooling versions:

| Check | Minimum version | Source |
| --- | --- | --- |
| pip | 25.1.1 | `PIP_VERSION` constant in `deploy.py` |
| SAM CLI | 1.138.0 | `SAM_CLI_VERSION` constant in `deploy.py` |

Both checks run `--version` via subprocess and compare string-wise using `packaging.version.Version`. A failing check raises `UserWarning` and aborts the deploy.

## Deploy flow and safety

Source: `src/easysam/deploy.py:deploy`

`deploy` regenerates the template internally (it calls `generate` + validation), then runs the following steps in order:

1. **Generate + validate** — `generate()` is called; any errors abort the deploy with `UserWarning('There were errors - aborting deployment')`.
2. **Version checks** — `check_pip_version()` and `check_sam_cli_version()`.
3. **Common dependency cleanup** — `remove_common_dependencies(directory)` removes any previously copied `common/` trees from lambda directories.
4. **Common dependency copy** — `copy_common_dependencies(directory, resources)` traces `common.*` imports using AST analysis and copies only the needed modules into each Lambda directory.
5. **`sam build`** — builds the SAM template in the project directory.
6. **`sam deploy`** — deploys with:
   - `--stack-name <environment>`
   - `--parameter-overrides Stage=<environment>`
   - `--no-fail-on-empty-changeset`
   - `--no-confirm-changeset`
   - `--resolve-s3`
   - `--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM`
   - `--region` if `target_region` is set
   - `--tags` merged from CLI `--tag` options and any `tags` in the resources data
   - `--profile` if `aws_profile` is set
7. **Post-deploy reconcile** — `reconcile_event_source_mappings()` reconciles SQS/Kinesis event source mapping `Enabled` state with the `polls` configuration.
8. **Cleanup** — `remove_common_dependencies(directory)` unless `--no-cleanup` was passed.

Key deploy options:

| Option | Effect |
| --- | --- |
| `--dry-run` | Print the `sam deploy` command without executing |
| `--sam-tool` | Override the SAM invocation (default: `uv run sam`) |
| `--override-main-template` | Use a custom Jinja template instead of `template.j2` |
| `--no-cleanup` | Skip removal of copied common dependencies after deploy |
| `--tag key=value` | Repeatable CloudFormation tags (merged with resource-level tags) |
| `--verbose` | Pass `--debug` to `sam build` and `sam deploy` |

After a successful deploy, EasySAM reconciles event source mappings for functions that declare `polls`. For each pollable function it lists existing event source mappings, matches them by queue name suffix, and updates `Enabled` to match the desired state. Mismatches are fixed; missing mappings are logged as warnings; function-not-found conditions are logged and skipped.

## Common dependency management

During deploy, `commondep.py` traces `common.*` imports using AST analysis and copies only the needed modules into each Lambda directory. This ensures:

- Lambda packages include transitively-required shared code
- No manual packaging of `common/` into each function
- Cleanup after deploy (unless `--no-cleanup`)

The algorithm:

1. Scan `common/` for available packages (directories and `.py` files, excluding `__`-prefixed names)
2. Parse each Lambda's Python files with `ast` to find `import common.X` and `from common.X import ...`
3. Recursively trace transitive dependencies (if `common.a` imports `common.b`, both are included)
4. Copy resolved dependencies into the Lambda directory

Inspect dependencies without deploying:

```bash
easysam inspect common-deps backend/function/myfunction
```

The `cleanup` command (`easysam cleanup <directory>`) removes common dependencies from the directory without deploying, calling `remove_common_dependencies()`.

## Local development

Source: `src/easysam/local_cli.py`

The `local` command group runs Lambda functions locally:

| Command | Purpose |
| --- | --- |
| `easysam local .` | Start a local HTTP server that mocks API Gateway routing |
| `easysam local invoke <function>` | Invoke a single function with a custom event |

`local` options:

| Option | Default | Purpose |
| --- | --- | --- |
| `--port` | 3000 | Port to listen on |
| `--host` | 127.0.0.1 | Host to bind to |
| `--event-format` | v1 | API Gateway event format (v1=REST API, v2=HTTP API) |
| `--auth-context` | none | Auth context JSON file path or inline JSON string (injected into `requestContext.authorizer`) |
| `--event` (invoke only) | `{}` | Event JSON file path or inline JSON string |

`local invoke` loads resources, resolves the named function, sets global and per-function environment variables, injects `AWS_DEFAULT_REGION` and `AWS_PROFILE` from the CLI context when not already set, and invokes the handler via `load_and_invoke` with a `MockLambdaContext`.

## Delete behavior

Source: `src/easysam/deploy.py:delete`

`delete` calls CloudFormation `delete_stack` directly (not via SAM CLI):

| Option | Effect |
| --- | --- |
| `--force` | Uses `FORCE_DELETE_STACK` deletion mode |
| `--await` | Polls stack status until `DELETE_COMPLETE` |

The delete flow:

1. Look up the environment name from `deploy_ctx['environment']`.
2. Call `cloudformation.delete_stack(StackName=environment, DeletionMode=mode)` where `mode` is `FORCE_DELETE_STACK` when `--force` is set, otherwise `STANDARD`.
3. If `--await` is set, poll `describe_stacks` until the status is `DELETE_COMPLETE` or the stack is no longer present. If the status is anything other than `DELETE_IN_PROGRESS` or `DELETE_COMPLETE`, raise `UserWarning`.

```bash
easysam --environment dev --aws-profile my-profile delete --await
easysam --environment dev --aws-profile my-profile delete --force --await
```

## Common errors and solutions

### `FatalError: Condition "environment" not found in deployment context`

A `!Conditional` resource references `environment` or `region`, but the corresponding CLI option was not provided. Fix: pass `--environment` and/or `--target-region`.

### `Import directory X not found`

An `import` entry in `resources.yaml` or `easysam.yaml` points to a non-existent directory. Check relative paths.

### `Duplicate lambda name` / `Duplicate path` / `Duplicate table`

Two `easysam.yaml` files define the same resource name. Names must be unique across all imports.

### `Bucket 'X' has an invalid extaccesspolicy`

The IAM policy `<PolicyName>-<environment>` was not found in the target AWS account (scoped to local policies). Create the policy or remove the `extaccesspolicy` reference.

### `SSM parameter X not found`

A custom Lambda layer references an SSM parameter that doesn't exist. Create the parameter or fix the reference.

### `Prismarine Cluster prefix must start with the master prefix`

The Prismarine `Cluster('Prefix')` in the model file doesn't match the `prefix` in `resources.yaml`. The cluster prefix must start with the EasySAM prefix.

### `pip version must be 25.1.1 or higher` / `SAM CLI version must be 1.138.0 or higher`

Tooling version checks failed during deploy. Upgrade pip and/or the SAM CLI to the required minimums.

### `Lambda path cannot have both authorizer and open` / `Lambda path must have either authorizer or be open`

A lambda path is missing `open` or `authorizer`, or has both. Fix the path definition.

### `Authorizer 'X' cannot have multiple types`

An authorizer defines more than one of `token`, `query`, `headers`. Fix to exactly one.

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

Recommended CI stages from `docs/PRODUCTION_HARDENING.md`:

```bash
easysam --environment prod --context-file deploy-context.yaml inspect schema .
easysam --environment prod --context-file deploy-context.yaml inspect cloud .
easysam --environment prod --context-file deploy-context.yaml generate .
easysam --environment prod --context-file deploy-context.yaml deploy .
```

### Observability and operations

- [ ] Critical alarms configured
- [ ] Dashboards available for API, Lambda, and data paths
- [ ] Runbooks exist for common failures

### Cost controls

- [ ] Budget alarms enabled
- [ ] Environment lifecycle policy in place
- [ ] Example/test stacks are removed after validation (`delete`)

## Recent operational changes

From `CHANGELOG.md` and git history:

- **OpenWiki automation** — Added GitHub Actions workflow (`.github/workflows/openwiki-update.yml`) for scheduled wiki updates (commit 55213b6)
- **v1.12.1** — Added `GatewayResponse` CORS headers for API Gateway 401/403 responses (commit 7476b73)
- **v1.12.0** — `!Conditional` support in local `easysam.yaml` files and Prismarine conditional tables (commits 08f51f8, 3a0b35d, 2bf1d55)
- **v1.11.0** — Environment variable expansion, `.env` support, `budget` service
- **v1.10.0** — Local JSON schema validation for `easysam.yaml`, configurable Python runtime, timeout support

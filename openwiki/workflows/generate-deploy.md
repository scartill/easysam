---
type: "Reference"
title: "Generate and Deploy Workflow"
openwiki_generated: true
verified:
  - by: openwiki/0.5.2
    at: 2026-09-19T15:38:50.328Z
sources:
  - id: openwiki-source-17e562d99a324c4472571fc7
    resource: repo://docs/CLI_REFERENCE.md
  - id: openwiki-source-76059441794faf322fc854f9
    resource: repo://src/easysam/deploy.py
  - id: openwiki-source-778363b9ddba351fd47aa280
    resource: repo://src/easysam/generate.py
  - id: openwiki-source-6a998f9c09695c437759a6e6
    resource: repo://src/easysam/inspect.py
  - id: openwiki-source-c15458a8ff9ea3d6838e74e7
    resource: repo://src/easysam/validate_cloud.py
generated: { by: "openwiki/0.5.2", at: "2026-09-19T15:38:50.328Z" }
---


# Generate and Deploy Workflow

This page documents the end-to-end lifecycle of an EasySAM project: initialization, validation, template generation, AWS deployment, and teardown. The implementation entrypoints are `src/easysam/generate.py`, `src/easysam/deploy.py`, `src/easysam/inspect.py`, and `src/easysam/validate_cloud.py`; deployment behavior is anchored by `deploy.py`, which regenerates the template, checks prerequisite tool versions, handles common dependencies, and drives SAM build/deploy.

## Lifecycle overview

```mermaid
sequenceDiagram
    participant User
    participant CLI as cli.py
    participant Inspect as inspect.py
    participant Load as load.py
    participant ValidateSchema as validate_schema.py
    participant ValidateCloud as validate_cloud.py
    participant Generate as generate.py
    participant Jinja as template.j2 / swagger.j2
    participant Prisma as prismarine.py
    participant Deploy as deploy.py
    participant SAM as SAM CLI
    participant AWS as AWS CloudFormation

    User->>CLI: easysam init [--prismarine]
    CLI->>User: Scaffold resources.yaml, common/, backend/, thirdparty/

    User->>CLI: easysam inspect schema .
    CLI->>Inspect: inspect schema
    Inspect->>Load: load_resources(resources.yaml + imports)
    Load->>Load: Resolve !Conditional, apply overrides, preprocess
    Load->>ValidateSchema: Validate against schemas.json + local_schemas.json + custom rules
    ValidateSchema-->>Inspect: Errors or success
    Inspect-->>User: Validation result (or selected subsection via --select)

    User->>CLI: easysam inspect cloud .
    CLI->>Inspect: inspect cloud
    Inspect->>Load: load_resources(...)
    Load-->>Inspect: resources_data
    Inspect->>ValidateCloud: validate_cloud(obj, resources_data, environment, errors)
    ValidateCloud->>AWS: IAM list_policies, SSM get_parameter, Lambda get_layer_version_by_arn
    ValidateCloud-->>Inspect: Cloud validation errors or success
    Inspect-->>User: Cloud validation result

    User->>CLI: easysam generate .
    CLI->>Generate: generate(cliparams, directory, pypath, deploy_ctx)
    Generate->>Load: load_resources(...)
    Load-->>Generate: resources_data (benedict)
    Generate->>Generate: Execute plugins (if defined)
    Generate->>Jinja: Render template.j2 -> template.yml
    Generate->>Jinja: Render swagger.j2 -> build/swagger.yaml (if paths defined)
    Generate->>Prisma: generate_prismarine_clients(...) (if prismarine configured)
    Generate-->>User: template.yml generated

    User->>CLI: easysam deploy .
    CLI->>Deploy: deploy(cliparams, directory, deploy_ctx)
    Deploy->>Generate: generate() internally (regenerate + validate)
    Deploy->>Deploy: check_pip_version / check_sam_cli_version
    Deploy->>Deploy: copy_common_dependencies(directory, resources)
    Deploy->>SAM: sam build
    SAM-->>Deploy: Build artifacts
    Deploy->>SAM: sam deploy --stack-name <environment> --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
    SAM->>AWS: Create/update CloudFormation stack
    AWS-->>SAM: Stack ARN
    SAM-->>Deploy: Deploy complete
    Deploy->>Deploy: remove_common_dependencies() unless --no-cleanup
    Deploy-->>User: Deployment successful

    User->>CLI: easysam delete --await [--force]
    CLI->>Deploy: delete(cliparams, environment)
    Deploy->>AWS: cloudformation.delete_stack (STANDARD or FORCE_DELETE_STACK)
    AWS-->>Deploy: DELETE_COMPLETE (when --await)
    Deploy-->>User: Stack deleted
```

*End-to-end sequence from init through schema/cloud validation, generation, SAM build/deploy, and delete. Deploy itself re-runs generate internally before invoking SAM.*

## 1. Init (`easysam init`)

Source: `src/easysam/init.py`

Creates a minimal project structure:

```
my-app/
├── resources.yaml          # prefix + import list
├── .gitignore              # build artifacts excluded
├── common/
│   └── utils.py            # shared utility module
├── backend/
│   ├── database/
│   │   └── easysam.yaml    # table definition (MyItem)
│   └── function/
│       └── myfunction/
│           ├── easysam.yaml # lambda + integration
│           └── index.py     # handler
└── thirdparty/
    └── requirements.txt    # boto3
```

With `--prismarine`, the scaffold includes Prismarine model files (`common/myobject/models.py`, `db.py`), a `dynamo_access.py` access module, and a trigger lambda (`itemlogger`) with a DynamoDB stream handler.

Requires `pyproject.toml` in the current directory.

## 2. Schema validation (`easysam inspect schema`)

Source: `src/easysam/inspect.py`, `src/easysam/validate_schema.py`

Loads and resolves all resources (including conditionals and imports), then validates against:

- **`schemas.json`** — JSON Schema Draft 7 for the global `resources.yaml` structure
- **`local_schemas.json`** — per-file schema for each `easysam.yaml`
- **Custom validators** — bucket rules (private can't be public), table trigger function existence, stream bucket validation, path/authorizer mutual exclusivity, MQTT config, Prismarine config

Use `--select functions.myfunction` to render a specific subsection of resolved resources for debugging.

```bash
easysam --environment dev inspect schema .
```

## 3. Cloud validation (`easysam inspect cloud`)

Source: `src/easysam/validate_cloud.py`

Checks live AWS resources that EasySAM depends on but does not create:

- **IAM policies** for bucket `extaccesspolicy` references (must exist as `<PolicyName>-<environment>`)
- **SSM parameters** for custom Lambda layers referenced via `{{resolve:ssm:...}}`
- **Lambda layer ARNs** — verifies the layer version exists

Requires `--aws-profile` and `--environment`.

```bash
easysam --environment dev --aws-profile my-profile inspect cloud .
```

## 4. Generate (`easysam generate`)

Source: `src/easysam/generate.py`

Runs the full load+validate pipeline, then renders the SAM template:

1. Calls `load.resources()` to produce the resolved `resources_data` dict
2. Executes plugins (if defined) to generate custom YAML fragments
3. Renders `template.j2` → `template.yml`
4. Renders `swagger.j2` → `build/swagger.yaml` (only if API `paths` are defined)
5. Calls `prismarine.generate()` to write `prismarine_client.py` (if Prismarine is configured)

Output goes to the project directory. The `template.yml` is the primary artifact consumed by SAM.

```bash
easysam --environment dev generate .
```

Generate returns a `ProcessingResult` (the resolved `resources_data` plus any errors) so callers such as `deploy.py` can inspect validation outcomes without running a separate schema command.

## 5. Deploy (`easysam deploy`)

Source: `src/easysam/deploy.py`

Wraps the SAM CLI deployment:

1. **Regenerates** the template (calls `generate()` internally — no separate generate step needed)
2. **Version checks** — pip ≥ 25.1.1, SAM CLI ≥ 1.138.0
3. **Common dependency copy** — uses `commondep.py` to AST-trace `common.*` imports in each lambda, copies only needed modules into the lambda directory
4. **`sam build`** — compiles the SAM template
5. **`sam deploy`** — deploys with `--stack-name <environment>`, `--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM`, tags, and region
6. **Cleanup** — removes copied common dependencies (unless `--no-cleanup`)

```bash
easysam --environment dev --aws-profile my-profile deploy . --tag project=myapp
```

Key deploy options:

- `--dry-run` — print the SAM deploy command without executing
- `--sam-tool` — override the SAM invocation (default: `uv run sam`)
- `--override-main-template` — use a custom Jinja template instead of `template.j2`
- `--tag key=value` — repeatable CloudFormation tags

Deployment aborts if generation produces errors: `deploy()` checks the error list returned by `generate()` and raises `UserWarning` before invoking SAM.

## 6. Delete (`easysam delete`)

Source: `src/easysam/deploy.py:delete`

Calls CloudFormation `delete_stack` directly (not via SAM CLI):

- `--force` — uses `FORCE_DELETE_STACK` deletion mode
- `--await` — polls stack status until `DELETE_COMPLETE`

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

## Common dependency management

Source: `src/easysam/commondep.py`

During deploy, EasySAM needs to package shared `common/` code into each Lambda function directory. The `commondep` module:

1. Scans `common/` for available packages (directories and `.py` files, excluding `__`-prefixed)
2. Parses each lambda's Python files using `ast` to find `import common.X` and `from common.X import ...` statements
3. Recursively traces transitive dependencies (if `common.a` imports `common.b`, both are included)
4. Copies resolved dependencies into the lambda directory
5. Cleans up after deploy (unless `--no-cleanup`)

You can inspect dependencies without deploying:

```bash
easysam inspect common-deps backend/function/myfunction
```

## Safe deployment pipeline

Schema validation and cloud validation are intended to run before generation/deploy so that template rendering and SAM deployment operate on already-resolved, externally-verified resources. Cloud validation is especially important because `deploy()` does not re-check external IAM/SSM/Lambda dependencies; it assumes `inspect cloud` (or an equivalent check) has already passed.

Recommended pre-deploy sequence:

1. `easysam inspect schema .` — confirm resource model is valid for the target environment/context
2. `easysam inspect cloud .` — confirm dependent external AWS resources exist and are reachable
3. `easysam generate .` — produce `template.yml` (and Swagger/Prismarine artifacts if applicable)
4. `easysam deploy .` — SAM build + deploy

## CI/CD recommended pipeline

The [Production Hardening guide](../../docs/PRODUCTION_HARDENING.md) recommends:

```bash
easysam --environment prod --context-file deploy-context.yaml inspect schema .
easysam --environment prod --context-file deploy-context.yaml inspect cloud .
easysam --environment prod --context-file deploy-context.yaml generate .
easysam --environment prod --context-file deploy-context.yaml deploy .
```

See [Operations Runbook](../operations/runbook.md) for more on validation and deployment safety.

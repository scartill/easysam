---
type: Reference
title: Source Map
description: Entry points, orchestration layers, supporting utilities, and key data surfaces across src/easysam/ plus schemas and Jinja templates.
tags: [source-map, modules, reference, easysam]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-19T15:38:50.328Z
sources:
  - id: openwiki-source-4ac1c0d195c62c553ac66f88
    resource: repo://src/easysam/cli.py
  - id: openwiki-source-5b82eb053aaed886997a474d
    resource: repo://src/easysam/commondep.py
  - id: openwiki-source-f8f2fdc7474ace3f59ac2193
    resource: repo://src/easysam/definitions.py
  - id: openwiki-source-76059441794faf322fc854f9
    resource: repo://src/easysam/deploy.py
  - id: openwiki-source-778363b9ddba351fd47aa280
    resource: repo://src/easysam/generate.py
  - id: openwiki-source-3225566694929dc59804d606
    resource: repo://src/easysam/load.py
  - id: openwiki-source-e7decf94ff906feb67d942e6
    resource: repo://src/easysam/local_cli.py
  - id: openwiki-source-b48422d4c307a93fa5963c57
    resource: repo://src/easysam/local_event.py
  - id: openwiki-source-7691698a7e4f744906c86f30
    resource: repo://src/easysam/local_handler.py
  - id: openwiki-source-890c694a00c3721f8b48e2ae
    resource: repo://src/easysam/local_routes.py
  - id: openwiki-source-4cfd1f5434670b9cf28d7460
    resource: repo://src/easysam/local_schemas.json
  - id: openwiki-source-210db2ad9d70a04e9487423c
    resource: repo://src/easysam/local_server.py
  - id: openwiki-source-401198b2a99299f078ce78a0
    resource: repo://src/easysam/schemas.json
  - id: openwiki-source-f15901941f091ca5f2d78245
    resource: repo://src/easysam/swagger.j2
  - id: openwiki-source-fc4a9d96fd7c4bfc4620150d
    resource: repo://src/easysam/template.j2
  - id: openwiki-source-205687dd76d7516f212885a8
    resource: repo://src/easysam/validate_schema.py
generated: { by: "openwiki/0.5.2", at: "2026-09-19T15:38:50.328Z" }
---

# Source Map

## `src/easysam/` — Core package

Entry points are shown first, followed by the orchestration layer, then supporting utilities and data surfaces.

### Entry points

| File | Responsibility | Notes |
| --- | --- | --- |
| `cli.py` | Click command group and CLI entrypoint. Global options: `--environment`, `--aws-profile`, `--context-file`, `--target-region`, `--verbose`. Commands: `generate`, `deploy`, `delete`, `cleanup`, `init`. Registers `inspect` and `local` subcommand groups in `main()`. | `repo://src/easysam/cli.py` |
| `local_cli.py` | `easysam local` subcommand group. Starts the local HTTP server (`easysam local .`) or invokes a single Lambda with a custom event (`easysam local invoke <function>`). Parses `--event` as a file path or inline JSON. | `repo://src/easysam/local_cli.py` |

### Orchestration layer

| File | Responsibility | Notes |
| --- | --- | --- |
| `generate.py` | Top-level generation orchestrator. Calls `load.resources`, invokes plugins if present, renders `template.j2` and `swagger.j2` via Jinja2 into `template.yml` and `build/swagger.yaml`, then generates Prismarine clients if the `prismarine` section is present. Supports `--override-main-template` and plugin template rendering. Returns `ProcessingResult` (`tuple[benedict, list[str]]`). | `repo://src/easysam/generate.py` |
| `load.py` | Core loading engine. Reads `resources.yaml`, loads `.env`, resolves `!Conditional` tags against the deploy context, applies overrides from context, recursively imports `easysam.yaml` files from `import` directories, preprocesses Prismarine tables, applies defaults, sets `enable_lambda_layer`, sorts sections. Exposes `resources()` as the main entry point. | `repo://src/easysam/load.py` |
| `deploy.py` | SAM CLI wrapper. Runs `generate`, checks pip/SAM CLI versions, removes and copies common dependencies, runs `sam build`, runs `sam deploy` with tags/region/profile, then reconciles event source mappings for pollable functions. `delete` uses CloudFormation `delete_stack` (supports `FORCE_DELETE_STACK`). | `repo://src/easysam/deploy.py` |

### Debug / inspection surface

| File | Responsibility | Notes |
| --- | --- | --- |
| `inspect.py` | Debug Click subgroup attached to the main CLI in `cli.main()`. Commands: `schema` (load + validate + optionally render a selected resource), `cloud` (live AWS validation of IAM policies and SSM/Lambda layers), `common-deps` (trace `common.*` imports for a lambda directory). | `repo://src/easysam/inspect.py` |

### Validation

| File | Responsibility | Notes |
| --- | --- | --- |
| `validate_schema.py` | JSON Schema Draft 7 validation against `schemas.json` (global `resources.yaml`) and `local_schemas.json` (per-file `easysam.yaml`). Custom validators: buckets, tables, streams, lambdas, paths, imports, prismarine, authorizers, MQTT. | `repo://src/easysam/validate_schema.py` |
| `validate_cloud.py` | Live AWS checks used by `inspect cloud`. Validates IAM policy existence for bucket `extaccesspolicy`, resolves SSM parameters for custom Lambda layers, validates layer ARNs via Lambda API. | `repo://src/easysam/validate_cloud.py` |

### Prismarine integration

| File | Responsibility | Notes |
| --- | --- | --- |
| `prismarine.py` | Generates `prismarine_client.py` from Prismarine model clusters. Reads the `prismarine` config section, calls `prisma_client.build_client` and `prisma_client.write_client`. Validates that cluster prefix starts with the master prefix. | `repo://src/easysam/prismarine.py` |

### Project scaffolding

| File | Responsibility | Notes |
| --- | --- | --- |
| `init.py` | Project scaffolder. Requires `pyproject.toml` to exist (expects `uv init` to have run first). Creates `resources.yaml`, `common/utils.py`, `backend/function/`, `thirdparty/requirements.txt`, `.gitignore`. Two modes: standard and `--prismarine` (adds `common/myobject/models.py`, `common/myobject/db.py`, `common/dynamo_access.py`, and a trigger lambda scaffold). | `repo://src/easysam/init.py` |

### Supporting utilities

| File | Responsibility | Notes |
| --- | --- | --- |
| `commondep.py` | AST-based dependency tracer. Scans `.py` files for `common.*` imports, recursively resolves transitive dependencies. Used by `deploy.copy_common_dependencies` and `inspect common-deps`. | `repo://src/easysam/commondep.py` |
| `definitions.py` | `FatalError` exception class (carries `errors: list[str]`) and `ProcessingResult` type alias (`tuple[benedict, list[str]]`). | `repo://src/easysam/definitions.py` |
| `utils.py` | `get_aws_client(service, cliparams)` — creates a boto3 client with an optional named AWS profile. | `repo://src/easysam/utils.py` |

### Local execution surface (local Lambda development)

These modules implement `easysam local` and are first-class surfaces for local development workflows.

| File | Responsibility | Notes |
| --- | --- | --- |
| `local_server.py` | FastAPI application factory for local Lambda execution. `local()` is the CLI-facing facade that loads resources, injects env vars/profile/region, and starts uvicorn. `create_app()` builds a FastAPI app with CORS, registers routes from `build_routes()`, and uses an asyncio lock (`_invocation_lock`) plus per-function envvar save/restore to serialize handler invocations. | `repo://src/easysam/local_server.py` |
| `local_routes.py` | Route construction for the local server. `RouteInfo` dataclass and `build_routes()` convert resolved resources into sorted routes: non-greedy API paths, greedy catch-all `/{path:path}` routes, and `/__fn/<name>` function URL routes. | `repo://src/easysam/local_routes.py` |
| `local_handler.py` | Lambda handler loading with module isolation. `MockLambdaContext` and `isolated_import_context()` (temporarily adjusts `sys.path`, cleans up `common.*` modules before import). `load_and_invoke()` loads `lambda_dir/index.py` via `importlib.util` and invokes `handler(event, context)`, supporting both sync and async handlers. | `repo://src/easysam/local_handler.py` |
| `local_event.py` | API Gateway event builders for local execution. Supports REST API (v1) and HTTP API (v2) event formats, including binary content detection, multi-value headers/query params, and auth context injection. `build_event()` dispatches by format. | `repo://src/easysam/local_event.py` |

## Data files

First-class surfaces that drive validation and code generation.

| File | Purpose | Notes |
| --- | --- | --- |
| `schemas.json` | JSON Schema (Draft 7) for global `resources.yaml` validation. ~16 KB. | `repo://src/easysam/schemas.json` |
| `local_schemas.json` | JSON Schema (Draft 7) for per-file `easysam.yaml` validation. ~8 KB. | `repo://src/easysam/local_schemas.json` |
| `template.j2` | Jinja2 template for SAM/CloudFormation output. ~30 KB. The primary code-generation artifact; renders `template.yml`. | `repo://src/easysam/template.j2` |
| `swagger.j2` | Jinja2 template for OpenAPI/Swagger spec (API Gateway). ~8 KB; renders `build/swagger.yaml` when `paths` are defined. | `repo://src/easysam/swagger.j2` |

## Runtime control flow

The main code-generation and deployment paths are:

1. **Generate path** — `cli.generate_cmd` → `generate.generate` → `load.resources` (parse, conditionals, overrides, imports, Prismarine preprocessing, defaults, sorting, schema validation) → plugin execution → Jinja rendering of `template.j2` and optionally `swagger.j2` → Prismarine client generation.
2. **Deploy path** — `cli.deploy_cmd` → `deploy.deploy` → `generate.generate` → version checks → `copy_common_dependencies` (AST-traced `common.*` imports) → `sam build` → `sam deploy` → event source mapping reconciliation.
3. **Local path** — `cli.main` registers `local`; `local_cli.local` (or `local_cli.invoke_cmd`) → `local_server.local` / `local_server.create_app` → FastAPI routes from `local_routes.build_routes` → `local_handler.load_and_invoke` with isolated import context and envvar save/restore.

Conditionals use the `!Conditional` YAML tag, which `load.conditional_constructor` converts into a `Conditional` object; `load.resolve_conditionals` filters the resource tree based on `environment` and `target_region` from the deploy context, raising `FatalError` when a required condition key is missing.

## Key types and contracts

- `ProcessingResult` = `tuple[benedict, list[str]]` — the standard return type for generation and loading functions.
- `FatalError` — raised by `resolve_conditionals` and `check_condition` when a deployment-context key is missing; caught by `generate.generate` to return an empty `benedict` plus error list.
- `deploy_ctx` — a dict carried through CLI context (`cli.easysam`) and into generation/deployment; keys include `environment`, `target_region`, and optionally `overrides` (from `--context-file`).
- `resources_data` — a `benedict` built from `resources.yaml` plus recursively imported `easysam.yaml` files; validated by `validate_schema` (global) and `validate_local_schema` (per-file).

## Tests

| File | Coverage |
| --- | --- |
| `tests/test_myapp.py` | Minimal app generation, template structure, API events |
| `tests/test_onelambda.py` | Simplest lambda-only app |
| `tests/test_conditionals.py` | `!Conditional` tag resolution with environment/region |
| `tests/test_errors.py` | Error reporting for invalid configs (`appwitherrors`) |
| `tests/test_aoss.py` | OpenSearch Serverless + DynamoDB streams |
| `tests/test_prismarine.py` | Prismarine TypedDict tables |
| `tests/test_prismarine_all.py` | Comprehensive Prismarine coverage |
| `tests/test_function_url.py` | Lambda Function URLs (simple + advanced) |
| `tests/test_gateway_cors.py` | GatewayResponse CORS headers for 401/403 |
| `tests/test_plugins.py` | Plugin template rendering |
| `tests/test_customlayer.py` | External Lambda layer via SSM |
| `tests/test_dynamottl.py` | DynamoDB TTL configuration |
| `tests/test_envvars_expansion.py` | `${VAR}` expansion in YAML |
| `tests/test_local_envvars.py` | Local `.env` file loading |
| `tests/test_userenvvars.py` | Global `envvars` in resources.yaml |
| `tests/test_greedy_paths.py` | API Gateway greedy path normalization |
| `tests/test_kinesis_multiple_buckets.py` | Kinesis multi-bucket streams |
| `tests/test_local_validation.py` | Local schema validation for easysam.yaml |
| `scripts/test_examples_generation.py` | Integration script: runs `generate` on every example directory |

## Existing documentation

| File | Content |
| --- | --- |
| `README.md` | Project overview, install, quick start, key concepts |
| `docs/CLI_REFERENCE.md` | Full CLI command and option reference |
| `docs/RESOURCE_REFERENCE.md` | Complete YAML field reference for all resource types |
| `docs/PRODUCTION_HARDENING.md` | Pre-production security and operations checklist |
| `example/README.md` | Catalog of 15+ example projects |
| `CHANGELOG.md` | Version history |

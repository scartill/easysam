---
type: Reference
title: Source Map
description: One-line reference for every Python module under src/easysam/, plus key data files (schemas, Jinja templates).
tags: [source-map, modules, reference]
---

# Source Map

## `src/easysam/` — Core package

| File | Lines (approx) | Purpose |
| --- | --- | --- |
| `cli.py` | ~100 | Click command group with global options (`--environment`, `--aws-profile`, `--context-file`, `--target-region`, `--verbose`). Commands: `init`, `generate`, `deploy`, `delete`, `inspect`. |
| `load.py` | ~490 | Core loading engine. Reads `resources.yaml`, loads `.env`, resolves `!Conditional` tags, applies overrides, recursively imports `easysam.yaml`, preprocesses Prismarine tables, sets defaults, sorts sections. |
| `generate.py` | ~115 | Orchestrates generation: calls `load.resources`, invokes plugins, renders `template.j2` and `swagger.j2` via Jinja2, calls `prismarine.generate` for client code. |
| `deploy.py` | ~210 | SAM CLI wrapper: version checks (pip, SAM), common dependency copy/cleanup, `sam build`, `sam deploy` with tags and region. `delete` via CloudFormation `delete_stack`. |
| `inspect.py` | ~100 | Debug sub-group: `schema` (validate + render resolved resources), `cloud` (live AWS validation), `common-deps` (trace common/ imports for a lambda). |
| `validate_schema.py` | ~290 | JSON Schema Draft 7 validation against `schemas.json` and `local_schemas.json`. Custom validators: buckets, tables, streams, lambdas, paths, imports, prismarine, authorizers, MQTT. |
| `validate_cloud.py` | ~95 | Live AWS checks: IAM policy existence for bucket `extaccesspolicy`, SSM parameter resolution for custom Lambda layers, Lambda layer ARN validation. |
| `prismarine.py` | ~57 | Generates `prismarine_client.py` from Prismarine model clusters. Reads `prismarine` config section, calls `prisma_client.build_client` and `write_client`. |
| `init.py` | ~280 | Project scaffolder. Creates `resources.yaml`, `common/utils.py`, `backend/function/`, `thirdparty/requirements.txt`, `.gitignore`. Two modes: standard and `--prismarine`. |
| `commondep.py` | ~90 | AST-based dependency tracer. Scans `.py` files for `common.*` imports, recursively resolves transitive dependencies. Used by deploy to copy needed common modules into lambda dirs. |
| `definitions.py` | ~12 | `FatalError` exception class (carries `errors: list[str]`) and `ProcessingResult` type alias (`tuple[benedict, list[str]]`). |
| `utils.py` | ~8 | `get_aws_client(service, cliparams)` — creates boto3 client with optional named profile. |

## Data files

| File | Purpose |
| --- | --- |
| `schemas.json` | JSON Schema (Draft 7) for global `resources.yaml` validation. ~16 KB. |
| `local_schemas.json` | JSON Schema (Draft 7) for per-file `easysam.yaml` validation. ~8 KB. |
| `template.j2` | Jinja2 template for SAM/CloudFormation output. ~30 KB. The primary code-generation artifact. |
| `swagger.j2` | Jinja2 template for OpenAPI 3.0 / Swagger spec (API Gateway). ~8 KB. |

## Tests

| File | Tests |
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
| `CHANGELOG.md` | Version history (current: 1.12.1) |

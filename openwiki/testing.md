---
type: Reference
title: Testing Guide
description: How EasySAM tests are structured, what patterns to follow, and how to add new tests. Covers example generation tests, unit/integration tests, local execution tests, and the example smoke test script.
tags: [testing, tests, examples, pytest, local-execution]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-19T15:38:50.328Z
sources:
  - id: openwiki-source-87816cc47b86eb3180d494e8
    resource: repo://example/README.md
  - id: openwiki-source-1ecc1b62f03333260246a477
    resource: repo://scripts/test_examples_generation.py
  - id: openwiki-source-3e5ad76f961629404d447930
    resource: repo://tests/test_aoss.py
  - id: openwiki-source-4460f5ab958f712b5013c18b
    resource: repo://tests/test_conditionals.py
  - id: openwiki-source-5e8cadf0f66d1a90726c6ab9
    resource: repo://tests/test_customlayer.py
  - id: openwiki-source-6c70c6274c8f14cab565b18a
    resource: repo://tests/test_dynamottl.py
  - id: openwiki-source-6191c12d5c632ebfe394e67a
    resource: repo://tests/test_envvars_expansion.py
  - id: openwiki-source-84c3da84f739332a2ca321fd
    resource: repo://tests/test_errors.py
  - id: openwiki-source-775f627f0df25b13f022b206
    resource: repo://tests/test_function_url.py
  - id: openwiki-source-20e65e35df8fc25cb23e183e
    resource: repo://tests/test_gateway_cors.py
  - id: openwiki-source-3874b9a2e4623c606c946833
    resource: repo://tests/test_greedy_paths.py
  - id: openwiki-source-ee69203678be74a052c6374b
    resource: repo://tests/test_kinesis_multiple_buckets.py
  - id: openwiki-source-03620955084f01b835f60b47
    resource: repo://tests/test_local_e2e.py
  - id: openwiki-source-e77a12af3b1a1ea3e67a64da
    resource: repo://tests/test_local_envvars.py
  - id: openwiki-source-2281ff99dd4b7e0661d88468
    resource: repo://tests/test_local_event.py
  - id: openwiki-source-44e517f26afb217626d1e052
    resource: repo://tests/test_local_handler.py
  - id: openwiki-source-3583496bbfd5273107147fc4
    resource: repo://tests/test_local_routes.py
  - id: openwiki-source-84b41857bf497e8e4790bfdc
    resource: repo://tests/test_local_server.py
  - id: openwiki-source-ab3208db94793e80367bd636
    resource: repo://tests/test_local_validation.py
  - id: openwiki-source-eb443876e2fbc96f3115f459
    resource: repo://tests/test_myapp.py
  - id: openwiki-source-681bf3b0a705bed5ea1eedc7
    resource: repo://tests/test_onelambda.py
  - id: openwiki-source-8f6ac3deda0d37ef113f2b44
    resource: repo://tests/test_plugins.py
  - id: openwiki-source-bf9910196cd9959387f1fdf9
    resource: repo://tests/test_prismarine_all.py
  - id: openwiki-source-8adca25caf129142d76e277a
    resource: repo://tests/test_prismarine.py
  - id: openwiki-source-3ce78c45b3189ec1bb42aae7
    resource: repo://tests/test_userenvvars.py
generated: { by: "openwiki/0.5.2", at: "2026-09-19T15:38:50.328Z" }
---

# Testing Guide

EasySAM uses pytest with multiple test categories: example-based generation tests that assert on SAM template output, unit tests for core modules like validation and event building, and integration tests that exercise the local execution server against example projects.

## Test structure

```
tests/
├── Generation tests (call generate() and assert on template.yml)
│   ├── test_myapp.py              # Minimal app: lambda + API + DynamoDB
│   ├── test_onelambda.py          # Lambda-only (no events)
│   ├── test_conditionals.py       # !Conditional resolution across environments
│   ├── test_errors.py             # Intentional schema errors
│   ├── test_aoss.py               # OpenSearch Serverless
│   ├── test_prismarine.py         # Prismarine TypedDict tables
│   ├── test_prismarine_all.py     # Comprehensive Prismarine
│   ├── test_function_url.py       # Lambda Function URLs
│   ├── test_gateway_cors.py       # GatewayResponse CORS
│   ├── test_plugins.py            # Plugin template rendering
│   ├── test_customlayer.py        # SSM-referenced Lambda layers
│   ├── test_dynamottl.py          # DynamoDB TTL
│   ├── test_envvars_expansion.py  # ${VAR} expansion
│   ├── test_userenvvars.py        # Global envvars in resources.yaml
│   ├── test_greedy_paths.py       # Greedy path normalization
│   └── test_kinesis_multiple_buckets.py  # Kinesis multi-bucket
├── Local validation tests (call resources() and assert on errors/data)
│   └── test_local_validation.py   # Schema validation error messages
├── Local execution tests (create_app + TestClient against examples)
│   ├── test_local_e2e.py          # Full flow: load → routes → handler → response
│   ├── test_local_server.py       # App factory and response normalization
│   ├── test_local_routes.py       # Route building (greedy, function URLs)
│   ├── test_local_event.py        # API Gateway event builders (REST/HTTP API)
│   ├── test_local_handler.py      # Handler isolation and async invocation
│   └── test_local_envvars.py      # .env file loading and template interpolation
├── Example smoke test script
│   └── test_examples_generation.py  # Runs generate on every example/
└── (integration test for real AWS)
    └── test_item_crud.py          # Referenced by prismapydantic example
```

## Test categories

### Example generation tests

These tests call `generate()` directly with a path to an example directory and assert on the resulting `template.yml`. They verify that resource generation produces correct SAM template structure for specific features.

Each generation test follows the same pattern (see `tests/test_myapp.py` as reference):

1. **Register SAM YAML constructors** for custom tags (`!GetAtt`, `!Sub`, `!Ref`):

```python
import yaml
from pathlib import Path
from easysam.generate import generate

def get_att_constructor(loader, node):
    value = loader.construct_scalar(node)
    return {'Fn::GetAtt': value.split('.')}

def sub_constructor(loader, node):
    return {'Fn::Sub': loader.construct_scalar(node)}

def ref_constructor(loader, node):
    return {'Ref': loader.construct_scalar(node)}

yaml.SafeLoader.add_constructor('!GetAtt', get_att_constructor)
yaml.SafeLoader.add_constructor('!Sub', sub_constructor)
yaml.SafeLoader.add_constructor('!Ref', ref_constructor)
```

2. **Call `generate()`** with cliparams and deploy context:

```python
cliparams = {'verbose': True}
deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
resources_data, errors = generate(cliparams, Path('example/myapp'), [], deploy_ctx)
```

3. **Assert no errors** (or assert expected errors for error-case tests):

```python
assert not errors
```

4. **Read and assert on the generated template**:

```python
with open('example/myapp/template.yml') as f:
    template = yaml.safe_load(f)

resources = template['Resources']
assert 'myfunctionFunction' in resources
assert resources['myfunctionFunction']['Type'] == 'AWS::Serverless::Function'
```

Error-case tests (like `test_errors.py`) assert that `errors` is non-empty and contains expected message fragments:

```python
assert errors
assert any('Error loading import file' in err for err in errors)
```

### Local validation tests

These tests call `resources()` directly (from `easysam.load`) to verify schema validation error messages and successful resource loading. They use temporary directories with crafted `resources.yaml` and `easysam.yaml` files.

See `tests/test_local_validation.py` for examples covering:
- Unexpected sections in `easysam.yaml`
- Missing required fields (e.g., `lambda.name`)
- Invalid integration configurations
- Memory value validation (minimum 128)

### Local execution tests

These tests exercise the local development server (`easysam.local_server`) by creating a FastAPI app from resources and using `fastapi.testclient.TestClient` to make HTTP requests. They cover:

- **End-to-end flow** (`test_local_e2e.py`): Loads `example/myapp`, creates an app, and tests route handling, CORS headers, and event format variations (v1/rest vs v2/http-api).
- **App factory** (`test_local_server.py`): Tests `create_app()` and `normalize_response()` with minimal resource configurations.
- **Route building** (`test_local_routes.py`): Tests `build_routes()` for greedy paths, function URLs, and empty configurations.
- **Event builders** (`test_local_event.py`): Tests `build_rest_api_event()` and `build_http_api_event()` with mocked Starlette requests.
- **Handler isolation** (`test_local_handler.py`): Tests `load_and_invoke()` for module isolation between lambdas and async handler support.

### Example smoke test script

`scripts/test_examples_generation.py` is an integration script that runs `easysam generate` on every directory under `example/`. It:

- Iterates all subdirectories in `example/`
- Runs `uv run easysam --aws-profile easysam-a --environment easysamdev --target-region us-east-1 generate <path>`
- Expects `appwitherrors` to fail (intentional errors for testing validation)
- Reports pass/fail with color output
- Exits non-zero if any unexpected failure occurs

Run it:

```bash
python scripts/test_examples_generation.py
# or
uv run python scripts/test_examples_generation.py
```

Note: this script invokes the CLI (`easysam generate`), not the Python API (`generate()`). It validates the end-to-end CLI-to-template pipeline, while the pytest generation tests validate the API directly.

## Example coverage matrix

The test suite covers these example features:

| Example | Test file | Focus |
| --- | --- | --- |
| `myapp` | `test_myapp.py`, `test_local_e2e.py` | Minimal app: lambda + API + DynamoDB |
| `onelambda` | `test_onelambda.py` | Lambda-only (no events) |
| `conditionals` | `test_conditionals.py` | !Conditional resolution across environments/regions |
| `appwitherrors` | `test_errors.py` | Intentional schema errors for validation testing |
| `aoss` | `test_aoss.py` | OpenSearch Serverless + DynamoDB Streams |
| `prismarine` | `test_prismarine.py`, `test_prismarine_all.py` | Prismarine TypedDict tables + stream triggers |
| `functionurl` | `test_function_url.py` | Lambda Function URLs (simple + CORS) |
| `plugins` | `test_plugins.py` | Template plugin rendering |
| `customlayer` | `test_customlayer.py` | SSM-referenced Lambda layers |
| `dynamottl` | `test_dynamottl.py` | DynamoDB TTL |
| `userenvvars` | `test_userenvvars.py` | Global envvars in resources.yaml |
| `kinesismutltiplebuckets` | `test_kinesis_multiple_buckets.py` | Kinesis multi-bucket delivery |
| (envvars expansion) | `test_envvars_expansion.py` | ${VAR} expansion from .env files |
| (local envvars) | `test_local_envvars.py` | .env file loading and template interpolation |
| (greedy paths) | `test_greedy_paths.py` | Greedy path normalization |

## Running tests

```bash
# All tests
uv run pytest

# Specific test
uv run pytest tests/test_myapp.py

# With verbose output
uv run pytest -v

# With coverage
uv run pytest --cov=easysam
```

## Adding a new test

1. **Create an example** under `example/` with the feature you want to test (if one doesn't exist). See `example/README.md` for the example catalog and common workflow.
2. **Add a test file** in `tests/` following the pattern above:
   - For generation tests: use `test_<feature>.py` and call `generate()` with the example path
   - For validation tests: use `test_local_validation.py` patterns with `tmp_path` fixtures
   - For execution tests: use `test_local_*.py` patterns with `create_app()` and `TestClient`
3. **Assert on generated resources** — check that the SAM template contains expected resource types and properties
4. **For error cases** — assert that `errors` is non-empty and contains expected message fragments

## Linting and formatting

EasySAM uses Ruff for linting and formatting (`pyproject.toml`):

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

Configuration:
- Line length: 120
- Quote style: single
- Lint rules: E (pycodestyle errors), F (pyflakes), W (pycodestyle warnings)

Recent commit db8532a applied Ruff fixes across all example files and source — keep new code Ruff-clean.

## Related pages

- [Generate and Deploy Workflow](workflows/generate-deploy.md) — end-to-end lifecycle including schema validation and generation
- [Operations Runbook](operations/runbook.md) — validation commands, deployment safety, and common errors

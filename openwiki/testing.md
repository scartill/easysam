---
type: Reference
title: Testing Guide
description: How EasySAM tests are structured, what patterns to follow, and how to add new tests. Covers unit tests, example generation tests, and the integration test script.
tags: [testing, tests, examples, pytest]
---

# Testing Guide

EasySAM uses pytest with a pattern of example-based integration tests: each test generates a SAM template from an example project and asserts on the output structure.

## Test structure

```
tests/
├── test_myapp.py                  # Minimal app: lambda + API + DynamoDB
├── test_onelambda.py              # Lambda-only (no events)
├── test_conditionals.py           # !Conditional resolution
├── test_errors.py                 # Intentional schema errors
├── test_aoss.py                   # OpenSearch Serverless
├── test_prismarine.py             # Prismarine TypedDict tables
├── test_prismarine_all.py         # Comprehensive Prismarine
├── test_function_url.py           # Lambda Function URLs
├── test_gateway_cors.py           # GatewayResponse CORS
├── test_plugins.py                # Plugin template rendering
├── test_customlayer.py            # SSM-referenced Lambda layers
├── test_dynamottl.py              # DynamoDB TTL
├── test_envvars_expansion.py      # ${VAR} expansion
├── test_local_envvars.py          # .env file loading
├── test_userenvvars.py            # Global envvars in resources.yaml
├── test_greedy_paths.py           # Greedy path normalization
├── test_kinesis_multiple_buckets.py  # Kinesis multi-bucket
└── test_local_validation.py       # Local schema validation

scripts/
└── test_examples_generation.py    # Runs generate on every example/
```

## How tests work

Each test follows the same pattern (see `tests/test_myapp.py` as reference):

1. **Call `generate()`** directly with a path to an example directory:

```python
from easysam.generate import generate

cliparams = {'verbose': True}
deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}
resources_data, errors = generate(cliparams, Path('example/myapp'), [], deploy_ctx)
```

2. **Assert no errors**:

```python
assert not errors
```

3. **Read and assert on the generated template**:

```python
with open('example/myapp/template.yml') as f:
    template = yaml.safe_load(f)

resources = template['Resources']
assert 'myfunctionFunction' in resources
assert myfunction['Type'] == 'AWS::Serverless::Function'
```

4. **Register SAM YAML constructors** for custom tags (`!GetAtt`, `!Sub`, `!Ref`):

```python
yaml.SafeLoader.add_constructor('!GetAtt', get_att_constructor)
yaml.SafeLoader.add_constructor('!Sub', sub_constructor)
yaml.SafeLoader.add_constructor('!Ref', ref_constructor)
```

## Example generation test script

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

## Running tests

```bash
# All tests
uv run pytest

# Specific test
uv run pytest tests/test_myapp.py

# With verbose output
uv run pytest -v
```

## Adding a new test

1. **Create an example** under `example/` with the feature you want to test (if one doesn't exist)
2. **Add a test file** in `tests/` following the pattern above
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

---
type: Reference
title: EasySAM Quickstart
description: Entry point for the EasySAM code wiki. Covers what EasySAM is, how to install it, the core workflow, and links to architecture, domain, operations, and testing docs.
tags: [easysam, quickstart, overview]
---

# EasySAM Quickstart

EasySAM is an opinionated YAML-to-SAM generator for modular AWS serverless applications. You define Lambda functions, API Gateway routes, DynamoDB tables, S3 buckets, SQS queues, Kinesis streams, OpenSearch Serverless collections, and IoT Core authorizers in a compact `resources.yaml` model, then EasySAM generates and deploys the resulting AWS SAM stack.

- **Language:** Python 3.12+ (src in `src/easysam/`)
- **Package:** `easysam` on PyPI, entrypoint `easysam.cli:main`
- **Current version:** 1.12.1 (see `pyproject.toml`, `CHANGELOG.md`)
- **Key dependencies:** Click (CLI), Jinja2 (template rendering), python-benedict (YAML dict handling), jsonschema (validation), Prismarine (model-driven DynamoDB), boto3 (AWS clients), rich (terminal output)

## Install

```bash
# Project-local (recommended)
uv add --dev easysam
uv run easysam --help

# Or global
pipx install easysam
```

## Core workflow (5 minutes)

```bash
mkdir my-easysam-app && cd my-easysam-app
uv init
uv add --dev easysam
uv run easysam init                    # scaffold resources.yaml + backend/
uv run easysam --environment dev inspect schema .   # validate
uv run easysam --environment dev generate .          # produce template.yml
uv run easysam --environment dev --aws-profile my-profile deploy . --tag project=demo
uv run easysam --environment dev --aws-profile my-profile delete --await
```

For a Prismarine scaffold: `uv run easysam init --prismarine`

## Documentation sections

| Section | What it covers |
| --- | --- |
| [Architecture Overview](architecture/overview.md) | CLI-to-deploy pipeline, module roles, Jinja template rendering |
| [Source Map](architecture/source-map.md) | One-line reference for every `src/easysam/` module |
| [Generate & Deploy Workflow](workflows/generate-deploy.md) | Step-by-step init→validate→generate→deploy→delete flow with sequence diagram |
| [Resource Model](domain/resource-model.md) | `resources.yaml` + `easysam.yaml` structure, conditionals, overrides, env vars |
| [Prismarine Integration](domain/prismarine.md) | Model-driven DynamoDB tables and client code generation |
| [Operations Runbook](operations/runbook.md) | Validation, cloud checks, deployment safety, production hardening |
| [Testing Guide](testing.md) | Test structure, example-generation tests, how to add tests |

## External documentation

- [CLI Reference](../docs/CLI_REFERENCE.md) — full command and option listing
- [Resource Reference](../docs/RESOURCE_REFERENCE.md) — complete YAML field reference
- [Production Hardening](../docs/PRODUCTION_HARDENING.md) — pre-production checklist
- [Examples Catalog](../example/README.md) — 15+ focused example projects
- [Changelog](../CHANGELOG.md) — version history
- [OpenWiki Update Workflow](../.github/workflows/openwiki-update.yml) — scheduled GitHub Actions workflow for wiki updates

## Backlog

- **Swagger/OpenAPI generation** (`swagger.j2`): only briefly mentioned in workflows; a dedicated page could document the Swagger template and API Gateway OpenAPI integration if it grows.
- **Plugin system** (`generate.py:invoke_plugin`): custom Jinja fragment rendering is documented in the resource reference but not yet given its own wiki page; defer until plugin complexity warrants it.

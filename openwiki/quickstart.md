---
type: Reference
title: EasySAM Quickstart
description: Entry point for the EasySAM code wiki. Covers what EasySAM is, how to install it, the core workflow, and links to architecture, domain, operations, and testing docs.
tags: [easysam, quickstart, overview]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-19T15:38:50.328Z
sources:
  - id: openwiki-source-ca6cb4b1a14fd7969dfae3ec
    resource: repo://CHANGELOG.md
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-4ac1c0d195c62c553ac66f88
    resource: repo://src/easysam/cli.py
generated: { by: "openwiki/0.5.2", at: "2026-09-19T15:38:50.328Z" }
---

# EasySAM Quickstart

EasySAM is an opinionated YAML-to-SAM generator for modular AWS serverless applications. You define Lambda functions, API Gateway routes, DynamoDB tables, S3 buckets, SQS queues, Kinesis streams, OpenSearch Serverless collections, and IoT Core authorizers in a compact `resources.yaml` model, then EasySAM generates and deploys the resulting AWS SAM stack.

- **Language:** Python 3.12+ (src in `src/easysam/`)
- **Package:** `easysam` on PyPI, entrypoint `easysam.cli:main`
- **Current version:** 1.13.0 (see `pyproject.toml`, `CHANGELOG.md`)
- **Key dependencies:** Click (CLI), Jinja2 (template rendering), python-benedict (YAML dict handling), jsonschema (validation), Prismarine (model-driven DynamoDB), boto3 (AWS clients), rich (terminal output), FastAPI + uvicorn (local execution server)

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
| [Architecture Overview](architecture/overview.md) | CLI-to-deploy pipeline, module roles, Jinja template rendering, and local execution server flow |
| [Source Map](architecture/source-map.md) | One-line reference for every `src/easysam/` module |
| [Generate & Deploy Workflow](workflows/generate-deploy.md) | Step-by-step init→validate→generate→deploy→delete flow with sequence diagram |
| [Resource Model](domain/resource-model.md) | `resources.yaml` + `easysam.yaml` structure, conditionals, overrides, env vars |
| [Prismarine Integration](domain/prismarine.md) | Model-driven DynamoDB tables and client code generation |
| [Local Execution Workflow](workflows/local-execution.md) | Local Lambda execution server, route registration, handler isolation, and envvar locking |
| [Conditionals and Deploy Overrides](integrations/conditional-overrides.md) | `!Conditional` resolution and context-file overrides, and how they interact with loading and validation |
| [Operations Runbook](operations/runbook.md) | Validation, cloud checks, deployment safety, production hardening |
| [Testing Guide](testing.md) | Test structure, example-generation tests, how to add tests |

## Task routing

Use this page as a starting point, then jump to the section that matches your task:

- **Starting a new project:** [Generate & Deploy Workflow](workflows/generate-deploy.md) for the full init→deploy sequence; [Resource Model](domain/resource-model.md) for the YAML shape you will edit.
- **Editing resources or wiring up DynamoDB:** [Resource Model](domain/resource-model.md) for fields and invariants; [Prismarine Integration](domain/prismarine.md) when you want model-driven tables and typed clients.
- **Running API Gateway routes locally:** [Local Execution Workflow](workflows/local-execution.md) for the server, route registration, event formats, and handler isolation.
- **Conditional or environment-specific resources:** [Conditionals and Deploy Overrides](integrations/conditional-overrides.md) for `!Conditional` semantics and `--context-file` overrides.
- **Validating, deploying, or tearing down stacks:** [Operations Runbook](operations/runbook.md) for pre-deploy checks, version gates, and delete semantics.
- **Understanding the codebase:** [Architecture Overview](architecture/overview.md) for the pipeline and module roles; [Source Map](architecture/source-map.md) for a module-by-module reference.
- **Adding or changing tests:** [Testing Guide](testing.md) for test categories and the example-generation pattern.

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

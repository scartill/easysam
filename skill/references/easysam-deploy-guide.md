# EasySAM Deployment Guide

## CLI Context & Options
- `--aws-profile`: Required for `deploy`, `delete`, and `inspect cloud` commands.
- `--environment`: Defines the stack environment (default is `dev`).

## Advanced Options & Commands
- **Cloud Validation (`inspect cloud`)**: Validates required cloud resources for deployment (e.g. checks if external buckets exist). This is an advanced and slow command.
  `uv run easysam --environment <env> --aws-profile <profile> inspect cloud .`
- `--context-file`: YAML deploy context file (useful for conditionals).
- `--target-region`: AWS region used in the deploy context.

## Typical Complete Workflow
1. Check the local YAML files configuration (typically `resources.yaml`).
2. Run schema validation: `uv run easysam --environment dev inspect schema .`
3. Generate template (optional, if you need to review `template.yml` before deploying): `uv run easysam --environment dev generate .`
4. Deploy the stack: `uv run easysam --environment dev --aws-profile my-profile deploy . --tag project=myapp`

## Directory Structure Notes
- Top-level AWS resource definitions are in `resources.yaml`.
- Lambda function local definitions are in `easysam.yaml` inside imported directories.
- Shared code for Lambdas should be placed in `common/`.
- Run `uv run easysam cleanup .` to remove copied `common` dependencies from lambda folders after deployment or manual inspection.

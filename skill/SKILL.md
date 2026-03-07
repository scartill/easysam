---
name: easysam-deploy
description: Agent-driven deployment and validation of AWS serverless applications using EasySAM. Use when instructed to deploy, validate, generate templates, or interact with an EasySAM project.
---
# EasySAM Deploy

This skill provides workflows for validating, generating, and deploying AWS serverless applications using the EasySAM CLI.

## Core Workflows

### 1. Validation

Before deploying, always validate the EasySAM schema:

```bash
uv run easysam --environment <env> inspect schema .
```

*Note: The default environment is usually `dev` unless specified.*

### 2. Generation

To generate the SAM template (and optional Swagger output) without deploying:

```bash
uv run easysam --environment <env> generate .
```

### 3. Deployment

To deploy the application (this automatically generates, builds, and deploys using SAM CLI):

```bash
uv run easysam --environment <env> --aws-profile <profile> deploy .
```

### 4. Deletion

To delete the deployed stack for a specific environment:

```bash
uv run easysam --environment <env> --aws-profile <profile> delete --await
```

## Advanced Options

For conditionals, deployments contexts, or advanced options, refer to [easysam-deploy-guide.md](references/easysam-deploy-guide.md).

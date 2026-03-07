# EasySAM

EasySAM is an opinionated YAML-to-SAM generator for modular AWS serverless applications.

It helps you define Lambda functions, API Gateway routes, DynamoDB tables, S3 buckets, SQS queues, Kinesis streams, OpenSearch Serverless collections, and IoT Core authorizers in a compact `resources.yaml` model, then generate and deploy the resulting SAM stack.

## Why EasySAM

- Simple YAML-first resource definitions
- Recursive import system (`import` + local `easysam.yaml`)
- Modular app structure with shared `common/` code support
- Built-in validation (`inspect schema`, `inspect cloud`)
- Native support for:
  - DynamoDB stream triggers from table definitions
  - DynamoDB TTL
  - Lambda Function URLs
  - Prismarine model-driven tables
  - OpenSearch Serverless search collections
  - MQTT/IoT Core custom authorizers

## Prerequisites

- Python 3.12+
- AWS credentials configured (named profile recommended)
- AWS SAM CLI 1.138.0+
- `pip` 25.1.1+ (used in deployment checks)
- One of:
  - `uv` (recommended for project-local workflows)
  - `pipx` (recommended for global CLI install)
  - `pip`

## Installation

Choose one installation method.

### Option A: project-local with uv

```bash
uv add --dev easysam
```

Use as:

```bash
uv run easysam --help
```

### Option B: global with pipx

```bash
pipx install easysam
```

Use as:

```bash
easysam --help
```

### Option C: global/local with pip

```bash
pip install easysam
```

## Quick start (5 minutes)

1. Create a Python project and initialize EasySAM:

```bash
mkdir my-easysam-app
cd my-easysam-app
uv init
uv add --dev easysam
uv run easysam init
```

For a Prismarine scaffold:

```bash
uv run easysam init --prismarine
```

2. Validate your resources:

```bash
uv run easysam --environment dev inspect schema .
```

3. Generate templates:

```bash
uv run easysam --environment dev generate .
```

4. Deploy to AWS:

```bash
uv run easysam --environment dev --aws-profile my-profile deploy . --tag project=easysam-demo
```

5. Delete stack when done:

```bash
uv run easysam --environment dev --aws-profile my-profile delete --await
```

For all options:

```bash
uv run easysam --help
```

## Minimal `resources.yaml`

```yaml
prefix: MyApp

import:
  - backend
```

EasySAM recursively finds `easysam.yaml` files under `backend/` and merges them.

## Local import file format (`easysam.yaml`)

```yaml
lambda:
  name: myfunction
  resources:
    tables:
      - MyItem
  integration:
    path: /items
    open: true
    greedy: false
```

You can also define tables locally:

```yaml
tables:
  MyItem:
    attributes:
      - name: ItemID
        hash: true
```

## Key concepts

### DynamoDB table triggers

Trigger a Lambda directly from table changes:

```yaml
tables:
  SearchableItem:
    attributes:
      - name: ItemID
        hash: true
    trigger: indexfunc
```

Advanced trigger configuration:

```yaml
tables:
  SearchableItem:
    attributes:
      - name: ItemID
        hash: true
    trigger:
      function: indexfunc
      viewtype: new-and-old
      batchsize: 10
      batchwindow: 5
      startingposition: latest
```

### Conditional resources

Conditional keys are resolved against deploy context (`environment`, `target_region`):

```yaml
buckets:
  ? !Conditional
    key: my-bucket
    environment: prod
    region: eu-west-2
  :
    public: true
    extaccesspolicy: ProdPolicy
```

Negation is supported using `~` (example: `environment: ~prod`).

### Deployment context overrides

Use a context file for CI/environment-specific patches:

```yaml
overrides:
  buckets/my-bucket/public: true
```

Then pass it with:

```bash
uv run easysam --environment dev --context-file deploy-context.yaml deploy .
```

### Prismarine integration

```yaml
prismarine:
  default-base: common
  access-module: common.dynamo_access
  modelling: typed-dict
  tables:
    - package: myobject
```

Set `modelling: pydantic` for Pydantic-based generated clients.

### MQTT / IoT Core custom authorizer

```yaml
mqtt:
  authorizer:
    function: mqtt-auth
  topics:
    - channels/*
```

If a function publishes to IoT topics, add `mqtt` in function `services`.

## Documentation

- [CLI reference](docs/CLI_REFERENCE.md)
- [Resource reference](docs/RESOURCE_REFERENCE.md)
- [Production hardening guide](docs/PRODUCTION_HARDENING.md)
- [Examples catalog](example/README.md)

## Examples

All examples live under `example/` and include focused scenarios such as:

- minimal app bootstrap
- conditionals and deploy context overrides
- custom Lambda layers
- global env vars and plugins
- DynamoDB TTL (plain + Prismarine)
- Prismarine TypedDict and Pydantic modelling
- OpenSearch Serverless + DynamoDB streams
- Kinesis with multiple S3 destinations

See the full index: [example/README.md](example/README.md).

## Development

```bash
git clone https://github.com/adsight-app/easysam.git
cd easysam
uv sync
source .venv/bin/activate
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Support

If you hit an issue:

1. Search [existing issues](https://github.com/adsight-app/easysam/issues)
2. Open a new issue with a reproducible example

## License

MIT. See [LICENSE](LICENSE).

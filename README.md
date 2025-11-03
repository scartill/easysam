# EasySAM

EasySAM is an opinionated YAML-to-SAM generator for modular AWS serverless applications.

It helps you define Lambda functions, API Gateway routes, DynamoDB tables, S3 buckets, SQS queues, Kinesis streams, OpenSearch Serverless collections, and IoT Core authorizers in a compact `resources.yaml` model, then generate and deploy the resulting SAM stack.

## Why EasySAM

- Simple YAML-first resource definitions
- Recursive import system (`import` + local `easysam.yaml`)
- Modular app structure with shared `common/` code support
- Built-in validation (`inspect schema`, `inspect cloud`)
- Native support for:
  - Environment variable expansion and `.env` loading
  - DynamoDB stream triggers from table definitions
  - DynamoDB TTL
  - Lambda Function URLs
  - Prismarine model-driven tables
  - OpenSearch Serverless search collections
  - MQTT/IoT Core custom authorizers

## Prerequisites

- Python 3.12+ (Your local/CI environment version should match the `python:` option in `resources.yaml` to ensure dependency compatibility)
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

```yaml
buckets:
  my-bucket:
    public: Boolean Optional (e.g., true), means Public read policy
    custompolicies: Optional Array of custom IAM policies
      - action: String or Array (e.g., "s3:GetObject" or ["s3:GetObject", "s3:PutObject"])
        effect: String Optional (e.g., "allow" or "deny", default: "allow")
        resource: String Optional (e.g., "arn:aws:s3:::my-bucket/*" or "any" for default, default: "any")
        principal: String or null Optional (e.g., "arn:aws:iam::123456789012:root" or null, default: null)
```

Custom policies are added to the bucket's S3 BucketPolicy. For public buckets, custom policies are merged with the existing public access policies. For non-public buckets, a new BucketPolicy is created if custompolicies are defined. The `resource` value of "any" translates to the bucket ARN (`arn:aws:s3:::bucket-name/*`). If `principal` is null, it is omitted from the policy statement.

### Queue Definitions

```yaml
queues:
  my-queue: null  # Simple queue (no custom policies)
  # OR
  my-queue:
    custompolicies: Optional Array of custom SQS queue policies
      - action: String or Array (e.g., "sqs:SendMessage" or ["sqs:SendMessage", "sqs:ReceiveMessage"])
        effect: String Optional (e.g., "allow" or "deny", default: "allow")
        resource: String Optional (e.g., "arn:aws:sqs:*:*:my-queue" or "any" for queue ARN, default: "any")
        principal: String or null Optional (e.g., "arn:aws:iam::123456789012:root" or null, default: null)
```

Custom policies create an SQS QueuePolicy resource. The `resource` value of "any" translates to the queue's ARN. If `principal` is null, it is omitted from the policy statement.

### Stream Definitions

1. Create a Python project and initialize EasySAM:

```bash
mkdir my-easysam-app
cd my-easysam-app
uv init
uv add --dev easysam
uv run easysam init
```

For a Prismarine scaffold:

```yaml
functions:
  my-lambda:
    uri: String (i.e., local path to the source)
    tables:
      - String (e.g., Items)
    polls:
      - String (e.g., my-stream) - incoming stream's name
    buckets:
      - String (e.g., my-bucket)
    send:
      - String (e.g., my-queue) - outgoing queue's name
    services:
      - comprehend  # Grants ComprehendBasicAccessPolicy
      - bedrock     # Grants bedrock:InvokeModel permission
    custompolicies: Optional Array of custom IAM policies
      - action: String or Array (e.g., "s3:GetObject" or ["s3:GetObject", "s3:PutObject"])
        effect: String Optional (e.g., "allow" or "deny", default: "allow")
        resource: String Optional (e.g., "arn:aws:s3:::my-bucket/*" or "any" for "*", default: "any")
        principal: String or null Optional (e.g., "arn:aws:iam::123456789012:root" or null, default: null)
```

Custom policies are added to the Lambda function's IAM execution role as inline policy statements. The `resource` value of "any" translates to "*" (any resource). If `principal` is null, it is omitted from the policy statement (which is appropriate for IAM role policies that don't need a principal field).

### API Gateway Definition

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
      - <table>
    buckets:
      - <bucket>
    send:
      - <queue>
    polls:
      - <stream>
    custompolicies: Optional Array of custom IAM policies
      - action: String or Array (e.g., "s3:GetObject" or ["s3:GetObject", "s3:PutObject"])
        effect: String Optional (e.g., "allow" or "deny", default: "allow")
        resource: String Optional (e.g., "arn:aws:s3:::my-bucket/*" or "any" for "*", default: "any")
        principal: String or null Optional (e.g., "arn:aws:iam::123456789012:root" or null, default: null)
  integration:
    path: /items
    open: true
    greedy: false
```

Locally-defined lambda URI is set to the path of the `easysam.yaml` file. Custom policies work the same way as in the main `resources.yaml` file.

#### Local Import

```yaml
tables:
  MyItem:
    attributes:
      - name: ItemID
        hash: true
```

## Key concepts

### Environment Variables and `.env` files

EasySAM automatically loads `.env` files if present in the target directory. It evaluates environment variables using the standard `${MY_VAR}` syntax in both global (`resources.yaml`) and local (`easysam.yaml`) files immediately after they are loaded.

You can also pass environment variables to your functions directly using the `envvars` property.

```yaml
functions:
  myfunc:
    uri: "src/"
    envvars:
      API_URL: "${API_URL}"
      LOG_LEVEL: "DEBUG"
```

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
- global and local env vars (with `.env` file support) and plugins
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

# EasySAM Resource Reference

This page documents the `resources.yaml` model expected by EasySAM.

All examples below use the normalized map/object style validated by `src/easysam/schemas.json`.

## Top-level structure

```yaml
prefix: MyApp

tags:
  team: platform

envvars:
  LOG_LEVEL: info

import:
  - backend
```

## Top-level keys

| Key | Type | Required | Description |
| --- | --- | --- | --- |
| `prefix` | string | yes | Prefix used in generated resource names |
| `python` | string | no | Target Python runtime version (default: 3.13). **Note:** Your local/CI build environment Python version should match this to ensure binary dependency compatibility. |
| `tags` | map<string,string> | no | Stack tags merged into SAM deploy tags |
| `envvars` | map<string,string> | no | Global Lambda environment variables |
| `buckets` | map | no | S3 bucket definitions |
| `queues` | map | no | SQS queue definitions |
| `streams` | map | no | Kinesis streams + Firehose destinations |
| `tables` | map | no | DynamoDB table definitions |
| `functions` | map | no | Lambda function definitions |
| `paths` | map | no | API Gateway integrations |
| `authorizers` | map | no | API authorizer Lambda configuration |
| `import` | list<string> | no | Import directories scanned for `easysam.yaml` |
| `prismarine` | object | no | Prismarine model integration |
| `plugins` | map | no | Jinja plugin templates |
| `mqtt` | object/null | no | IoT Core custom authorizer setup |
| `search` | object/null | no | OpenSearch Serverless collections |

## Buckets

```yaml
buckets:
  assets:
    public: false
  public-content:
    public: true
    extaccesspolicy: PublicContentReadPolicy
```

Fields:

- `public` (boolean, required)
- `extaccesspolicy` (string, optional)

## Queues

```yaml
queues:
  jobs:
  notifications:
```

Queue values are `null`/empty; queue names are the keys.

## Streams

Simple form:

```yaml
streams:
  simple:
    bucketname: private
    bucketprefix: simple/
    intervalinseconds: 60
```

Expanded form:

```yaml
streams:
  complex:
    buckets:
      private:
        bucketname: private
        bucketprefix: complex/
        intervalinseconds: 60
      external:
        extbucketarn: arn:aws:s3:::my-external-bucket
        bucketprefix: complex-external/
        intervalinseconds: 300
```

Bucket destination fields:

- `bucketname` or `extbucketarn` (exactly one)
- `bucketprefix` (optional, default: empty string)
- `intervalinseconds` (optional, default: `300`, min: `60`, max: `900`)

## Tables

```yaml
tables:
  MyItem:
    attributes:
      - name: ItemID
        hash: true
      - name: SortKey
        range: true
    indices:
      - name: BySortKey
        attributes:
          - name: SortKey
            hash: true
    ttl: ExpireAt
    trigger:
      function: indexfunc
      viewtype: new-and-old
      batchsize: 10
      batchwindow: 5
      startingposition: latest
```

Table fields:

- `attributes` (required)
- `indices` (optional)
- `ttl` (optional, DynamoDB TTL attribute name)
- `trigger` (optional): string or object

Trigger defaults:

- `viewtype`: `new-and-old`
- `startingposition`: `latest`

Allowed trigger values:

- `viewtype`: `keys-only`, `new`, `old`, `new-and-old`
- `startingposition`: `trim-horizon`, `latest`

## Functions

```yaml
functions:
  myfunction:
    uri: backend/function/myfunction
    timeout: 30
    memory: 1024
    tables:
      - MyItem
    buckets:
      - assets
    streams:
      - simple
    polls:
      - name: jobs
        batchsize: 10
        batchwindow: 5
    send:
      - notifications
    services:
      - bedrock
      - mqtt
    searches:
      - searchable
    schedule: rate(5 minutes)
    functionurl: true
    layers:
      ffmpeg: '{{resolve:ssm:/ffmpeg-latest-arn}}'
```

Notes:

- `uri` is required for top-level function definitions.
- For imported local lambdas, EasySAM derives `uri` from the `easysam.yaml` directory.
- `timeout` (integer, optional, default: 30)
- `memory` (integer, optional, default: 128)
- `services` supports: `comprehend`, `bedrock`, `mqtt`.

## Function URLs (Lambda)

Lambda Function URLs can be defined with simple or advanced configuration:

Simple form (defaults to `AuthType: NONE`):

```yaml
functions:
  hello-world:
    uri: backend/function/hello-world
    functionurl: true
```

Advanced form:

```yaml
functions:
  hello-custom:
    uri: backend/function/hello-custom
    functionurl:
      auth_type: NONE
      invoke_mode: BUFFERED
      cors:
        allow_origins:
          - "*"
        allow_methods:
          - GET
          - POST
        allow_headers:
          - Content-Type
        allow_credentials: true
        max_age: 3600
```

Fields:

- `auth_type` (enum: `NONE`, `AWS_IAM`, default: `NONE`)
- `invoke_mode` (enum: `BUFFERED`, `RESPONSE_STREAM`, default: `BUFFERED`)
- `cors` (object, optional):
    - `allow_origins` (list of strings)
    - `allow_methods` (list of strings)
    - `allow_headers` (list of strings)
    - `expose_headers` (list of strings)
    - `allow_credentials` (boolean)
    - `max_age` (integer)

## Paths (API Gateway)

### Lambda integration

```yaml
paths:
  /items:
    integration: lambda
    function: myfunction
    open: true
    greedy: false
```

Defaults:

- `integration`: `lambda`
- `greedy`: `true` (if omitted)

`open` and `authorizer` are mutually exclusive.

### Dynamo integration

```yaml
paths:
  /items/{id}:
    integration: dynamo
    method: get
    parameters:
      - id
    role: GatewayDynamoRole
    action: GetItem
    requestTemplate: |
      {}
    responseTemplateFile: build/response.vtl
```

### SQS integration

```yaml
paths:
  /jobs:
    integration: sqs
    method: post
    role: GatewaySQSRole
    queue: jobs
    requestTemplate: |
      Action=SendMessage
    responseTemplate: |
      {"ok": true}
```

For SQS, provide request and response templates (inline or file-based).

## Authorizers

```yaml
authorizers:
  jwt-auth:
    function: authfunc
    token: Authorization
    ttl: 300
```

Exactly one identity style is required:

- `token`
- `query`
- `headers`

## Import

```yaml
import:
  - backend
```

EasySAM recursively loads `easysam.yaml` files under each import directory.

Supported keys inside local `easysam.yaml`:

- `lambda`
- `tables`
- `import` (local file imports)

## Prismarine

```yaml
prismarine:
  default-base: common
  access-module: common.dynamo_access
  extra-imports:
    - common.myobject.models:NestedItem
  modelling: pydantic
  tables:
    - package: myobject
      base: common
```

`modelling` values:

- `typed-dict` (default)
- `pydantic`

## Plugins

```yaml
plugins:
  myplugin:
    template: customlambda.j2
    aux:
      funname: mycustomfun
```

Each plugin renders a template to `<plugin-name>.yaml`.

## MQTT (IoT Core)

```yaml
mqtt:
  authorizer:
    function: mqtt-auth
  topics:
    - channels/*
```

Generated resources include IoT authorizer, Lambda permission for IoT invocation, and optional client policy for `topics`.

## Search (OpenSearch Serverless)

```yaml
search:
  searchable:
```

Define one or more collection keys. Empty `search:` is normalized to a default `searchable` collection.

## Conditionals

Conditional keys can be used inside map sections:

```yaml
buckets:
  ? !Conditional
    key: my-bucket
    environment: prod
    region: eu-west-2
  :
    public: true
```

Condition values are matched against deploy context:

- `environment`
- `target_region` (mapped from conditional key `region`)

Use `~` for negation, for example: `environment: ~prod`.

## Deploy context file

```yaml
overrides:
  buckets/my-bucket/public: true
```

Pass with:

```bash
easysam --environment dev --context-file deploy-context.yaml deploy .
```

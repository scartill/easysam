# Cloud structure for simplified SAM templating (EASYSAM)

## Table Definitions

```yaml
tables:
  - name: String (e.g., Items)
    attributes:
      - name: String (e.g., ItemID)
        type: String (e.g., S), dynamodb type
        hash: Boolean Optional (e.g., true), means Partition Key
        range: Boolean Optional (e.g., true) means Sort Key
    indices:
      - name: String
        attributes:
          - name: String
            type: String
            hash: Boolean Optional
            range: Boolean Optional
```

## Bucket Definition

```yaml
buckets:
  - name: String (e.g., my-bucket)
    public Boolean Optional (e.g., true), means Public read policy
```

## Queue Definition

```yaml
queues:
  - name: String (e.g., my-queue)
```

## Stream Definition

```yaml
streams:
  - name: String (e.g., my-stream)
```

## Lambda Definition

```yaml
  - name: String (e.g., my-lambda)
    uri: String (i.e., local path to the source)
    tables:
      - String (e.g., Items)
    polls:
      - String (e.g., my-stream) - incoming stream's name
    buckets:
      - String (e.g., my-bucket)
    send:
      - String (e.g., my-queue) - outgoing queue's name
```

## API Gateway Definition

### Lambda Function Integration

```yaml
  path: # (e.g., /my-lambda)
    function: String # (e.g., my-lambda)
    authorizer: String # (e.g., my-authorizer)
    greedy: Boolean # (e.g., false)
```

### Direct DynamoDB Integration

```yaml
  path: # (e.g., /my-lambda)
    integration: dynamo
    method: String # (e.g., get)
    parameters: [String] # (e.g., [channel])
    role: GatewayDynamoRole
    action: String # (e.g., GetItem)
    requestTemplate: VTL Template 
    responseTemplateFile: VTL File Path
```

### Direct SQS Integration

```yaml
  path: # (e.g., /my-lambda)
    integration: sqs
    method: String # (e.g., post)
    role: GatewaySQSRole
    queue: String # (e.g., my-queue)
    requestTemplate: String # VTL Template
    responseTemplateFile: String # VTL File Path
    authorizer: String # (e.g., my-authorizer)
```

## Import

```yaml
import:
  - <directory>
```

The `import` directive searches recursively for `easysam.yaml` files (local definitions) in the specified directory and merges them into the current template.

### Local Lambda Definition

```yaml
lambda:
  name: <name>
  resources:
    tables:
      - <table>
    buckets:
      - <bucket>
    send:
      - <queue>
    polls:
      - <stream>
  integration:
    path: <path>
    open: <boolean>
    greedy: <boolean>
    authorizer: <authorizer-lambda-name>
```

Locally-defined lambda URI is set to the path of the `easysam.yaml` file.

### Local Import

```yaml
import:
  - <file>
```

## Prismarine Support

```yaml
prismarine:
  default-base: <base-path>
  tables:
    - package: <package-to-import>
      base: <optional-base-path>
```


# SAM Template Generator

Generates a SAM template and a API Gateway Swagger definition from a resource definition from simplified YAML files.

## Getting Usage Information

```pwsh
python generate.py --help
```

## Standard Usage

```pwsh
python generate.py --resources <resources.yaml> --swagger <swagger.yaml> --template <template.yml>
```

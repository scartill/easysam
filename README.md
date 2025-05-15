# Opionated Modular Cloud Deployment Tool

## Installation

```pwsh
pip install easysam
```

## Usage

Initialize a new application. This command creates a new directory with the given name and generates the necessary files for a single lambda function and a single table.

```pwsh
easysam init <app-name>
```

Deploy the application:

```pwsh
easysam deploy <app-directory> <aws-stack-name>
```

For more options, use the `--help` flag:

```pwsh
easysam --help
```

## Resource Definitions

### Table Definitions

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

### Bucket Definitions

```yaml
buckets:
  - name: String (e.g., my-bucket)
    public Boolean Optional (e.g., true), means Public read policy
```

### Queue Definitions

```yaml
queues:
  - name: String (e.g., my-queue)
```

### Stream Definitions

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

### API Gateway Definition

#### Lambda Function Integration

```yaml
  path: # (e.g., /my-lambda)
    function: String # (e.g., my-lambda)
    authorizer: String # (e.g., my-authorizer)
    greedy: Boolean # (e.g., false)
```

#### Direct DynamoDB Integration

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

#### Direct SQS Integration

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

### Import

```yaml
import:
  - <directory>
```

The `import` directive searches recursively for `easysam.yaml` files (local definitions) in the specified directory and merges them into the current template.

#### Local Lambda Definition

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

#### Local Import

```yaml
import:
  - <file>
```

### Prismarine Support

```yaml
prismarine:
  default-base: <base-path>
  tables:
    - package: <package-to-import>
      base: <optional-base-path>
```

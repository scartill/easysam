# EasySAM - Opinionated Modular Cloud Deployment Tool

EasySAM is a simple, opinionated tool for deploying cloud resources with a focus on simplicity and modularity. It provides a streamlined way to define and deploy AWS resources using YAML configuration files, making cloud infrastructure management more accessible and maintainable.

## Features

- Simple YAML-based resource definitions
- Modular architecture with import support
- Comprehensive AWS resource support:
  - Lambda functions
  - DynamoDB tables
  - S3 buckets
  - SQS queues
  - Kinesis streams
  - API Gateway integrations
- Easy initialization of new projects

## Installation

```pwsh
pip install easysam
```

## Quick Start

1. Initialize a new application:
```pwsh
easysam init my-app
```

2. Deploy your application:
```pwsh
easysam deploy --tag my-tag=my-value my-app my-stack-name
```

Please note that at least one tag is required.

For more options, use the `--help` flag:
```pwsh
easysam --help
```

### Windows

On Windows, it may be necessary to run the `deploy` command with the `-sam-tool sam.cmd` option.

## Prerequisites  
* Python 3.12 or higher with `pip` on PATH
* uv 0.5 or higher
* AWS SAM CLI 1.138 or higher on PATH
* AWS Credentials Configured

## Usage

First, initialize a new application. This command creates a new directory with the given name and generates the necessary files for a single lambda function and table. This version only supports AWS as a backend, and Python as a language. 

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

The entry point for all cloud resources definitions in the `resources.yaml` file. See [example applications](./example) for how applications are structures.

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
    services:
      - comprehend
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

## Development

### Setting up the development environment

1. Clone the repository:
```bash
git clone https://github.com/adsight-app/easysam.git
cd easysam
```

2. Install development dependencies and activate the virtual environment:
```bash
uv sync
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and suggest improvements.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions, please:  
1. Search [existing issues](https://github.com/adsight-app/easysam/issues)  
2. Create a new issue if needed

## Changelog

See [CHANGELOG.md](https://github.com/adsight-app/easysam/blob/main/CHANGELOG.md) for a list of changes between versions.

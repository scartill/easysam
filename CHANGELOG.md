# 1.11.0

- Added `budget` service support for Lambda functions.
- Added environment variable expansion and local `.env` support.
- Added comprehensive deployment guide and expanded documentation for services.
- Normalized greedy root paths for API Gateway routes.
- Removed unused `yaml.YAMLObject` inheritance and validation stubs.

# 1.10.1

- Added `schedule` support to the root of local lambda definitions (`easysam.yaml`)
- Added `Scheduled Lambda Example` demonstrating the new `schedule` configuration
- Removed unused `get_aws_resource` dead code from `cloud.py`
- Standardized example function naming and updated documentation

# 1.10.0

- Added global `python` setting for configuring Lambda runtime version
- Added `timeout` support to Lambda function configuration
- Added local JSON schema validation for `easysam.yaml` files
- Added Python 3.14 support and example configuration
- Refactored load logic and eliminated redundant dictionary iterations
- Updated local schemas with flexible poll, layers, and type support
- Switched prismarine dependency to PyPI release `>=1.5.4`
- Removed unused cloud.py and AWS VPC scanning logic
- Changed default Python runtime version to 3.13

# 1.9.2

- Fixed MQTT Authorizer Bug

# 1.9.1

- Fixed a bug where a Lambda function without any event sources (API Gateway, SQS, etc.) would fail to deploy.
- Fixed a bug where a SAM template without any defined outputs would fail to deploy.
- Fixed a bug where MQTT authorizer permissions were rendered even when the authorizer was not defined.

# 1.9.0

- Added Lambda Function URL support for Lambda functions
- Supports simple (`functionurl: true`) and advanced (`auth_type`, `invoke_mode`, `cors`) configurations
- Improved integration test coverage for example configurations

# 1.8.2

- Fixed repository links

# 1.8.1

- Added `ACCOUNT_ID` global environment variable for all Lambda functions (`AWS::AccountId`)

# 1.8.0

- Added MQTT (IoT Core) support with custom Lambda authorizer
- Added `mqtt` service for Lambda functions to publish to IoT topics
- Automatic provisioning of IoT Authorizer, Lambda permissions, and client policies

# 1.7.1

- Fixed a bug with Prismarine Pydantic models by upgrading to Prismarine 1.5.2

# 1.7.0

- Added support for Pydantic models in Prismarine
- Added support for DynamoDB TTL attributes

# 1.6.0

- Added support for the AWS Bedrock permissions
- Changed `init` command to work in the current directory (requires `uv init` to be run first)
- Added `--prismarine` option to `init` command for scaffolding minimal Prismarine applications
- Removed `app-name` argument from `init` command

# 1.5.1

- Fixed multicollection AOSS deployment
- Added default search index support

# 1.5.0

- Added DynamoDB Streams support for lambda functions
- Simple table-level `trigger` configuration - just specify the function name to enable automatic stream processing
- Supports both simple (`trigger: my-function`) and advanced forms with options
- User-friendly view type constants: `keys-only`, `new`, `old`, `new-and-old` (default: `new-and-old`)
- User-friendly starting position: `trim-horizon`, `latest` (default: `latest`)
- Optional batch size and batch window configuration for stream event processing
- Automatic validation ensures trigger functions exist before deployment
- Updated `aoss` example to demonstrate automatic OpenSearch indexing via DynamoDB Streams
- Breaking change: Removed `tablestreams` from lambda function configuration in favor of table-based `trigger` configuration

# 1.4.1

- Fixed a bug with json load encoding issue

# 1.4.0

- Added custom `layers` support for lambda functions
- Fixed a bug with empty `streams` resources
- Added `envvars` (global environment variables for functions)
- Added `tags` support to the resources.yaml file

# 1.3.0

- Added multibucket stream support
- Added conditional resources support
- Added `inspect schema` command to validate the resources.yaml file
- Added `inspect cloud` command to inspect required cloud resources

# 1.2.0

- Added `extra-imports` support to Prismarine
- Added `version` command

## 1.1.0

- Prismarine support
- Added `delete` command
- Added `cleanup` command
- Added `inspect` command

## 1.0.0

- First published version

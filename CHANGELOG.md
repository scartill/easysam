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

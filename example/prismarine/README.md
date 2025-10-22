# Prismarine Example with DynamoDB Triggers

This example demonstrates how to use **Prismarine models with DynamoDB triggers** in EasySAM.

## Overview

This example shows how to configure a Lambda function to be triggered automatically when items are inserted, modified, or deleted in a DynamoDB table that is defined using Prismarine models.

## Key Components

### 1. Prismarine Model with Trigger

In `common/myobject/models.py`, the `Item` model is decorated with a `trigger` parameter:

```python
@c.model(PK='Foo', SK='Bar', trigger='itemlogger')
class Item(TypedDict):
    Foo: str
    Bar: str
    Baz: NotRequired[str]
```

The `trigger` parameter can be:
- **String**: Simple function name (e.g., `trigger='itemlogger'`)
- **Dict**: Full configuration with options:
  ```python
  trigger={
      'function': 'itemlogger',
      'viewtype': 'new-and-old',  # keys-only, new, old, or new-and-old
      'batchsize': 100,            # Optional: number of records per batch
      'batchwindow': 5,            # Optional: max seconds to wait for batch
      'startingposition': 'latest' # trim-horizon or latest
  }
  ```

### 2. Trigger Lambda Function

The `backend/function/itemlogger/index.py` contains a Lambda handler that:
- Receives DynamoDB stream events
- Processes INSERT, MODIFY, and REMOVE operations
- Logs all changes to CloudWatch

### 3. Resources Configuration

The `resources.yaml` file:
- Imports backend functions
- Configures Prismarine integration
- EasySAM automatically creates the DynamoDB stream and EventSourceMapping

## What Gets Generated

When you run `easysam generate`, the following AWS resources are created:

1. **DynamoDB Table** (`MyAppWithPrismarineItem`) with:
   - StreamSpecification enabled (NEW_AND_OLD_IMAGES)
   - Point-in-time recovery

2. **Lambda Function** (`itemlogger`) with:
   - Permissions to read from DynamoDB table
   - Permissions to access DynamoDB streams

3. **EventSourceMapping** that:
   - Connects the DynamoDB stream to the Lambda function
   - Configured with specified batch size, window, and starting position

## Usage

Generate the SAM template:
```bash
uv run easysam generate example/prismarine
```

The generated `template.yml` will include all necessary resources for the trigger to work.

## Benefits

- **Declarative**: Define triggers directly in your model decorators
- **Type-Safe**: Works seamlessly with TypedDict models
- **Consistent**: Same trigger configuration as explicit YAML table definitions
- **Automatic**: EasySAM handles all IAM permissions and resource dependencies

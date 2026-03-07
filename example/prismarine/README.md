# Prismarine + DynamoDB Trigger Example

This example demonstrates model-driven table generation with Prismarine and automatic DynamoDB stream triggers.

## What this example demonstrates

- Prismarine `TypedDict` model definitions
- Trigger configuration in model decorator (`trigger='itemlogger'`)
- Automatic stream + event source mapping generation

## Source configuration

`common/myobject/models.py`:

```python
@c.model(PK='Foo', SK='Bar', trigger='itemlogger')
class Item(TypedDict):
    Foo: str
    Bar: str
    Baz: NotRequired[str]
```

Trigger can be:

- string: `trigger='itemlogger'`
- dict with advanced options (`viewtype`, `batchsize`, `batchwindow`, `startingposition`)

`resources.yaml`:

```yaml
prefix: MyAppWithPrismarine

import:
  - backend

prismarine:
  default-base: common
  access-module: common.dynamo_access
  tables:
    - package: myobject
```

## Generate and inspect

```bash
easysam --environment dev inspect schema example/prismarine
easysam --environment dev generate example/prismarine
```

Generated resources include:

- `MyAppWithPrismarineItem` DynamoDB table
- `itemlogger` Lambda function
- DynamoDB `StreamSpecification`
- `AWS::Lambda::EventSourceMapping` to connect table stream to lambda

## Deploy

```bash
easysam --environment dev --aws-profile my-profile deploy example/prismarine
```

## Verify behavior

After inserting/updating/deleting table items, check CloudWatch logs for:

- function: `itemlogger-dev`
- event names: `INSERT`, `MODIFY`, `REMOVE`

## Extra reference

See `common/myobject/advanced_example.py` for additional trigger patterns.

## Cleanup

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

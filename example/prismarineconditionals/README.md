# Prismarine + DynamoDB Trigger Example

This example demonstrates model-driven table generation with Prismarine and automatic DynamoDB stream triggers.

## What this example demonstrates

- Prismarine `TypedDict` model definitions
- Trigger configuration in model decorator (`trigger='itemlogger'`)
- Conditional table inclusion via !Conditional
- Conditional trigger attachment to tables
- Conditional table inclusion

## Source configuration

`common/myobject/models.py`:

```python
@c.model(PK='Foo', SK='Bar', trigger='itemlogger')
class Item(TypedDict):
    Foo: str
    Bar: str
    Baz: NotRequired[str]
```

`common/condition/models.py`

```python
@c.model(PK='Foo', SK='Bar', trigger='itemlogger')
class Condition(TypedDict):
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
      trigger:
        ? !Conditional
          key: function
          environment:
            - prodsam
            - stagingsam
        : itemlogger
  conditional-tables:
    ? !Conditional
      key: tables
      environment:
        - prodsam
        - stagingsam
    : - package: condition
```

## Generate and inspect

```bash
easysam --environment dev inspect schema example/prismarineconditional
easysam --environment dev generate example/prismarineconditional
```

Generated resources include:

- `MyAppWithPrismarineItem` DynamoDB table
- `itemlogger` Lambda function is applied only if environment is allowed
- DynamoDB `StreamSpecification`
- `AWS::Lambda::EventSourceMapping` to connect table stream to lambda
- `MyAppWithPrismarineItem` DynamoDB table created in allowed environments

## Deploy

```bash
easysam --environment dev --aws-profile my-profile deploy example/prismarineconditional
```

## Verify behavior

Behavior depends on the environment:

- **Base table (`myobject`)**
  - Always created
  - If trigger is enabled:
    - Writes (`INSERT`, `MODIFY`, `REMOVE`) appear in CloudWatch logs
    - Lambda: `itemlogger-<environment>`
  - If trigger is NOT enabled:
    - Table works normally (read/write)
    - No stream, no Lambda, no logs

- **Conditional table (`condition`)**
  - Created only in allowed environments (`devaoss`, `prodsam`, `stagingsam`)
  - In other environments:
    - Table is not created at all

## Cleanup

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

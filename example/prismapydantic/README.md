# Prismarine Pydantic Example

This example demonstrates Prismarine client generation with Pydantic models.

## What this example demonstrates

- `prismarine.modelling: pydantic`
- Pydantic model definitions in `common/myobject/models.py`
- Generated typed client usage through CRUD integration test

`resources.yaml`:

```yaml
prefix: PrismaPydantic

prismarine:
  default-base: common
  access-module: common.dynamo_access
  tables:
    - package: myobject
  modelling: pydantic
```

## Validate and generate

```bash
easysam --environment easysamdev inspect schema example/prismapydantic
easysam --environment easysamdev generate example/prismapydantic
```

## Deploy

```bash
easysam --environment easysamdev --aws-profile my-profile deploy example/prismapydantic
```

## Run CRUD integration test

From `example/prismapydantic`:

```bash
AWS_PROFILE=my-profile python3 -m pytest tests/test_item_crud.py
```

The test executes real CRUD operations against the deployed DynamoDB table and then deletes created data.

## Cleanup

```bash
easysam --environment easysamdev --aws-profile my-profile delete --await
```

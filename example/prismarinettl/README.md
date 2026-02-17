# Prismarine TTL Example

This example demonstrates DynamoDB TTL declared directly in a Prismarine model.

## What this example demonstrates

`common/myobject/models.py`:

```python
@c.model(PK='Foo', SK='Bar', ttl='ExpireAt')
class Item(TypedDict):
    Foo: str
    Bar: str
    Baz: NotRequired[str]
    ExpireAt: int
```

- Model-driven table generation
- TTL configuration through Prismarine metadata

## Validate and generate

```bash
easysam --environment dev inspect schema example/prismarinettl
easysam --environment dev generate example/prismarinettl
```

In generated `template.yml`, verify:

```yaml
TimeToLiveSpecification:
  AttributeName: ExpireAt
  Enabled: true
```

## Deploy

```bash
easysam --environment dev --aws-profile my-profile deploy example/prismarinettl
```

## Cleanup

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

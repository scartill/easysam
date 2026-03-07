# DynamoDB TTL Example

This example shows how to configure DynamoDB Time To Live (TTL) with EasySAM.

## What this example demonstrates

- Table-level TTL in local `easysam.yaml`
- Generated `TimeToLiveSpecification` in SAM template
- Expected runtime behavior for expiring items

## Source configuration

`backend/database/easysam.yaml`:

```yaml
tables:
  MyItem:
    attributes:
      - hash: true
        name: ItemID
    ttl: ExpireAt
```

`ttl: ExpireAt` means DynamoDB treats `ExpireAt` as a Unix timestamp (seconds since epoch).

## Generate and inspect

```bash
easysam --environment dev inspect schema example/dynamottl
easysam --environment dev generate example/dynamottl
```

In generated `template.yml`, verify:

```yaml
TimeToLiveSpecification:
  AttributeName: ExpireAt
  Enabled: true
```

## Deploy

```bash
easysam --environment dev --aws-profile my-profile deploy example/dynamottl
```

## Write an expiring item

```python
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('DynTTLMyItem-dev')
expire_at = int((datetime.now() + timedelta(hours=1)).timestamp())

table.put_item(
    Item={
        'ItemID': 'item-123',
        'ExpireAt': expire_at,
    }
)
```

## Important TTL behavior

- Deletion is asynchronous (typically within up to 48 hours after expiry).
- TTL deletions do not consume write capacity.

## Cleanup

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

# DynamoDB TTL Example

This example demonstrates how to configure **DynamoDB Time To Live (TTL)** in EasySAM.

## Overview

This example shows how to define a DynamoDB table with TTL enabled, which allows DynamoDB to automatically delete items after a specified expiration time.

## Key Components

### 1. Table Definition with TTL

In `backend/database/easysam.yaml`, the `MyItem` table is configured with a TTL attribute:

```yaml
tables:
  MyItem:
    attributes:
    - hash: true
      name: ItemID
    ttl: ExpireAt
```

The `ttl` parameter specifies the attribute name that will store the expiration timestamp. Items will be automatically deleted when their TTL timestamp has passed.

### 2. Generated DynamoDB Table

When you run `easysam generate`, the following AWS resources are created:

1. **DynamoDB Table** (`DynTTLMyItem`) with:
   - Hash key: `ItemID`
   - Billing mode: PAY_PER_REQUEST
   - Point-in-time recovery enabled (14 days)
   - **TTL enabled** on the `ExpireAt` attribute

The generated table includes:

```yaml
TimeToLiveSpecification:
  AttributeName: ExpireAt
  Enabled: true
```

## How TTL Works

1. **Set TTL Value**: When creating or updating an item, set the `ExpireAt` attribute to a Unix timestamp (number of seconds since epoch).

2. **Automatic Deletion**: DynamoDB automatically deletes items within 48 hours after the TTL timestamp has passed.

3. **No Additional Cost**: TTL deletion is free and doesn't consume write capacity units.

## Usage

Generate the SAM template:

```bash
uv run easysam generate example/dynamottl
```

The generated `template.yml` will include the DynamoDB table with TTL enabled.

## Example: Setting TTL on Items

When inserting items into the table, include the `ExpireAt` attribute:

```python
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('DynTTLMyItem-dev')

# Item expires in 1 hour
expire_at = int((datetime.now() + timedelta(hours=1)).timestamp())

table.put_item(
    Item={
        'ItemID': 'item-123',
        'ExpireAt': expire_at,
        # ... other attributes
    }
)
```

## Benefits

- **Automatic Cleanup**: No need to manually delete expired items
- **Cost Effective**: TTL deletion is free
- **Declarative**: Define TTL directly in your table configuration
- **Simple**: EasySAM handles all the TTL specification setup automatically

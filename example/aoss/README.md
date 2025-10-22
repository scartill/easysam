# Amazon OpenSearch Serverless (AOSS) Example

This example demonstrates how to use Amazon OpenSearch Serverless with EasySAM, including DynamoDB Streams integration.

## Overview

The application consists of:
- A DynamoDB table (`SearchableItem`) with streams enabled
- An OpenSearch Serverless collection for full-text search
- Lambda functions for indexing and searching
- A Lambda function (`streamprocessor`) that processes DynamoDB Stream events

## Components

### 1. DynamoDB Table: SearchableItem
- Configured with DynamoDB Streams enabled
- Stream view type is set to `NEW_AND_OLD_IMAGES` to capture both old and new item states
- Stores searchable items with an `ItemID` as the primary key

### 2. OpenSearch Serverless Collection: searchable
- Provides full-text search capabilities
- Indexed by the `indexfunc` Lambda function

### 3. Lambda Functions

#### indexfunc
- **Multi-purpose function with DynamoDB Streams integration**
- Can be invoked manually to index items into the OpenSearch collection
- **Automatically triggered by DynamoDB Streams** when items in SearchableItem table change
- Processes INSERT events: Indexes new items into OpenSearch
- Processes MODIFY events: Updates existing items in OpenSearch
- Processes REMOVE events: Removes deleted items from OpenSearch
- Processes events in batches of up to 10 records
- Maintains synchronization between DynamoDB and OpenSearch automatically

#### searchfunc
- Performs searches against the OpenSearch collection
- Has access to the SearchableItem table and searchable collection

## DynamoDB Streams Configuration

In `backend/database/easysam.yaml`:
```yaml
tables:
  SearchableItem:
    attributes:
    - hash: true
      name: ItemID
    trigger: indexfunc  # Lambda function to trigger on table changes
```

That's it! The simple `trigger: indexfunc` configuration:
- Enables DynamoDB Streams on the table automatically
- Triggers the `indexfunc` Lambda when items are created, modified, or deleted
- Uses sensible defaults (view type: `new-and-old`, starting position: `latest`)

For advanced configuration, you can use the expanded form:
```yaml
trigger:
  function: indexfunc
  viewtype: new-and-old  # Optional, default
  batchsize: 10          # Optional
  startingposition: latest  # Optional, default
```

## Stream View Types

- `keys-only`: Only the key attributes of the modified item
- `new`: The entire item, as it appears after modification
- `old`: The entire item, as it appeared before modification
- `new-and-old`: Both the new and old item images (default, used in this example)

## Testing DynamoDB Streams

### Automated Testing with the Test Script

Use the included test script to trigger DynamoDB Stream events:

```bash
# Run both stream and search tests
python test/invoke_lambda.py --env <your-env-name>

# Only test DynamoDB Streams
python test/invoke_lambda.py --env <your-env-name> --test-stream --no-test-search

# Only test search function
python test/invoke_lambda.py --env <your-env-name> --no-test-stream --test-search
```

The script will:
1. Insert a test item → triggers INSERT event → indexfunc indexes to OpenSearch
2. Update the item → triggers MODIFY event → indexfunc updates in OpenSearch
3. Delete the item → triggers REMOVE event → indexfunc removes from OpenSearch
4. Optionally invoke searchfunc to query the index

Check CloudWatch Logs for `indexfunc` to see the stream processing in action!

### Manual Testing

You can also manually test by:
1. Deploy the application
2. Insert, modify, or delete items in the SearchableItem DynamoDB table using the AWS Console or CLI
3. Check CloudWatch Logs for the `indexfunc` Lambda function to see the processed events
4. Query the OpenSearch collection to verify items are automatically synchronized

## Deployment

```bash
easysam deploy example/aoss --environment dev --tag purpose=testing
```

## Use Cases

The DynamoDB Streams integration in this example demonstrates:

1. **Automatic Search Index Synchronization**: Keep OpenSearch in sync with DynamoDB without manual intervention
2. **Event-driven Architecture**: React to data changes in real-time
3. **Single Lambda Multi-purpose**: One function handles both manual indexing and automatic stream processing
4. **Batch Processing**: Efficiently process multiple changes in a single invocation
5. **Data Consistency**: Ensure search results always reflect the current state of the database

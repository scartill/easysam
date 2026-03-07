# Amazon OpenSearch Serverless (AOSS) Example

This example demonstrates automatic indexing from DynamoDB streams into OpenSearch Serverless.

## What this example demonstrates

- DynamoDB table with `trigger: indexfunc`
- Stream-driven indexing (`INSERT`, `MODIFY`, `REMOVE`)
- Separate search lambda (`searchfunc`) querying the collection

## Architecture

- `SearchableItem` DynamoDB table
- `searchable` OpenSearch Serverless collection
- `indexfunc` lambda for stream processing
- `searchfunc` lambda for search query execution

## Source configuration

`backend/database/easysam.yaml`:

```yaml
tables:
  SearchableItem:
    attributes:
      - hash: true
        name: ItemID
    trigger: indexfunc
```

The simple `trigger: indexfunc` form enables stream processing with defaults:

- `viewtype: new-and-old`
- `startingposition: latest`

Advanced form is also supported:

```yaml
trigger:
  function: indexfunc
  viewtype: new-and-old
  batchsize: 10
  batchwindow: 5
  startingposition: latest
```

## Generate and inspect

```bash
easysam --environment dev inspect schema example/aoss
easysam --environment dev generate example/aoss
```

Generated resources include:

- DynamoDB table + stream
- OpenSearch Serverless policies + collection
- Lambda functions for indexing and search
- Event source mapping from table stream to `indexfunc`

## Deploy

```bash
easysam --environment dev --aws-profile my-profile deploy example/aoss --tag purpose=testing
```

## Test

From `example/aoss`:

```bash
python3 test/invoke_lambda.py --env dev --aws-profile my-profile
```

Selective test modes:

```bash
python3 test/invoke_lambda.py --env dev --aws-profile my-profile --test-stream --no-test-search
python3 test/invoke_lambda.py --env dev --aws-profile my-profile --no-test-stream --test-search
```

The script performs:

1. Insert item -> stream `INSERT` -> index in AOSS
2. Update item -> stream `MODIFY` -> update in AOSS
3. Delete item -> stream `REMOVE` -> delete from AOSS
4. Optional `searchfunc` invocation

## Verify in CloudWatch

- `indexfunc-dev` logs should show processed stream events.
- `searchfunc-dev` logs should show search invocation result.

## Cleanup

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

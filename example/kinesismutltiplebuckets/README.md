# Kinesis Multiple Buckets Example

This example demonstrates Kinesis stream delivery into multiple S3 destinations (internal and external).

## What this example demonstrates

- Kinesis stream definitions with Firehose delivery configuration
- Simple single-bucket destination (`simple`)
- Multi-destination stream (`complex`) with conditional external bucket ARN
- Deploy-context overrides for environment-specific values

## Source highlights

`resources.yaml`:

- `streams.simple` uses `bucketname: private`
- `streams.complex.buckets.private` targets internal bucket
- `streams.complex.buckets.external` uses conditional `extbucketarn`

Override file:

- `deploy-context.yaml`

## Validate and generate

```bash
easysam --environment kinesissampledev --context-file example/kinesismutltiplebuckets/deploy-context.yaml inspect schema example/kinesismutltiplebuckets
easysam --environment kinesissampledev --context-file example/kinesismutltiplebuckets/deploy-context.yaml generate example/kinesismutltiplebuckets
```

## Deploy

```bash
easysam --environment kinesissampledev --aws-profile my-profile --context-file example/kinesismutltiplebuckets/deploy-context.yaml deploy example/kinesismutltiplebuckets
```

## Send test event

From `example/kinesismutltiplebuckets`:

```bash
python3 test/send_message.py --env kinesissampledev
```

This invokes `myfunction-<env>`, which writes records to both streams.

## Cleanup

```bash
easysam --environment kinesissampledev --aws-profile my-profile delete --await
```

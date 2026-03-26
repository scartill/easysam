# Scheduled Lambda Example

This example demonstrates setting a schedule for a Lambda function using `easysam.yaml`.

## What this example demonstrates

`backend/function/local-lambda/easysam.yaml`:

```yaml
lambda:
  name: locallambda
  schedule: rate(1 hour)
```

The Lambda function is triggered according to the configured schedule.

## Validate and generate

```bash
easysam --environment dev inspect schema example/schedule
easysam --environment dev generate example/schedule
```

## Deploy

```bash
easysam --environment dev --aws-profile my-profile deploy example/schedule
```

## Verify

The Lambda function `locallambda-dev` will be triggered based on the configured schedule. You can verify it by checking the CloudWatch logs:

```bash
aws logs tail /aws/lambda/locallambda-dev --profile my-profile
```

## Cleanup

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

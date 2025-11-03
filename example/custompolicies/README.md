# Custom Policies Example

This example demonstrates the use of `custompolicies` for lambdas, queues, and buckets.

## Features Demonstrated

### 1. Lambda Custom Policies
The `myfunction` lambda has custom IAM policies that grant:
- `logs:CreateLogGroup` on any log group ARN
- `logs:CreateLogStream` and `logs:PutLogEvents` on any resource (`*`)

These are identity-based policies attached to the Lambda execution role, so they don't include a `Principal` field.

### 2. Queue Custom Policies
The `notifications` queue has custom SQS queue policies that:
- Allow account `123456789012` to send messages
- Allow any principal (`*`) to receive and delete messages

Queue policies are resource-based and always include a `Principal` field (defaults to `*` if not specified).

### 3. Bucket Custom Policies
The `documents` bucket has custom S3 bucket policies that:
- Allow account `123456789012` to get objects
- Allow account `987654321098` to put and delete objects

Bucket policies are resource-based and always include a `Principal` field (defaults to `*` if not specified).

## File Structure

```
custompolicies/
??? resources.yaml              # Main resources file with bucket and queue custom policies
??? backend/
?   ??? function/
?       ??? myfunction/
?           ??? easysam.yaml    # Lambda definition with custom policies
?           ??? index.py        # Lambda function code
??? common/
    ??? utils.py                # Common utilities
```

## Key Points

- **Lambda policies**: Identity-based, no `Principal` field, `resource` can be `"any"` (translates to `"*"`)
- **Queue policies**: Resource-based, always require `Principal` (defaults to `"*"`), `resource` is always the queue ARN
- **Bucket policies**: Resource-based, always require `Principal` (defaults to `"*"`), `resource` is always the bucket ARN

## Deployment

```bash
easysam deploy custompolicies --environment dev --tag Environment=dev
```

Note: Update the principal ARNs in `resources.yaml` to match your AWS account IDs.

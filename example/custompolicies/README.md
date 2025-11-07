# Custom Policies Example

This example demonstrates the use of `custompolicies` for lambdas.

## Features Demonstrated

### Lambda Custom Policies
The `myfunction` lambda has custom IAM policies that grant:
- `logs:CreateLogGroup` on any log group ARN
- `logs:CreateLogStream` and `logs:PutLogEvents` on any resource (`*`)

These are identity-based policies attached to the Lambda execution role, so they don't include a `Principal` field.

> Bucket and queue custom policies have been removed from `easysam`. Use separate CloudFormation resources or IAM roles if you need resource-based policies for those services.

## File Structure

```
custompolicies/
??? resources.yaml              # Main resources file importing the lambda example
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
- **Buckets/queues**: Resource-based custom policies are no longer managed by `easysam`

## Deployment

```bash
easysam deploy custompolicies --environment dev --tag Environment=dev
```

Note: Update the principal ARNs in `resources.yaml` to match your AWS account IDs.

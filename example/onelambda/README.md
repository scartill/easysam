# One Lambda Example

This is the smallest deployable EasySAM app: a single lambda without tables, queues, or API routes.

## What this example demonstrates

- Minimal local lambda declaration:

```yaml
lambda:
  name: myfunction
```

- Basic function packaging and invocation path
- Global tags in root `resources.yaml`

## Validate and generate

```bash
easysam --environment dev inspect schema example/onelambda
easysam --environment dev generate example/onelambda
```

## Deploy

```bash
easysam --environment dev --aws-profile my-profile deploy example/onelambda
```

## Invoke test script

From `example/onelambda`:

```bash
python3 test/invoke_lambda.py --env dev
```

## Cleanup

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

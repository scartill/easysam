# Conditional Resources Example

This example shows how to include or exclude resource definitions based on deployment context.

## What this example demonstrates

- `!Conditional` keys in `resources.yaml`
- Environment and region checks
- Negation using `~`
- Override patches via context file

## Source highlights

`resources.yaml` contains conditional bucket variants:

- `environment: prod`
- `region: eu-west-2`
- `environment: ~prod` and `region: ~eu-west-2`

## Validate with context

The example includes `deploy-context.yaml`.

```bash
easysam --environment prod --target-region eu-west-2 --context-file example/conditionals/deploy-context.yaml inspect schema example/conditionals
```

Try different combinations of `--environment` and `--target-region` to see different resolved outputs.

## Generate

```bash
easysam --environment prod --target-region eu-west-2 --context-file example/conditionals/deploy-context.yaml generate example/conditionals
```

## Deploy

```bash
easysam --environment prod --target-region eu-west-2 --aws-profile my-profile --context-file example/conditionals/deploy-context.yaml deploy example/conditionals
```

## Cleanup

```bash
easysam --environment prod --aws-profile my-profile delete --await
```

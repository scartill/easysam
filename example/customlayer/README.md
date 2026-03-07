# Custom Layer Example

This example demonstrates attaching an external Lambda layer ARN via EasySAM.

## What this example demonstrates

- Function-level `layers` configuration in local `easysam.yaml`
- Dynamic SSM reference for layer ARN

`backend/function/myfunction/easysam.yaml`:

```yaml
lambda:
  name: myfunction
  resources:
    layers:
      mycustomlayer: '{{resolve:ssm:/ffmpeg-latest-arn}}'
```

## Prerequisite

The SSM parameter `/ffmpeg-latest-arn` must exist in the target account/region and contain a valid Lambda layer ARN.

## Validate and generate

```bash
easysam --environment dev inspect schema example/customlayer
easysam --environment dev generate example/customlayer
```

## Deploy

```bash
easysam --environment dev --aws-profile my-profile deploy example/customlayer
```

## Invoke test script

From `example/customlayer`:

```bash
python3 test/invoke_lambda.py --env dev
```

## Cleanup

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

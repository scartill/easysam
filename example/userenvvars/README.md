# Global Env Vars Example

This example demonstrates defining global Lambda environment variables in `resources.yaml`.

## What this example demonstrates

`resources.yaml`:

```yaml
envvars:
  MY_ENV_VAR: myvalue
```

Every generated Lambda gets the configured variable(s).

## Validate and generate

```bash
easysam --environment dev inspect schema example/userenvvars
easysam --environment dev generate example/userenvvars
```

## Deploy

```bash
easysam --environment dev --aws-profile my-profile deploy example/userenvvars
```

## Invoke test script

From `example/userenvvars`:

```bash
python3 test/invoke_lambda.py --env dev
```

Expected output body includes:

```json
{"envvar": "myvalue"}
```

## Cleanup

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

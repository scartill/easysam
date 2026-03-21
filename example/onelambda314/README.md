# Python 3.14 Lambda Example

This example demonstrates how to specify a custom Python runtime version and configure advanced Lambda properties.

## What this example demonstrates

- **Custom Python Runtime:** Setting the global Python version in `resources.yaml`.
- **Lambda Configuration:** Overriding default `timeout` and `memory` settings in the local `easysam.yaml`.

## Source configuration

`resources.yaml`:

```yaml
prefix: Onelambda
python: "3.14"
import:
  - backend
```

`backend/function/myfunction/easysam.yaml`:

```yaml
lambda:
  name: myfunction
  timeout: 60
  memory: 1024
```

## Validate and generate

```bash
easysam --environment dev inspect schema example/onelambda314
easysam --environment dev generate example/onelambda314
```

In the generated `template.yml`, verify that `Runtime: python3.14` is set for the function, along with the specified `Timeout` and `MemorySize`.

## Deploy

```bash
easysam --environment dev --aws-profile my-profile deploy example/onelambda314
```

## Cleanup

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

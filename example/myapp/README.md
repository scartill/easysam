# MyApp Example

This is the baseline EasySAM application pattern: imported backend resources with one API lambda and one DynamoDB table.

## What this example demonstrates

- Root `resources.yaml` with `import: [backend]`
- Local table definition in `backend/database/easysam.yaml`
- Local lambda definition and API path in `backend/function/myfunction/easysam.yaml`
- Shared helper module under `common/`

## Key files

- `resources.yaml`
- `backend/database/easysam.yaml`
- `backend/function/myfunction/easysam.yaml`
- `backend/function/myfunction/index.py`
- `common/utils.py`

## Validate and generate

```bash
easysam --environment dev inspect schema example/myapp
easysam --environment dev generate example/myapp
```

## Deploy

```bash
easysam --environment dev --aws-profile my-profile deploy example/myapp
```

## Verify

Invoke the lambda directly or call the generated API endpoint for `/items`.

## Cleanup

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

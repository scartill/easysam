# App With Errors Example

This example intentionally contains invalid configuration to demonstrate EasySAM validation behavior.

## What this example demonstrates

- How schema/load errors are reported
- Why `inspect schema` should be run before deployment

## Intentional problem

`backend/database/easysam.yaml` is malformed on purpose.

Use this example to see diagnostics, not to deploy.

## Run validation

```bash
easysam --environment dev inspect schema example/appwitherrors
```

Expected result: one or more validation/load errors.

## Why keep this example

- Useful for CI guardrail demonstrations
- Useful for onboarding users to error message format

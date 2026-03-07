# EasySAM Production Hardening Guide

This guide covers practical checks before promoting an EasySAM application to production.

## 1) IAM and access control

- Avoid broad `open: true` API paths in production unless intentional.
- Prefer Lambda authorizers (`authorizers`) for protected endpoints.
- Keep function-level resource lists explicit (`tables`, `buckets`, `queues`, `streams`).
- Review generated policies for `services` and `searches`:
  - `bedrock` grants model invocation
  - `mqtt` grants IoT publish/endpoint access
  - `searches` grants AOSS access for configured collections

Checklist:

- [ ] No unnecessary admin-like permissions
- [ ] Public API routes are intentionally public
- [ ] Authorizer functions are monitored and versioned

## 2) API security and CORS

By default, generated API CORS is permissive (`*`). For internet-facing APIs:

- Restrict origins, headers, and methods where possible.
- Use custom templates or downstream controls if you need stricter CORS than defaults.
- Ensure protected paths use `authorizer`, not `open`.

Checklist:

- [ ] CORS settings align with frontend domains
- [ ] Sensitive routes require authorization

## 3) Data protection

### DynamoDB

- Enable TTL only for data that should expire.
- Use stream triggers intentionally; stream consumers should be idempotent.
- Validate key schema and GSIs for expected query patterns.

### S3

- Set `public: true` only when needed.
- Prefer private buckets and explicit access patterns.

### OpenSearch Serverless

- Review collection network/data policies generated for your use case.
- Limit function access to only required collections.

Checklist:

- [ ] Buckets are private by default
- [ ] TTL and stream behavior are documented
- [ ] Search collections are scoped to expected principals

## 4) Secrets and configuration

- Keep secrets in AWS Secrets Manager / SSM Parameter Store.
- Do not hardcode credentials in `resources.yaml`, handlers, or tests.
- Use `--aws-profile` in local workflows instead of embedding profile names in code.

Checklist:

- [ ] No plaintext secrets in repo
- [ ] Runtime config comes from environment/SSM/secrets

## 5) Deploy safety in CI/CD

Recommended CI stages:

1. `inspect schema` (structural validation)
2. `inspect cloud` (dependency/environment readiness)
3. `generate` (template rendering)
4. `deploy --dry-run` for preview (optional)
5. `deploy`

Suggested commands:

```bash
easysam --environment prod --context-file deploy-context.yaml inspect schema .
easysam --environment prod --context-file deploy-context.yaml inspect cloud .
easysam --environment prod --context-file deploy-context.yaml generate .
easysam --environment prod --context-file deploy-context.yaml deploy .
```

Checklist:

- [ ] Context file is versioned and reviewed
- [ ] Deploys are environment-specific (`--environment`)
- [ ] Rollback and delete procedures are documented

## 6) Observability and operations

- Add structured logging in Lambda handlers.
- Monitor Lambda errors, throttles, and duration.
- Track DynamoDB stream failures and retries.
- Track API Gateway 4xx/5xx and latency metrics.
- For AOSS flows, monitor indexing/search errors and data drift.

Checklist:

- [ ] Critical alarms configured
- [ ] Dashboards available for API, Lambda, and data paths
- [ ] Runbooks exist for common failures

## 7) Cost controls

- Validate stream volume assumptions (Kinesis + Firehose + S3).
- Use TTL to reduce long-lived DynamoDB storage.
- Scope OpenSearch collections to actual demand.
- Clean up non-prod stacks regularly (`delete`).

Checklist:

- [ ] Budget alarms enabled
- [ ] Environment lifecycle policy in place
- [ ] Example/test stacks are removed after validation

## 8) Release readiness checklist

- [ ] `README.md` updated and accurate
- [ ] Example README for each maintained example
- [ ] CLI and resource references published
- [ ] CI validates schema/cloud before deploy
- [ ] No organization-specific profile names or credentials in source

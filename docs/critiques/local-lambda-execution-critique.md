# Critique: Local Lambda Execution Mode

**Target Document:** `docs/specs/local-lambda-execution.md`  
**Date:** 2026-08-03  
**Reviewers:** Product Lens (CEO/Product Lead) & Engineering Lens (Staff Engineer)

---

## Executive Summary

The proposed `Local Lambda Execution Mode` specification addresses a critical developer experience pain point in EasySAM: allowing developers to test HTTP API routes and non-HTTP Lambda functions locally without deploying to AWS. The overall architecture (FastAPI + uvicorn serving API Gateway v2 synthesized events and isolated handler imports) is well-conceived and aligns with EasySAM's lightweight, non-Docker philosophy.

However, the critique identified key technical risks and usability gaps prior to implementation:
1. **Thread-Safety Hazard**: Mutating `os.environ` per request in a concurrent FastAPI server causes environment variable race conditions between handlers.
2. **Execution Support**: Missing support for `async def handler(event, context)` functions, which will cause runtime coroutine failures.
3. **Response Parity**: Incomplete handling of API Gateway v2 response payloads (missing `statusCode` auto-wrapping and base64 binary responses).
4. **Module Cache Strategy**: Unselective `sys.modules` purging can break third-party package caching (e.g., `boto3`) while failing to reload modified `common/` utilities.

**Verdict:** ⚠️ **PROCEED WITH UPDATES** — The spec is structurally solid, but the 3 Must-Address items and 4 Recommendations should be integrated before implementation.

---

## Findings Summary Table

| ID | Lens | Severity | Category | Finding | Suggestion |
|---|---|---|---|---|---|
| **E1** | Engineering | 🎯 Must-Address | Thread Safety | Mutating `os.environ` per request creates race conditions under concurrent requests | Enforce single-request execution lock (`asyncio.Lock()`) around envvar setting and invocation |
| **E2** | Engineering | 🎯 Must-Address | Execution Support | `handler(event, context)` does not handle `async def` handlers | Inspect `iscoroutinefunction(handler)` and await coroutines properly |
| **P1** | Product | 🎯 Must-Address | AWS Parity | API Gateway v2 response format not auto-wrapped if handler returns simple dict/primitive | Normalize handler return dict; default `statusCode: 200` and JSON-encode body if missing |
| **E3** | Engineering | 💡 Recommendation | Architecture | `sys.modules` cleanup deletes third-party packages but fails to reload `common/` edits | Selectively invalidate only local project path modules (`lambda_dir` & `project_root`) |
| **E4** | Engineering | 💡 Recommendation | Routing | Route registration order between exact and greedy routes could cause shadowing | Sort routes by specificity (exact first, greedy last) before FastAPI registration |
| **P2** | Product | 💡 Recommendation | Usability | `local invoke` requires JSON file path for `--event` | Allow inline JSON strings and default to `{}` if `--event` is omitted |
| **P3** | Product | 💡 Recommendation | Observability | Missing structured local request/invocation logs and execution timing | Log `[METHOD] /path -> function (statusCode, duration_ms)` and print readable tracebacks on 500 |
| **Q1** | Both | 🤔 Question | Policy | Function timeouts specified in `resources.yaml` are ignored locally | Decide whether to enforce local timeout (e.g., via `asyncio.wait_for`) or allow infinite execution for debugging |

---

## Verdict: ⚠️ PROCEED WITH UPDATES

All Must-Address and Recommendation items have been incorporated into the spec.

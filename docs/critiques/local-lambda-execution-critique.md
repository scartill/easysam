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

## Product Lens Findings

### 1a. Problem Validation & Scope
- **Finding:** The core capability (local HTTP server + `local invoke`) solves a real developer pain point: high latency during dev cycles.
- **CLI Alignment:** The spec proposes `easysam local . --port 3000`. In existing EasySAM CLI structure (`cli.py`), global options like `--environment` precede subcommands, and target directory arguments follow standard Click patterns.
- **Suggestion:** Standardize CLI syntax to `easysam --environment dev local [DIRECTORY] --port 3000`, defaulting `DIRECTORY` to `.` if omitted.

### 1b. User Experience & DX
- **Finding (P1 / 🎯 Must-Address): API Gateway v2 Response Auto-Formatting**  
  AWS API Gateway HTTP API v2 allows handlers to return simple dicts or primitive values without explicit `statusCode` keys (e.g. returning `{"message": "success"}` or a string). The spec assumes handlers always return `{"statusCode": 200, "body": ...}`.
- **Suggestion:** Implement API Gateway v2 response normalization in `local_server.py`. If the handler output is a dict lacking `statusCode`, default to `statusCode: 200` and serialize the dict to JSON body.

- **Finding (P2 / 💡 Recommendation): Flexible `local invoke` Event Inputs**  
  Task 7 specifies `easysam local invoke <function> --event file.json`. Requiring a file path for quick ad-hoc testing creates friction.
- **Suggestion:** Allow `--event` to accept either a JSON file path, inline JSON string (e.g. `'{"key":"value"}'`), or default to `{}` if omitted.

- **Finding (P3 / 💡 Recommendation): Developer Observability & Execution Duration**  
  Local execution should give developers immediate visibility into invocation status, execution duration in milliseconds, and clear error stack traces on handler failures.
- **Suggestion:** Add structured log lines per request in `local_server.py` showing `[HTTP METHOD] /path -> FunctionName (200 OK, 14ms)`.

### 1c. Success Measurement & Edge Cases
- **Finding:** Handling binary payload responses (e.g. images, PDFs) from Lambda handlers returning `isBase64Encoded: True` is not detailed in the spec.
- **Suggestion:** Add explicit response translation rules in `local_server.py` for decoding base64 bodies when `isBase64Encoded` is `True`.

---

## Engineering Lens Findings

### 2a. Architecture & Thread Safety

- **Finding (E1 / 🎯 Must-Address): Race Condition in Global `os.environ` Mutation**  
  Task 5 steps (1) set per-function envvars, (2) run handler, (3) restore envvars in global `os.environ`. In FastAPI/uvicorn, concurrent incoming HTTP requests execute in parallel tasks/threads. Mutating `os.environ` globally per request introduces severe race conditions where Request A's environment variables leak into Request B.
- **Suggestion:** Execute handler invocations synchronously under an async thread lock (or execute single-worker), OR pass environment variables directly into a process executor / thread-local environment context. For v1, wrapping per-request handler invocation and envvar setting in an `asyncio.Lock()` ensures thread-safe environment isolation.

- **Finding (E2 / 🎯 Must-Address): Lack of `async def handler` Support**  
  In `local_handler.py`, calling `handler(event, context)` assumes `handler` is a synchronous function. If a Lambda function defines `async def handler(event, context)`, `load_and_invoke` will return an un-awaited coroutine object instead of executing the handler, leading to response serialization crashes.
- **Suggestion:** Check `inspect.iscoroutinefunction(handler)` in `local_handler.py`. If true, `await` the coroutine (or run it via `asyncio.run()` / current event loop).

- **Finding (E3 / 💡 Recommendation): `sys.modules` Purge Strategy Improvements**  
  The proposed `isolated_import_context` deletes *all* newly added keys from `sys.modules` after invocation. This causes heavy dependencies (e.g. `boto3`, `botocore`, `pydantic`) to be re-imported from scratch on every request, degrading performance. Conversely, modules imported before the server started (like `common.utils`) will *never* be purged or reloaded, breaking hot-reload expectations when `common/` files are edited.
- **Suggestion:** Refine `isolated_import_context` to selectively purge or reload only modules originating from the local project root (`lambda_dir` and `project_root`), while preserving external library module caching in `sys.modules`.

- **Finding (E4 / 💡 Recommendation): FastAPI Route Shadowing for Greedy Routes**  
  Task 4 registers both exact paths (`/items`) and greedy catch-all paths (`/items/{path:path}`). In Starlette/FastAPI, if routes are registered in the wrong order or if greedy routes capture exact sub-paths, request routing can fail or misroute.
- **Suggestion:** Explicitly enforce route sorting in `local_routes.py` so specific routes and non-greedy paths are registered before catch-all / greedy routes. Additionally, map `{path:path}` correctly to API Gateway v2 `pathParameters` (e.g. mapping parameter name to `"proxy"` or `"path"` as configured in resource definitions).

---

## Cross-Lens Insights

- **Convergence C1 (Environment Isolation & System Stability)**: Fixing the `os.environ` race condition (E1) guarantees both product reliability (predictable function execution) and technical correctness (no cross-request memory leakage).
- **Convergence C2 (Developer Experience & Hot Reloading)**: Targeted module purging (E3) speeds up execution by retaining `boto3`/library caches while ensuring edits to local `index.py` and `common/` take effect immediately without restarting the server.
- **Convergence C3 (AWS Parity & Robustness)**: Async handler support (E2) and API Gateway v2 auto-formatting (P1) ensure that local handler behavior matches AWS cloud execution without surprise failures upon deployment.

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

## Verdict

### ⚠️ **PROCEED WITH UPDATES**

The specification is well-architected and ready for implementation once the 3 **Must-Address** items (**E1**, **E2**, **P1**) and key recommendations are incorporated into the specification tasks.

---

## Offered Remediation & Proposed Spec Edits

Below are specific proposed updates to apply to `docs/specs/local-lambda-execution.md`:

### 1. Update Requirements Section in Spec
Add the following explicit requirements:
- **Req 12:** Async Lambda handlers (`async def handler`) must be detected and awaited correctly.
- **Req 13:** Environment variable application per request must be synchronized via an `asyncio.Lock()` to prevent concurrent `os.environ` mutations.
- **Req 14:** API Gateway v2 response normalization must handle simple dict returns (default `statusCode: 200`), base64 decoding for `isBase64Encoded: True`, and 500 status code with formatted tracebacks on uncaught exceptions.
- **Req 15:** Selective module cleanup: invalidate local module paths (`project_root` and `lambda_dir`) without purging third-party dependencies from `sys.modules`.

### 2. Update Task 2 (`src/easysam/local_handler.py`)
- Update `load_and_invoke` implementation guidance to support async coroutines (`inspect.iscoroutinefunction`) and use selective module invalidation.

### 3. Update Task 5 (`src/easysam/local_server.py`)
- Add `asyncio.Lock()` around handler execution and environment variable setting.
- Add API Gateway v2 response translation with `statusCode` default, base64 decoding, and execution duration logging.

### 4. Update Task 7 (`src/easysam/local_cli.py` - `local invoke`)
- Support inline JSON string parsing for `--event` (fallback from file checking) and default empty dict `{}` if `--event` is omitted.

---

*Would you like me to apply these updates to `docs/specs/local-lambda-execution.md`? (all / select / none)*

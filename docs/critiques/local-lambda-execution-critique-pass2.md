# Critique (Pass 2): Local Lambda Execution Mode

**Target Document:** `docs/specs/local-lambda-execution.md`  
**Date:** 2026-08-03  
**Reviewers:** Product Lens (CEO/Product Lead) & Engineering Lens (Staff Engineer)

---

## Executive Summary (2nd Pass)

The updated specification (`docs/specs/local-lambda-execution.md`) incorporates significant improvements from the first critique pass:
- Added `--event-format v1|v2` option (defaulting to `v1` REST API payload format matching EasySAM's CloudFormation/SAM template generation).
- Added `--auth-context` injection for local authorization stubbing.
- Added `async def handler` support (`inspect.iscoroutinefunction`).
- Introduced `asyncio.Lock()` for thread-safe environment variable handling.
- Added selective module invalidation and route specificity sorting.

This second-pass critique evaluates the updated specification to ensure there are no remaining execution edge cases or architectural flaws.

**Verdict:** ⚠️ **PROCEED WITH UPDATES** — The spec is nearly ready for implementation. Two targeted engineering items (**E1_2**, **E2_2**) and three minor recommendations should be addressed.

---

## Product Lens Findings (2nd Pass)

### 1a. Specification Consistency & Architecture Diagram
- **Finding (P1_2 / 💡 Recommendation): Outdated Diagram & Task Text References**  
  While Requirement 2 and Task 3 were updated to support both `v1` and `v2` event formats, the Mermaid architecture diagram (line 78: `H[Build v2 Event]`) and Task 5 step 3 ("Build v2 event from request") still reference v2 specifically.
- **Suggestion:** Update the architecture diagram box to `H[Build Synthesized Event (v1/v2)]` and Task 5 text to reference `--event-format` dispatching.

### 1b. CLI Usability & Response Formatting
- **Finding (P2_2 / 💡 Recommendation): Safe JSON Output in `local invoke`**  
  Task 7 states `local invoke` will "print response JSON to stdout". If a Lambda function returns a non-standard JSON payload (e.g. `datetime` objects, `Decimal` types, or `None`), standard `json.dumps()` will raise a `TypeError`.
- **Suggestion:** Specify using `json.dumps(response, indent=2, default=str)` in `local_cli.py` to ensure robust terminal output without crashes.

---

## Engineering Lens Findings (2nd Pass)

### 2a. Module Invalidation & Local Hot Reloading

- **Finding (E1_2 / 🎯 Must-Address): Local Module Purge Bug in `isolated_import_context`**  
  In the proposed code sketch for `isolated_import_context`:
  ```python
  new_modules = set(sys.modules.keys()) - original_modules
  ```
  If `common.utils` (or any shared local module under `project_root`) was imported during server startup or during request 1, it exists in `original_modules`. On request 2, when `common.utils` is modified on disk, `new_modules` will **not** contain `common.utils`. Thus, `isolated_import_context` will skip purging it, and changes to `common/` files will not take effect on subsequent requests.
- **Suggestion:** Instead of purging only `new_modules`, scan `sys.modules` for any module whose `__file__` is inside `project_root` or `lambda_dir` and delete it (or force re-import) on every request context exit, ensuring true local hot-reloading for source files while retaining third-party packages.

### 2b. Exception Safety & Environment Cleanup

- **Finding (E2_2 / 🎯 Must-Address): Unhandled Exception Hazard in `_invocation_lock` and `os.environ`**  
  In Task 5, steps 1–6 outline: (1) acquire lock, (2) set per-function envvars, (3) build event, (4) invoke handler, (5) restore envvars, (6) release lock. If `load_and_invoke` or event building raises an unhandled exception, steps 5 and 6 will be bypassed, leaving the `_invocation_lock` permanently locked (deadlocking the local server) and `os.environ` mutated.
- **Suggestion:** Wrap steps 2–6 in a mandatory `try...finally` block inside an `async with _invocation_lock:` context manager to guarantee `os.environ` restoration and lock release under all failure conditions.

### 2c. Multi-Value Query String Parsing (REST API v1)

- **Finding (E3_2 / 💡 Recommendation): Query Parameter List Construction for REST API v1**  
  For REST API (v1) events, `multiValueQueryStringParameters` expects lists of strings for repeated keys (e.g. `?tag=a&tag=b` -> `{"tag": ["a", "b"]}`). Converting `dict(request.query_params)` directly truncates repeated query parameters to single values.
- **Suggestion:** In `local_event.py` (`build_rest_api_event`), parse query parameters using `request.query_params.multi_items()` to properly construct `multiValueQueryStringParameters`.

---

## Findings Summary Table (Pass 2)

| ID | Lens | Severity | Category | Finding | Suggestion |
|---|---|---|---|---|---|
| **E1_2** | Engineering | 🎯 Must-Address | Hot Reloading | `isolated_import_context` skips purging local modules loaded prior to invocation context | Purge all `sys.modules` matching `project_root` / `lambda_dir` regardless of `original_modules` |
| **E2_2** | Engineering | 🎯 Must-Address | Robustness | `_invocation_lock` and `os.environ` restoration are not in a `try...finally` block | Wrap envvar mutation and handler invocation in `async with lock:` + `try...finally` |
| **P1_2** | Product | 💡 Recommendation | Documentation | Architecture diagram and Task 5 step 3 hardcode "v2 event" | Update diagram to "Build Synthesized Event (v1/v2)" and align task description |
| **P2_2** | Product | 💡 Recommendation | Usability | `local invoke` standard `json.dumps()` crashes on non-serializable return types | Use `json.dumps(result, indent=2, default=str)` |
| **E3_2** | Engineering | 💡 Recommendation | AWS Parity | `dict(request.query_params)` drops duplicate query string keys in REST API v1 events | Use `request.query_params.multi_items()` to construct `multiValueQueryStringParameters` |

---

## Verdict (Pass 2)

### ⚠️ **PROCEED WITH UPDATES**

The specification is in excellent shape. Applying the fix for **E1_2** (local module purge) and **E2_2** (exception-safe lock/envvar cleanup) will complete the specification and make it fully ready for implementation.

---

## Offered Remediation

Would you like me to apply these final 2nd-pass updates directly to [`docs/specs/local-lambda-execution.md`](file:///C:/Users/boris/projects/var/easysam/docs/specs/local-lambda-execution.md)?  
**(all / select / none)**

# Code Review (Pass 2): `local-mode`

- **Date**: 2026-08-04
- **Author**: scartill (Boris Resnick)
- **Branch**: `local-mode` → `main`
- **PR**: [#30](https://github.com/scartill/easysam/pull/30)
- **Files Changed**: 43 (3,501 additions, 443 deletions)
- **Decision**: **APPROVE**

---

## 1. Executive Summary

This second pass code review re-evaluates the implementation of **Local Gateway & Execution Mode** (`easysam local .` and `easysam local invoke`) following the resolution of findings from Pass 1.

All **4 functional and performance defects** identified in Pass 1 (path parameter corruption on non-greedy routes, Windows `OSError` on inline JSON parsing, cross-platform path resolution during module cleanup, and request body lock contention) have been cleanly resolved. Lint issues were reduced from 19 to 0, and all 74 unit/integration test cases pass without errors.

---

## 2. Pass 1 Feedback Verification

| Item | Issue | Severity | Status | Verification |
|---|---|---|---|---|
| 1 | `path_params.pop('path')` corrupted `{path}` params on non-greedy routes | **HIGH** | **FIXED** | [local_server.py:L134-L136](file:///C:/Users/boris/projects/var/easysam/src/easysam/local_server.py#L134-L136) now checks `if route.is_greedy and 'path' in path_params:`. |
| 2 | `Path(value).exists()` raised unhandled `OSError` on Windows for inline JSON strings | **HIGH** | **FIXED** | [local_cli.py:L38-L39](file:///C:/Users/boris/projects/var/easysam/src/easysam/local_cli.py#L38-L39) traps `(OSError, ValueError)` during file path checking. |
| 3 | Incomplete module cleanup on Windows due to un-resolved `__file__` paths | **MEDIUM** | **FIXED** | [local_handler.py:L43-L79](file:///C:/Users/boris/projects/var/easysam/src/easysam/local_handler.py#L43-L79) uses `Path(...).resolve()` for robust prefix comparison. |
| 4 | `request.body()` read blocked global `_invocation_lock` | **MEDIUM** | **FIXED** | [local_server.py:L138-L140](file:///C:/Users/boris/projects/var/easysam/src/easysam/local_server.py#L138-L140) reads request body and builds event *before* entering `_invocation_lock`. |
| 5 | 19 lint errors flagged by `ruff` | **LOW** | **FIXED** | `uv run ruff check` outputs 0 issues (`All checks passed!`). |

---

## 3. Architectural & Design Overview

The local Lambda execution subsystem is built with a modular, lightweight architecture:
1. **`easysam.local_server`**: FastAPI application factory that mirrors API Gateway routing rules, manages process-wide environment variable mutations during handler execution via `_invocation_lock`, and normalizes Lambda response structures.
2. **`easysam.local_handler`**: Dynamic module importer providing isolated execution context (`isolated_import_context`), cleaning `sys.modules` to prevent cross-request handler state leakage.
3. **`easysam.local_event`**: Bi-modal event builder synthesizing AWS API Gateway v1 (REST API) and v2 (HTTP API) event structures, including header normalization, query string aggregation, and binary payload base64 encoding.
4. **`easysam.local_routes`**: Specificity-based route builder sorting exact/non-greedy paths ahead of catch-all greedy paths (`/{path:path}`) and Function URLs (`/__fn/<name>`).
5. **`easysam.local_cli`**: Click CLI group enabling interactive local server execution (`easysam local .`) and direct single-function invocation (`easysam local invoke <function>`).

---

## 4. Security & Performance Audit

- **Security**:
  - Request parameters and headers are safely parsed without dangerous `eval` or shell interpolation.
  - File path resolution in `_parse_json_option` safely traps OS exceptions.
  - CORS middleware is enabled wide-open (`*`) specifically for local DX, which is expected and appropriate for local dev servers.
- **Performance**:
  - Moving network body payload reads (`await build_event(...)`) outside `async with _invocation_lock:` eliminates lock contention under concurrent request loads.
  - Module cleanup selectively purges project-local and stale `common.*` modules while leaving standard library and third-party dependencies warm in `sys.modules`.

---

## 5. Detailed File Findings & Suggestions

### [`src/easysam/local_server.py`](file:///C:/Users/boris/projects/var/easysam/src/easysam/local_server.py)
- **[Severity: Low]** Lines 55 & 65: Case-sensitive header lookup for `Content-Type`.
  - **Context**: AWS Lambda headers can return keys in lower or title case (`content-type` vs `Content-Type`).
  - **Suggested Fix**:
    ```python
    content_type = next((v for k, v in headers.items() if k.lower() == 'content-type'), 'application/octet-stream')
    ```

### [`src/easysam/local_handler.py`](file:///C:/Users/boris/projects/var/easysam/src/easysam/local_handler.py)
- **[Severity: Low]** Line 83: Type annotation for `context` parameter in `load_and_invoke`.
  - **Context**: Currently untyped (`event: dict, context`). Adding `MockLambdaContext | Any` improves IDE auto-completion and static analysis.

---

## 6. Test Coverage & Validation Matrix

| Check | Result | Details |
|---|---|---|
| **Ruff Linter** | **PASS** | `uv run ruff check` — 0 issues |
| **Unit & Integration Tests** | **PASS** | `uv run pytest tests/` — 74/74 passed in 4.89s |
| **Event Synthesis Tests** | **PASS** | 16 test cases covering v1/v2 payload formats, headers, and binary bodies |
| **Server & Route Tests** | **PASS** | 17 test cases covering FastAPI app factory, response translation, and greedy paths |
| **Handler Isolation Tests** | **PASS** | 3 test cases verifying `sys.path` sandbox and `sys.modules` cleanup |

---

## 7. Conclusion & Next Steps

The local Lambda execution feature is in excellent shape, well-tested, robust across platforms (Windows/Linux/macOS), and ready to merge into `main`.

- [x] Pass 1 High/Medium findings resolved
- [x] Linting and formatting 100% clean
- [x] All 74 unit/integration tests green
- [ ] Merge PR #30 into `main`

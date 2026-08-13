# Code Review (Pass 3): `local-mode`

- **Date**: 2026-08-10
- **Target Branch**: `main`
- **Branch**: `local-mode`
- **Files Changed**: 45
- **Decision**: **APPROVE WITH MINOR NITS**

---

## 1. Architectural & Design Overview

This third-pass code review covers the updates to the **Local Gateway & Execution Mode** subsystem in `easysam`, including:
1. **Positional Directory CLI Argument**: Refactored `easysam local` to take `directory` as a positional argument (defaulting to `.`).
2. **AWS Profile & Region Passthrough**: Added support for `--aws-profile` and `--target-region` (along with `EASYSAM_AWS_PROFILE` and `EASYSAM_TARGET_REGION` environment variables) to populate `AWS_PROFILE`, `AWS_DEFAULT_REGION`, and `AWS_REGION` during local server startup and direct invocation.
3. **Synchronous Handler Execution**: Improved thread executor wrapping for synchronous Lambda functions to run isolated handlers cleanly.
4. **Server Facade**: Refactored startup flow into a clean `easysam.local_server.local()` facade function.

---

## 2. Security & Performance Audit

- **Security**:
  - Request body parsing and header normalization handle edge cases cleanly without unsafe dynamic code evaluation.
  - CORS middleware is configured with wildcard origin (`*`), which is standard and appropriate for local developer experience.
  - Per-function environment variables are safely restored in `finally` blocks inside `_invocation_lock`.
- **Performance**:
  - Network IO and event builder generation occur outside the global `_invocation_lock`, eliminating thread lock contention during body streaming.

---

## 3. Detailed File-by-File Findings

### [`src/easysam/local_handler.py`](file:///C:/Users/boris/projects/var/easysam/src/easysam/local_handler.py)
- **[Severity: Medium]** Lines 100–107: Event loop cleanup in `_invoke_sync`.
  - **Context**: In `_invoke_sync`, `asyncio.set_event_loop(loop)` is called, followed by `loop.close()` in `finally:`. However, `asyncio.set_event_loop(None)` is omitted. Leaving a closed loop bound to a thread-pool worker thread can cause `RuntimeError` on subsequent task executions in thread pools or if sync handlers invoke `asyncio.run()`.
  - **Suggested Fix**:
    ```python
    def _invoke_sync():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return handler(event, context)
        finally:
            loop.close()
            asyncio.set_event_loop(None)
    ```
- **[Severity: Low]** Line 84: Missing type annotation for `context` parameter.
  - **Context**: `load_and_invoke(project_root: Path, lambda_dir: Path, event: dict, context)` leaves `context` untyped.
  - **Suggested Fix**:
    ```python
    async def load_and_invoke(
        project_root: Path, lambda_dir: Path, event: dict, context: MockLambdaContext | Any = None
    ) -> dict:
    ```

### [`src/easysam/local_cli.py`](file:///C:/Users/boris/projects/var/easysam/src/easysam/local_cli.py)
- **[Severity: Low]** Lines 140–143: Parity between `invoke` and `local` server AWS region injection.
  - **Context**: `local_cli.py` sets `AWS_DEFAULT_REGION`, but omits `AWS_REGION` (which `local_server.py` sets).
  - **Suggested Fix**:
    ```python
    if target_region:
        os.environ.setdefault('AWS_DEFAULT_REGION', target_region)
        os.environ.setdefault('AWS_REGION', target_region)
    ```
- **[Severity: Low]** Line 95: Line length (E501) exceeds 120 characters (136 chars).

### [`src/easysam/cli.py`](file:///C:/Users/boris/projects/var/easysam/src/easysam/cli.py)
- **[Severity: Low]** Line 35: Line length (E501) exceeds 120 characters (141 chars).

---

## 4. Test Coverage & Validation Matrix

| Check | Result | Details |
|---|---|---|
| **Unit Tests (`tests/`)** | **PASS** | `uv run pytest tests/` — 74/74 unit tests green |
| **Linting (`ruff`)** | **WARN** | 2 line-length warnings (E501) in `cli.py` and `local_cli.py` |
| **Local E2E Tests** | **PASS** | `test_local_e2e.py` passed all end-to-end server invocation scenarios |
| **Event Builders** | **PASS** | `test_local_event.py` passed all v1/v2 payload generation tests |

---

## 5. Actionable Next Steps

- [ ] Add `asyncio.set_event_loop(None)` in `_invoke_sync` in `src/easysam/local_handler.py`.
- [ ] Ensure `AWS_REGION` and `AWS_DEFAULT_REGION` are both set consistently in `src/easysam/local_cli.py`.
- [ ] Reformat long lines in `src/easysam/cli.py` and `src/easysam/local_cli.py` to satisfy `ruff` E501.
- [ ] Merge PR [#30](https://github.com/scartill/easysam/pull/30) into `main`.

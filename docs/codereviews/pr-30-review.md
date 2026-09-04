# PR Review: #30 — Local Gateway Mode

**Reviewed**: 2026-08-04
**Author**: scartill (Boris Resnick)
**Branch**: local-mode → main
**Decision**: REQUEST CHANGES

## Summary
PR #30 successfully implements local Lambda execution mode (`easysam local .` and `easysam local invoke`) with FastAPI routing, module isolation, API Gateway v1/v2 event synthesis, and `sys.path` environment sandbox. All 74 core test cases pass. However, changes are requested to address path parameter corruption on non-greedy routes, unhandled `OSError` on Windows when parsing inline JSON options, cross-platform path matching during module cleanup, and lock contention during HTTP request body reads.

## Findings

### CRITICAL
None

### HIGH

1. **Path parameter corruption on non-greedy routes with `{path}` parameter**
   - **File**: `src/easysam/local_server.py#L136-L137`
   - **Description**: In `_register_route`, `path_params.pop('path')` unconditionally renames any path parameter named `'path'` to `'proxy'`. For non-greedy routes like `/docs/{path}`, AWS API Gateway exposes the path parameter as `event['pathParameters']['path']`. Renaming it to `proxy` breaks handlers expecting `pathParameters['path']`.
   - **Recommendation**: Restrict renaming to greedy catch-all routes: `if route.is_greedy and 'path' in path_params:`.

2. **Unhandled `OSError` on Windows when parsing inline JSON string options**
   - **File**: `src/easysam/local_cli.py#L33-L38`
   - **Description**: `_parse_json_option` calls `Path(value).exists()` prior to trying `json.loads(value)`. On Windows, inline JSON strings containing double quotes (`"`) or colons (`:`) raise `OSError: [WinError 123]` when passed to `Path.exists()`. This causes `easysam local --auth-context '{"principalId": "debug"}'` to crash with an unhandled exception instead of parsing the inline JSON.
   - **Recommendation**: Wrap the file existence check in `try...except (OSError, ValueError): pass`.

### MEDIUM

3. **Incomplete module cleanup on Windows and relative `__file__` paths**
   - **File**: `src/easysam/local_handler.py#L56-L77`
   - **Description**: `isolated_import_context` checks `mod_file.startswith(project_root_abs)`. If `mod.__file__` uses relative paths or different path separators on Windows (e.g. forward vs backslashes), `startswith` fails, leaving local modules cached in `sys.modules` across handler invocations.
   - **Recommendation**: Resolve `mod_file` with `Path(mod_file).resolve()` before performing prefix comparison.

4. **HTTP request body read blocks global execution lock**
   - **File**: `src/easysam/local_server.py#L139-L149`
   - **Description**: `await build_event(...)` reads `await request.body()` *inside* `async with _invocation_lock:`. Reading network payloads while holding the handler lock causes slow client body uploads to block all other concurrent requests to the local server.
   - **Recommendation**: Read request body and build event *before* entering `async with _invocation_lock:`.

### LOW

5. **Unused imports and lint warnings**
   - **Files**: `src/easysam/local_event.py`, `tests/test_local_e2e.py`, `tests/test_local_event.py`, `tests/test_local_handler.py`, `tests/test_local_routes.py`, `tests/test_local_server.py`
   - **Description**: `ruff check` identified unused imports (`time`, `json`, `pytest`, `RouteInfo`, `Path`), line length > 120 chars in `local_server.py`, and trailing whitespace in `test_local_routes.py`.
   - **Recommendation**: Clean up unused imports and run `uv run ruff check --fix`.

## Validation Results

| Check | Result |
|---|---|
| Type check | Pass (`uv run pytest tests/`) |
| Lint | Fail (19 issues reported by `uv run ruff check`) |
| Tests | Pass (74/74 unit/integration tests passed in 2.69s) |
| Build | Pass |

## Files Reviewed
- `pyproject.toml` — Modified (Added `fastapi` and `uvicorn[standard]` dependencies)
- `src/easysam/cli.py` — Modified (Registered `local` CLI command group)
- `src/easysam/local_cli.py` — Added (Click CLI group `local` and `local invoke`)
- `src/easysam/local_event.py` — Added (API Gateway v1/v2 event builders)
- `src/easysam/local_handler.py` — Added (Isolated handler loader and MockLambdaContext)
- `src/easysam/local_routes.py` — Added (Route resolution and specificity sorting)
- `src/easysam/local_server.py` — Added (FastAPI app factory, envvar lock, response normalization)
- `tests/test_local_e2e.py` — Added (End-to-end local server integration tests)
- `tests/test_local_event.py` — Added (Unit tests for event synthesis)
- `tests/test_local_handler.py` — Added (Unit tests for isolated import context)
- `tests/test_local_routes.py` — Added (Unit tests for route sorting and function URLs)
- `tests/test_local_server.py` — Added (Unit tests for response translation and app factory)

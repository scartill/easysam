# Task 2: Handler Isolation Module

- [ ] Complete

## Objective

Build a utility that loads a Lambda handler from a file path with per-invocation `sys.path` isolation, selective `sys.modules` cleanup, and async handler support.

## Implementation

Create `src/easysam/local_handler.py` with:

### `isolated_import_context(project_root: Path, lambda_dir: Path)`

Context manager that:
1. Prepends `[lambda_dir, project_root]` to `sys.path`
2. On exit, purges ALL `sys.modules` entries whose `__file__` originates from `project_root` or `lambda_dir` (preserves third-party caches like `boto3`, `pydantic`)
3. Restores original `sys.path`

```python
@contextmanager
def isolated_import_context(project_root: Path, lambda_dir: Path):
    original_path = sys.path[:]
    sys.path = [str(lambda_dir), str(project_root)] + sys.path

    try:
        yield
    finally:
        sys.path = original_path
        project_root_str = str(project_root)
        lambda_dir_str = str(lambda_dir)
        to_remove = []
        for mod_name, mod in sys.modules.items():
            if mod is None:
                continue
            mod_file = getattr(mod, '__file__', None) or ''
            if mod_file.startswith(project_root_str) or mod_file.startswith(lambda_dir_str):
                to_remove.append(mod_name)
        for mod_name in to_remove:
            del sys.modules[mod_name]
```

### `load_and_invoke(project_root: Path, lambda_dir: Path, event: dict, context) -> dict`

Async function that:
1. Computes handler path as `lambda_dir / 'index.py'`
2. Uses `importlib.util.spec_from_file_location()` with a unique module name (`_easysam_local_<uuid8>`)
3. Executes the module, extracts `handler`
4. Checks `inspect.iscoroutinefunction(handler)` — if true, `await` it; otherwise call directly
5. Returns handler result

### `MockLambdaContext`

Dataclass/class with:
- `function_name: str`
- `memory_limit_in_mb: int = 128`
- `invoked_function_arn: str = "arn:aws:lambda:local:000000000000:function:<name>"`
- `aws_request_id: str = "<uuid>"`

## Files to Create

- `src/easysam/local_handler.py`
- `tests/test_local_handler.py`

## Test

Create two temp lambdas in `tmp_path`:
- `lambda_a/index.py` imports `helpers` and returns `helpers.VALUE`
- `lambda_a/helpers.py` defines `VALUE = "alpha"`
- `lambda_b/index.py` imports `helpers` and returns `helpers.VALUE`
- `lambda_b/helpers.py` defines `VALUE = "beta"`

Invoke both in sequence via `load_and_invoke`. Assert:
- Lambda A returns `"alpha"`
- Lambda B returns `"beta"` (no `sys.modules` contamination)

Also test:
- `async def handler(event, context)` returns correctly
- `MockLambdaContext` has expected attributes

## Demo

```bash
pytest tests/test_local_handler.py -v
```

## Dependencies

- Task 1 (fastapi/uvicorn installed — needed for async event loop in tests)

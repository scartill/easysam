# Task 4: Route Builder

- [ ] Complete

## Objective

Convert loaded resource `paths` and `functions` dicts into a list of route descriptors for FastAPI registration, sorted by specificity.

## Implementation

Create `src/easysam/local_routes.py` with:

### `RouteInfo` dataclass

```python
@dataclass
class RouteInfo:
    path: str              # FastAPI route path (e.g., "/items", "/items/{path:path}")
    function_name: str     # Lambda function name
    lambda_dir: Path       # Absolute path to lambda source directory
    is_greedy: bool        # Whether this is a catch-all route
    is_function_url: bool  # Whether this is a /__fn/ route
    resource_path: str     # Original EasySAM path template (for event building)
```

### `build_routes(resources_data: dict, project_root: Path) -> list[RouteInfo]`

1. Iterate `resources_data['paths']` dict:
   - For each path entry with `integration == "lambda"`:
     - Resolve `function_name` from the path entry
     - Resolve `lambda_dir` from `resources_data['functions'][function_name]['uri']` relative to `project_root`
     - If `greedy` is `True` (or path ends with `/`):
       - Add exact route: `RouteInfo(path="/items", ..., is_greedy=False, resource_path="/items")`
       - Add catch-all route: `RouteInfo(path="/items/{path:path}", ..., is_greedy=True, resource_path="/items/{proxy+}")`
     - If `greedy` is `False`:
       - Add single route: `RouteInfo(path="/items", ..., is_greedy=False, resource_path="/items")`

2. Iterate `resources_data['functions']` for Function URLs:
   - For each function with `functionurl` property:
     - Add route: `RouteInfo(path="/__fn/<name>", ..., is_function_url=True)`

3. **Sort** the result: non-greedy routes first, greedy catch-all routes last. This prevents Starlette route shadowing.

4. Map greedy `{path:path}` captures to `pathParameters["proxy"]` in event building (communicate via `resource_path` field).

### Path parameter conversion

EasySAM paths may contain `{id}` style params — these map directly to FastAPI `{id}` format (no conversion needed).

## Files to Create

- `src/easysam/local_routes.py`
- `tests/test_local_routes.py`

## Test

Sample `resources_data`:
```python
{
    "functions": {
        "listfunc": {"uri": "backend/function/listfunc"},
        "getfunc": {"uri": "backend/function/getfunc"},
        "allfunc": {"uri": "backend/function/allfunc", "functionurl": True},
    },
    "paths": {
        "/items": {"function": "listfunc", "greedy": False, "integration": "lambda", "open": True},
        "/proxy": {"function": "getfunc", "greedy": True, "integration": "lambda", "open": True},
    }
}
```

Assertions:
- 4 routes total: `/items`, `/proxy`, `/proxy/{path:path}`, `/__fn/allfunc`
- Non-greedy routes appear before greedy routes in the list
- `lambda_dir` paths resolve correctly
- Function URL route has `is_function_url=True`

## Demo

```bash
pytest tests/test_local_routes.py -v
```

## Dependencies

None — this task only depends on Python stdlib and `pathlib`.

# Task 5: FastAPI App Factory

- [ ] Complete

## Objective

Wire together routes, handler loading, event building, and response translation into a FastAPI app with thread-safe envvar handling.

## Implementation

Create `src/easysam/local_server.py` with:

### `create_app(resources_data: dict, project_root: Path, event_format: str, auth_context: dict) -> FastAPI`

1. Create `FastAPI()` instance
2. Add CORS middleware: allow all origins, methods, headers
3. Create module-level `asyncio.Lock()` (`_invocation_lock`)
4. Set global envvars from `resources_data.get('envvars', {})` into `os.environ` once at creation
5. Call `build_routes(resources_data, project_root)` to get sorted route list
6. For each `RouteInfo`, register an async route handler:

```python
async def handle_request(request: Request, ...):
    start = time.perf_counter()
    func_envvars = resources_data['functions'][route.function_name].get('envvars', {})
    
    async with _invocation_lock:
        saved_env = {}
        try:
            # Set per-function envvars
            for key, value in func_envvars.items():
                saved_env[key] = os.environ.get(key)
                os.environ[key] = value
            
            # Build event
            event = build_event(request, path_params, route.resource_path, event_format, auth_context)
            context = create_mock_context(route.function_name)
            
            # Invoke handler
            result = await load_and_invoke(project_root, route.lambda_dir, event, context)
        finally:
            # Restore envvars
            for key, original in saved_env.items():
                if original is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original
    
    # Translate response (outside lock)
    response = normalize_response(result)
    
    duration_ms = (time.perf_counter() - start) * 1000
    lg.info(f"[{request.method}] {request.url.path} -> {route.function_name} ({response.status_code}, {duration_ms:.0f}ms)")
    
    return response
```

7. Register error handler for uncaught exceptions → 500 with formatted traceback

### `normalize_response(result) -> Response`

Response normalization logic:
- If `result` is a dict with `statusCode`:
  - Extract `statusCode`, `headers` (optional), `body` (optional)
  - If `isBase64Encoded` is `True`: decode `body` from base64 to bytes
  - If `body` is a dict: JSON-encode it
  - Return `Response(content=body, status_code=statusCode, headers=headers)`
- If `result` is a dict WITHOUT `statusCode` (v2 auto-format):
  - Return `JSONResponse(content=result, status_code=200)`
- If `result` is a string/primitive:
  - Return `Response(content=str(result), status_code=200)`
- On uncaught handler exception:
  - Return `Response(content=traceback.format_exc(), status_code=500)`

### Route registration

- All methods accepted per route (use `api_route(..., methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])`)
- Exact routes registered before greedy catch-all routes (already sorted by `build_routes`)

## Files to Create

- `src/easysam/local_server.py`
- `tests/test_local_server.py`

## Test

Integration test using FastAPI `TestClient` with `example/myapp`:

1. Load resources via `load.resources(Path('example/myapp'), [], {'environment': 'dev', 'target_region': 'us-east-1'}, [])`
2. Create app with `create_app(resources_data, Path('example/myapp'), 'v1', {})`
3. GET `/items` → assert status 200, body contains output from `my_common_function()`
4. Test handler returning simple dict without `statusCode` → auto-wrapped to 200
5. Test handler that raises → returns 500 with traceback
6. Test request logging output (capture log)

## Demo

```bash
pytest tests/test_local_server.py -v
```

## Dependencies

- Task 1 (fastapi/uvicorn)
- Task 2 (`load_and_invoke`, `MockLambdaContext`)
- Task 3 (`build_event`, `create_mock_context`)
- Task 4 (`build_routes`, `RouteInfo`)

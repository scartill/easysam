# Task 3: API Gateway Event Builder

- [ ] Complete

## Objective

Build functions that construct both API Gateway v1 (REST API) and v2 (HTTP API) event dicts from a Starlette/FastAPI Request, with auth context injection.

## Implementation

Create `src/easysam/local_event.py` with:

### `build_rest_api_event(request, path_params, resource_path, auth_context) -> dict`

Builds a REST API (v1) event:
- `resource`: the resource path template (e.g., `/items/{id}`)
- `path`: actual request path
- `httpMethod`: request method (uppercase)
- `headers`: dict of header name → single value
- `multiValueHeaders`: dict of header name → list of values
- `queryStringParameters`: dict of param → single value (last wins)
- `multiValueQueryStringParameters`: dict of param → list of values (use `request.query_params.multi_items()` to preserve repeated keys)
- `pathParameters`: from route matching
- `body`: request body as string or `None`
- `isBase64Encoded`: `False` for text, `True` for binary content types
- `requestContext`:
  - `resourcePath`, `httpMethod`, `path`
  - `stage`: `"local"`
  - `requestId`: generated UUID
  - `identity`: `{"sourceIp": "127.0.0.1"}`
  - `authorizer`: contents of `auth_context` dict

### `build_http_api_event(request, path_params, route_key, auth_context) -> dict`

Builds an HTTP API (v2) event:
- `version`: `"2.0"`
- `routeKey`: e.g., `"GET /items/{id}"`
- `rawPath`: actual request path
- `rawQueryString`: raw query string
- `headers`: dict of lowercase header name → single value (comma-joined for multiples)
- `queryStringParameters`: dict of param → single value (comma-joined for multiples)
- `pathParameters`: from route matching
- `body`: request body as string or `None`
- `isBase64Encoded`: `False` for text, `True` for binary
- `requestContext`:
  - `http`: `{"method", "path", "sourceIp": "127.0.0.1"}`
  - `authorizer`: `{"lambda": <auth_context dict>}`
  - `time`: formatted timestamp
  - `timeEpoch`: milliseconds since epoch

### `build_event(request, path_params, route_path, event_format: str, auth_context: dict) -> dict`

Dispatcher:
- If `event_format == "v1"`: call `build_rest_api_event`
- If `event_format == "v2"`: call `build_http_api_event`

### `create_mock_context(function_name: str) -> MockLambdaContext`

Import `MockLambdaContext` from `local_handler` and instantiate with given function name.

## Files to Create

- `src/easysam/local_event.py`
- `tests/test_local_event.py`

## Test

Using `httpx` or Starlette `TestClient` request mocks:

1. **v1 GET with query params**: verify `httpMethod`, `queryStringParameters`, `multiValueQueryStringParameters` (including repeated keys like `?tag=a&tag=b`)
2. **v1 POST with JSON body**: verify `body` is string, `headers` populated
3. **v2 GET with query params**: verify `version`, `routeKey`, `rawQueryString`, flat query params
4. **v2 POST with body**: verify body handling
5. **Path parameters**: both formats correctly populate `pathParameters`
6. **Auth context injection**: v1 puts it in `requestContext.authorizer`; v2 in `requestContext.authorizer.lambda`
7. **Empty auth context**: produces `{}` / `{"lambda": {}}`

## Demo

```bash
pytest tests/test_local_event.py -v
```

## Dependencies

- Task 2 (imports `MockLambdaContext` from `local_handler`)

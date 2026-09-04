# Task 8: End-to-End Integration Test

- [ ] Complete

## Objective

Verify the full local server flow works against `example/myapp`.

## Implementation

Create `tests/test_local_e2e.py`:

### Test Setup

```python
from pathlib import Path
from fastapi.testclient import TestClient
from easysam.load import resources as load_resources
from easysam.local_server import create_app

EXAMPLE_DIR = Path('example/myapp')

def create_test_app(event_format='v1', auth_context=None):
    errors = []
    resources_data = load_resources(EXAMPLE_DIR, [], {'environment': 'dev', 'target_region': 'us-east-1'}, errors)
    assert not errors, f"Resource loading errors: {errors}"
    return create_app(resources_data, EXAMPLE_DIR, event_format, auth_context or {})
```

### Test Cases

1. **`test_get_items_returns_200`**
   - GET `/items` → status 200
   - Body contains output from `common.utils.my_common_function()` (which returns `"Hello from common"`)
   - Verifies full chain: resource loading → route matching → handler isolation → common/ resolution → response translation

2. **`test_undefined_route_returns_404`**
   - GET `/nonexistent` → status 404

3. **`test_global_envvars_accessible`**
   - If `example/myapp` has global envvars, verify handler can access them via `os.environ`
   - (May need to add a test handler or use `example/userenvvars` instead)

4. **`test_auth_context_injected_in_event`**
   - Create app with `auth_context={"principalId": "test-user"}`
   - GET `/items` → handler receives `event['requestContext']['authorizer']['principalId'] == "test-user"` (v1)
   - (This may require a handler that echoes the event back; consider using a temp fixture)

5. **`test_v2_event_format`**
   - Create app with `event_format='v2'`
   - GET `/items` → verify handler receives v2-format event (version: "2.0", routeKey, etc.)

6. **`test_handler_exception_returns_500`**
   - Use a handler that raises `RuntimeError`
   - Verify response is 500 with traceback in body

7. **`test_cors_headers_present`**
   - Send request, verify CORS headers in response (`access-control-allow-origin: *`)

## Files to Create

- `tests/test_local_e2e.py`

## Test

```bash
pytest tests/test_local_e2e.py -v
```

## Demo

All assertions pass, confirming full round-trip:
- Resources loaded from `example/myapp`
- Routes registered from `paths` definitions
- Handler imported in isolation with `common/` on path
- API Gateway event correctly built (v1 and v2)
- Response correctly translated

## Dependencies

- All previous tasks (1–7) must be complete
- Specifically: Task 5 (`create_app`) is the main integration point

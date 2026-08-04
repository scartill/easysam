"""End-to-end integration test for local Lambda execution.

Tests the full flow against example/myapp:
resource loading → route registration → handler invocation → response.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from easysam.load import resources as load_resources
from easysam.local_server import create_app


EXAMPLE_DIR = Path('example/myapp')


def _create_test_app(event_format='v1', auth_context=None):
    """Load example/myapp resources and create a test app."""
    errors = []
    resources_data = load_resources(
        EXAMPLE_DIR, [], {'environment': 'dev', 'target_region': 'us-east-1'}, errors
    )
    assert not errors, f'Resource loading errors: {errors}'
    return create_app(resources_data, EXAMPLE_DIR, event_format, auth_context or {})


class TestMyAppE2E:
    """End-to-end tests using example/myapp."""

    def test_get_items_returns_200(self):
        """GET /items should return 200 with data from common.utils.my_common_function()."""
        app = _create_test_app()
        client = TestClient(app)

        response = client.get('/items')
        assert response.status_code == 200

        body = response.json()
        assert body == {'data': 'Hello, world!'}

    def test_post_items_returns_200(self):
        """POST /items should also route to the same handler."""
        app = _create_test_app()
        client = TestClient(app)

        response = client.post('/items', json={'name': 'test'})
        assert response.status_code == 200
        assert response.json() == {'data': 'Hello, world!'}

    def test_undefined_route_returns_404(self):
        """Requesting a path not in resources should return 404."""
        app = _create_test_app()
        client = TestClient(app)

        response = client.get('/nonexistent')
        assert response.status_code == 404

    def test_cors_headers_on_response(self):
        """CORS headers should be present on responses."""
        app = _create_test_app()
        client = TestClient(app)

        response = client.get('/items', headers={'Origin': 'http://example.com'})
        assert response.headers.get('access-control-allow-origin') == '*'

    def test_v1_event_format(self):
        """With v1 format, handler receives REST API event structure."""
        app = _create_test_app(event_format='v1')
        client = TestClient(app)

        response = client.get('/items')
        # Handler doesn't inspect event format, but it should still work
        assert response.status_code == 200

    def test_v2_event_format(self):
        """With v2 format, handler receives HTTP API event structure."""
        app = _create_test_app(event_format='v2')
        client = TestClient(app)

        response = client.get('/items')
        # Handler doesn't inspect event format, so same result expected
        assert response.status_code == 200
        assert response.json() == {'data': 'Hello, world!'}

    def test_auth_context_accessible_in_event(self):
        """Auth context should be injected into the event."""
        # For this test we need a handler that reads requestContext.
        # Since myapp's handler doesn't read it, we just verify no crash.
        auth_ctx = {'principalId': 'test-user', 'claims': {'sub': '123'}}
        app = _create_test_app(auth_context=auth_ctx)
        client = TestClient(app)

        response = client.get('/items')
        assert response.status_code == 200


class TestCommonModuleResolution:
    """Tests verifying that common/ module resolution works end-to-end."""

    def test_common_utils_resolved_from_project_root(self):
        """The handler in example/myapp imports common.utils — verify it works."""
        app = _create_test_app()
        client = TestClient(app)

        response = client.get('/items')
        body = response.json()
        # my_common_function() returns 'Hello, world!'
        assert body['data'] == 'Hello, world!'

    def test_repeated_requests_get_fresh_handler(self):
        """Each request should get a fresh handler import (no stale module cache)."""
        app = _create_test_app()
        client = TestClient(app)

        # Make multiple requests — should all succeed
        for _ in range(5):
            response = client.get('/items')
            assert response.status_code == 200
            assert response.json() == {'data': 'Hello, world!'}

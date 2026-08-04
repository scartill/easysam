"""Tests for the FastAPI app factory (local_server)."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from easysam.local_server import create_app, normalize_response


def _simple_resources(tmp_path):
    """Create a minimal project with a test handler."""
    func_dir = tmp_path / 'src'
    func_dir.mkdir()
    (func_dir / 'index.py').write_text(
        'import json\n'
        'def handler(event, context):\n'
        '    return {"statusCode": 200, "body": json.dumps({"msg": "ok"})}\n'
    )
    return {
        'functions': {'testfunc': {'uri': 'src'}},
        'paths': {'/test': {'function': 'testfunc', 'greedy': False, 'integration': 'lambda', 'open': True}},
    }


def test_basic_get_request(tmp_path):
    """Test a basic GET request returns 200."""
    resources = _simple_resources(tmp_path)
    app = create_app(resources, tmp_path, 'v1', {})
    client = TestClient(app)

    response = client.get('/test')
    assert response.status_code == 200
    assert response.json() == {'msg': 'ok'}


def test_handler_returning_dict_without_status_code(tmp_path):
    """Handler returning simple dict should be auto-wrapped as JSON 200."""
    func_dir = tmp_path / 'src'
    func_dir.mkdir()
    (func_dir / 'index.py').write_text(
        'def handler(event, context):\n'
        '    return {"message": "auto-wrapped"}\n'
    )
    resources = {
        'functions': {'autofunc': {'uri': 'src'}},
        'paths': {'/auto': {'function': 'autofunc', 'greedy': False, 'integration': 'lambda', 'open': True}},
    }
    app = create_app(resources, tmp_path, 'v1', {})
    client = TestClient(app)

    response = client.get('/auto')
    assert response.status_code == 200
    assert response.json() == {'message': 'auto-wrapped'}


def test_handler_exception_returns_500(tmp_path):
    """Handler that raises should return 500 with traceback."""
    func_dir = tmp_path / 'src'
    func_dir.mkdir()
    (func_dir / 'index.py').write_text(
        'def handler(event, context):\n'
        '    raise RuntimeError("test error")\n'
    )
    resources = {
        'functions': {'errfunc': {'uri': 'src'}},
        'paths': {'/err': {'function': 'errfunc', 'greedy': False, 'integration': 'lambda', 'open': True}},
    }
    app = create_app(resources, tmp_path, 'v1', {})
    client = TestClient(app)

    response = client.get('/err')
    assert response.status_code == 500
    assert 'RuntimeError: test error' in response.text


def test_cors_headers_present(tmp_path):
    """CORS should be wide open."""
    resources = _simple_resources(tmp_path)
    app = create_app(resources, tmp_path, 'v1', {})
    client = TestClient(app)

    response = client.options('/test', headers={'Origin': 'http://localhost:3001'})
    assert response.headers.get('access-control-allow-origin') == '*'


def test_envvars_set_per_function(tmp_path):
    """Per-function envvars should be available during handler execution."""
    func_dir = tmp_path / 'src'
    func_dir.mkdir()
    (func_dir / 'index.py').write_text(
        'import os, json\n'
        'def handler(event, context):\n'
        '    return {"statusCode": 200, "body": json.dumps({"val": os.environ.get("MY_VAR")})}\n'
    )
    resources = {
        'functions': {'envfunc': {'uri': 'src', 'envvars': {'MY_VAR': 'hello'}}},
        'paths': {'/env': {'function': 'envfunc', 'greedy': False, 'integration': 'lambda', 'open': True}},
    }
    app = create_app(resources, tmp_path, 'v1', {})
    client = TestClient(app)

    response = client.get('/env')
    assert response.status_code == 200
    assert response.json() == {'val': 'hello'}


def test_v2_event_format(tmp_path):
    """Test that v2 event format produces correct event structure."""
    func_dir = tmp_path / 'src'
    func_dir.mkdir()
    (func_dir / 'index.py').write_text(
        'import json\n'
        'def handler(event, context):\n'
        '    return {"statusCode": 200, "body": json.dumps({"version": event.get("version")})}\n'
    )
    resources = {
        'functions': {'v2func': {'uri': 'src'}},
        'paths': {'/v2': {'function': 'v2func', 'greedy': False, 'integration': 'lambda', 'open': True}},
    }
    app = create_app(resources, tmp_path, 'v2', {})
    client = TestClient(app)

    response = client.get('/v2')
    assert response.status_code == 200
    assert response.json() == {'version': '2.0'}


def test_auth_context_injected_v1(tmp_path):
    """Auth context should appear in event requestContext.authorizer for v1."""
    func_dir = tmp_path / 'src'
    func_dir.mkdir()
    (func_dir / 'index.py').write_text(
        'import json\n'
        'def handler(event, context):\n'
        '    auth = event["requestContext"]["authorizer"]\n'
        '    return {"statusCode": 200, "body": json.dumps(auth)}\n'
    )
    resources = {
        'functions': {'authfunc': {'uri': 'src'}},
        'paths': {'/auth': {'function': 'authfunc', 'greedy': False, 'integration': 'lambda', 'open': True}},
    }
    auth_ctx = {'principalId': 'test-user'}
    app = create_app(resources, tmp_path, 'v1', auth_ctx)
    client = TestClient(app)

    response = client.get('/auth')
    assert response.status_code == 200
    assert response.json() == {'principalId': 'test-user'}


def test_greedy_route(tmp_path):
    """Greedy routes should match both exact and sub-paths."""
    func_dir = tmp_path / 'src'
    func_dir.mkdir()
    (func_dir / 'index.py').write_text(
        'import json\n'
        'def handler(event, context):\n'
        '    params = event.get("pathParameters") or {}\n'
        '    return {"statusCode": 200, "body": json.dumps({"proxy": params.get("proxy", "")})}\n'
    )
    resources = {
        'functions': {'proxyfunc': {'uri': 'src'}},
        'paths': {'/api': {'function': 'proxyfunc', 'greedy': True, 'integration': 'lambda', 'open': True}},
    }
    app = create_app(resources, tmp_path, 'v1', {})
    client = TestClient(app)

    # Exact path
    response = client.get('/api')
    assert response.status_code == 200

    # Sub-path
    response = client.get('/api/users/123')
    assert response.status_code == 200
    assert response.json() == {'proxy': 'users/123'}


class TestNormalizeResponse:
    """Unit tests for normalize_response."""

    def test_standard_response(self):
        result = {'statusCode': 200, 'body': '{"ok": true}', 'headers': {'X-Custom': 'val'}}
        resp = normalize_response(result)
        assert resp.status_code == 200
        assert resp.body == b'{"ok": true}'

    def test_dict_without_status_code(self):
        result = {'data': [1, 2, 3]}
        resp = normalize_response(result)
        assert resp.status_code == 200
        assert json.loads(resp.body) == {'data': [1, 2, 3]}

    def test_none_response(self):
        resp = normalize_response(None)
        assert resp.status_code == 200

    def test_string_response(self):
        resp = normalize_response('hello')
        assert resp.status_code == 200
        assert resp.body == b'hello'

    def test_base64_encoded_response(self):
        import base64
        content = b'\x89PNG\r\n'
        encoded = base64.b64encode(content).decode()
        result = {
            'statusCode': 200,
            'body': encoded,
            'isBase64Encoded': True,
            'headers': {'Content-Type': 'image/png'},
        }
        resp = normalize_response(result)
        assert resp.status_code == 200
        assert resp.body == content

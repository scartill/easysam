"""Tests for the API Gateway event builder."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from easysam.local_event import (
    build_event,
    build_http_api_event,
    build_rest_api_event,
)


def _make_request(method='GET', path='/items', query_string=b'', headers=None, body=b''):
    """Create a mock Starlette Request."""
    request = MagicMock()
    request.method = method
    request.url.path = path
    request.url.query = query_string.decode() if query_string else ''
    request.client = MagicMock()
    request.client.host = '127.0.0.1'

    # Headers
    header_list = list((headers or {}).items())
    request.headers = MagicMock()
    request.headers.items = MagicMock(return_value=header_list)
    request.headers.get = lambda key, default=None: dict(header_list).get(key, default)

    # Query params
    if query_string:
        from urllib.parse import parse_qsl
        multi_items = parse_qsl(query_string.decode())
        request.query_params = MagicMock()
        request.query_params.__bool__ = lambda self: True
        request.query_params.multi_items = MagicMock(return_value=multi_items)
    else:
        request.query_params = MagicMock()
        request.query_params.__bool__ = lambda self: False

    # Body
    request.body = AsyncMock(return_value=body)

    return request


class TestRestApiEvent:
    """Tests for REST API (v1) event building."""

    def test_get_with_query_params(self):
        request = _make_request(
            method='GET',
            path='/items',
            query_string=b'page=1&limit=10',
        )
        event = asyncio.run(build_rest_api_event(request, {}, '/items', {}))

        assert event['httpMethod'] == 'GET'
        assert event['path'] == '/items'
        assert event['resource'] == '/items'
        assert event['queryStringParameters'] == {'page': '1', 'limit': '10'}
        assert event['multiValueQueryStringParameters'] == {'page': ['1'], 'limit': ['10']}
        assert event['body'] is None
        assert event['isBase64Encoded'] is False
        assert event['requestContext']['stage'] == 'local'
        assert event['requestContext']['httpMethod'] == 'GET'
        assert event['requestContext']['identity']['sourceIp'] == '127.0.0.1'

    def test_post_with_json_body(self):
        request = _make_request(
            method='POST',
            path='/items',
            headers={'content-type': 'application/json'},
            body=b'{"name": "test"}',
        )
        event = asyncio.run(build_rest_api_event(request, {}, '/items', {}))

        assert event['httpMethod'] == 'POST'
        assert event['body'] == '{"name": "test"}'
        assert event['isBase64Encoded'] is False
        assert event['headers']['content-type'] == 'application/json'
        assert event['multiValueHeaders']['content-type'] == ['application/json']

    def test_path_parameters(self):
        request = _make_request(method='GET', path='/items/123')
        event = asyncio.run(build_rest_api_event(request, {'id': '123'}, '/items/{id}', {}))

        assert event['pathParameters'] == {'id': '123'}
        assert event['resource'] == '/items/{id}'
        assert event['path'] == '/items/123'
        assert event['requestContext']['resourcePath'] == '/items/{id}'

    def test_multi_value_query_params(self):
        """Repeated query keys should produce multi-value lists."""
        request = _make_request(
            method='GET',
            path='/items',
            query_string=b'tag=a&tag=b&page=1',
        )
        event = asyncio.run(build_rest_api_event(request, {}, '/items', {}))

        assert event['queryStringParameters'] == {'tag': 'b', 'page': '1'}  # last wins
        assert event['multiValueQueryStringParameters'] == {'tag': ['a', 'b'], 'page': ['1']}

    def test_auth_context_injected(self):
        request = _make_request()
        auth_ctx = {'principalId': 'debug_principal', 'role': 'admin'}
        event = asyncio.run(build_rest_api_event(request, {}, '/items', auth_ctx))

        assert event['requestContext']['authorizer'] == auth_ctx

    def test_empty_auth_context(self):
        request = _make_request()
        event = asyncio.run(build_rest_api_event(request, {}, '/items', {}))

        assert event['requestContext']['authorizer'] == {}

    def test_no_query_params_returns_none(self):
        request = _make_request(method='GET', path='/items')
        event = asyncio.run(build_rest_api_event(request, {}, '/items', {}))

        assert event['queryStringParameters'] is None
        assert event['multiValueQueryStringParameters'] is None


class TestHttpApiEvent:
    """Tests for HTTP API (v2) event building."""

    def test_get_with_query_params(self):
        request = _make_request(
            method='GET',
            path='/items',
            query_string=b'page=1&limit=10',
        )
        event = asyncio.run(build_http_api_event(request, {}, 'GET /items', {}))

        assert event['version'] == '2.0'
        assert event['routeKey'] == 'GET /items'
        assert event['rawPath'] == '/items'
        assert event['rawQueryString'] == 'page=1&limit=10'
        assert event['queryStringParameters'] == {'page': '1', 'limit': '10'}
        assert event['body'] is None
        assert event['isBase64Encoded'] is False
        assert event['requestContext']['http']['method'] == 'GET'
        assert event['requestContext']['http']['path'] == '/items'

    def test_post_with_body(self):
        request = _make_request(
            method='POST',
            path='/items',
            headers={'content-type': 'application/json'},
            body=b'{"name": "test"}',
        )
        event = asyncio.run(build_http_api_event(request, {}, 'POST /items', {}))

        assert event['body'] == '{"name": "test"}'
        assert event['headers']['content-type'] == 'application/json'

    def test_path_parameters(self):
        request = _make_request(method='GET', path='/items/123')
        event = asyncio.run(build_http_api_event(request, {'id': '123'}, 'GET /items/{id}', {}))

        assert event['pathParameters'] == {'id': '123'}

    def test_auth_context_in_lambda_key(self):
        request = _make_request()
        auth_ctx = {'principalId': 'debug_principal'}
        event = asyncio.run(build_http_api_event(request, {}, 'GET /items', auth_ctx))

        assert event['requestContext']['authorizer'] == {'lambda': auth_ctx}

    def test_empty_auth_context(self):
        request = _make_request()
        event = asyncio.run(build_http_api_event(request, {}, 'GET /items', {}))

        assert event['requestContext']['authorizer'] == {'lambda': {}}

    def test_multi_value_query_comma_joined(self):
        """v2 format comma-joins repeated query params."""
        request = _make_request(
            method='GET',
            path='/items',
            query_string=b'tag=a&tag=b',
        )
        event = asyncio.run(build_http_api_event(request, {}, 'GET /items', {}))

        assert event['queryStringParameters'] == {'tag': 'a,b'}

    def test_timestamp_fields_present(self):
        request = _make_request()
        event = asyncio.run(build_http_api_event(request, {}, 'GET /items', {}))

        assert 'time' in event['requestContext']
        assert 'timeEpoch' in event['requestContext']
        assert isinstance(event['requestContext']['timeEpoch'], int)


class TestBuildEventDispatcher:
    """Tests for the format dispatcher."""

    def test_v1_dispatches_to_rest_api(self):
        request = _make_request(method='GET', path='/items')
        event = asyncio.run(build_event(request, {}, '/items', 'v1', {}))

        assert 'httpMethod' in event
        assert 'version' not in event

    def test_v2_dispatches_to_http_api(self):
        request = _make_request(method='GET', path='/items')
        event = asyncio.run(build_event(request, {}, '/items', 'v2', {}))

        assert event['version'] == '2.0'
        assert 'httpMethod' not in event

"""API Gateway event builders for local Lambda execution.

Supports both REST API (v1) and HTTP API (v2) event formats.
"""

from __future__ import annotations

import base64
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from starlette.requests import Request


# Content types that should be treated as binary
BINARY_CONTENT_TYPES = frozenset([
    'application/octet-stream',
    'image/png',
    'image/jpeg',
    'image/gif',
    'image/webp',
    'application/pdf',
    'application/zip',
])


def _is_binary_content_type(content_type: str | None) -> bool:
    """Check if the content type indicates binary content."""
    if not content_type:
        return False
    # Check base content type (without parameters like charset)
    base_type = content_type.split(';')[0].strip().lower()
    return base_type in BINARY_CONTENT_TYPES


async def _get_body(request: Request) -> tuple[str | None, bool]:
    """Read request body and determine if it should be base64-encoded."""
    body_bytes = await request.body()
    if not body_bytes:
        return None, False

    content_type = request.headers.get('content-type')
    if _is_binary_content_type(content_type):
        return base64.b64encode(body_bytes).decode('utf-8'), True
    else:
        return body_bytes.decode('utf-8', errors='replace'), False


async def build_rest_api_event(
    request: Request,
    path_params: dict[str, str],
    resource_path: str,
    auth_context: dict[str, Any],
) -> dict[str, Any]:
    """Build an API Gateway REST API (v1) event from a request.

    Args:
        request: The incoming Starlette/FastAPI request.
        path_params: Path parameters extracted from route matching.
        resource_path: The resource path template (e.g., '/items/{id}').
        auth_context: Authorization context to inject into requestContext.authorizer.
    """
    body, is_base64 = await _get_body(request)

    # Headers
    headers: dict[str, str] = {}
    multi_value_headers: dict[str, list[str]] = {}
    for key, value in request.headers.items():
        # Use original case for v1
        headers[key] = value
        multi_value_headers.setdefault(key, []).append(value)

    # Query string parameters
    query_params: dict[str, str] | None = None
    multi_value_query_params: dict[str, list[str]] | None = None
    if request.query_params:
        query_params = {}
        multi_value_query_params = {}
        for key, value in request.query_params.multi_items():
            query_params[key] = value  # Last value wins
            multi_value_query_params.setdefault(key, []).append(value)

    return {
        'resource': resource_path,
        'path': request.url.path,
        'httpMethod': request.method,
        'headers': headers or None,
        'multiValueHeaders': multi_value_headers or None,
        'queryStringParameters': query_params,
        'multiValueQueryStringParameters': multi_value_query_params,
        'pathParameters': path_params or None,
        'body': body,
        'isBase64Encoded': is_base64,
        'requestContext': {
            'resourcePath': resource_path,
            'httpMethod': request.method,
            'path': request.url.path,
            'stage': 'local',
            'requestId': str(uuid.uuid4()),
            'identity': {
                'sourceIp': request.client.host if request.client else '127.0.0.1',
            },
            'authorizer': auth_context,
        },
    }


async def build_http_api_event(
    request: Request,
    path_params: dict[str, str],
    route_key: str,
    auth_context: dict[str, Any],
) -> dict[str, Any]:
    """Build an API Gateway HTTP API (v2) event from a request.

    Args:
        request: The incoming Starlette/FastAPI request.
        path_params: Path parameters extracted from route matching.
        route_key: The route key (e.g., 'GET /items/{id}').
        auth_context: Authorization context to inject into requestContext.authorizer.lambda.
    """
    body, is_base64 = await _get_body(request)

    # Headers — lowercase, comma-joined for multiples
    headers: dict[str, str] = {}
    for key, value in request.headers.items():
        key_lower = key.lower()
        if key_lower in headers:
            headers[key_lower] = f"{headers[key_lower]},{value}"
        else:
            headers[key_lower] = value

    # Query string parameters — comma-joined for multiples
    query_params: dict[str, str] | None = None
    if request.query_params:
        query_params = {}
        for key, value in request.query_params.multi_items():
            if key in query_params:
                query_params[key] = f"{query_params[key]},{value}"
            else:
                query_params[key] = value

    now = datetime.now(timezone.utc)

    return {
        'version': '2.0',
        'routeKey': route_key,
        'rawPath': request.url.path,
        'rawQueryString': str(request.url.query) if request.url.query else '',
        'headers': headers,
        'queryStringParameters': query_params,
        'pathParameters': path_params or None,
        'body': body,
        'isBase64Encoded': is_base64,
        'requestContext': {
            'http': {
                'method': request.method,
                'path': request.url.path,
                'sourceIp': request.client.host if request.client else '127.0.0.1',
            },
            'authorizer': {'lambda': auth_context},
            'time': now.strftime('%d/%b/%Y:%H:%M:%S +0000'),
            'timeEpoch': int(now.timestamp() * 1000),
        },
    }


async def build_event(
    request: Request,
    path_params: dict[str, str],
    resource_path: str,
    event_format: str,
    auth_context: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch to the appropriate event builder based on format.

    Args:
        request: The incoming request.
        path_params: Path parameters from route matching.
        resource_path: The resource path template or route key.
        event_format: 'v1' for REST API or 'v2' for HTTP API.
        auth_context: Authorization context dict.
    """
    if event_format == 'v2':
        route_key = f"{request.method} {resource_path}"
        return await build_http_api_event(request, path_params, route_key, auth_context)
    else:
        return await build_rest_api_event(request, path_params, resource_path, auth_context)

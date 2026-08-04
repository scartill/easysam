"""FastAPI application factory for local Lambda execution.

Creates a FastAPI app that routes HTTP requests to Lambda handlers
with thread-safe environment variable handling and response normalization.
"""

import asyncio
import base64
import json
import logging as lg
import os
import time
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from easysam.local_event import build_event
from easysam.local_handler import MockLambdaContext, load_and_invoke
from easysam.local_routes import RouteInfo, build_routes


def local(
    directory: Path,
    deploy_ctx: dict,
    port: int = 3000,
    host: str = '127.0.0.1',
    event_format: str = 'v1',
    auth_context: dict | None = None,
) -> None:
    """Start the local Lambda execution server.

    Facade function for programmatic use — starts a local HTTP server
    that mocks API Gateway routing and invokes Lambda handlers directly.

    Args:
        directory: Project root directory containing resources.yaml.
        deploy_ctx: Deployment context dict (must include 'environment').
        port: Port to listen on (default: 3000).
        host: Host to bind to (default: '127.0.0.1').
        event_format: API Gateway event format, 'v1' (REST) or 'v2' (HTTP API).
        auth_context: Authorization context dict injected into requestContext.authorizer.

    Raises:
        UserWarning: If resource loading produces errors.
    """
    import uvicorn

    from easysam.load import resources as load_resources

    if auth_context is None:
        auth_context = {}

    errors = []
    resources_data = load_resources(directory, [], deploy_ctx, errors)

    if errors:
        for e in errors:
            lg.error(e)
        raise UserWarning(f'There were {len(errors)} error(s) loading resources')

    # Set global envvars
    for key, value in resources_data.get('envvars', {}).items():
        os.environ[key] = str(value)

    app = create_app(resources_data, directory, event_format, auth_context)

    lg.info(f'Starting local server on {host}:{port} (event format: {event_format})')
    uvicorn.run(app, host=host, port=port)


# Module-level lock for serializing handler invocations with envvar mutations
_invocation_lock = asyncio.Lock()


def normalize_response(result: Any) -> Response:
    """Translate Lambda handler output to an HTTP response.

    Supports:
    - Standard Lambda response: {"statusCode": 200, "body": "...", "headers": {...}}
    - Simple dict without statusCode (v2 auto-format): wrapped as JSON 200
    - String/primitive: wrapped as plain text 200
    - isBase64Encoded: True → decode body from base64
    """
    if result is None:
        return Response(content='', status_code=200)

    if isinstance(result, dict):
        if 'statusCode' in result:
            status_code = int(result['statusCode'])
            headers = result.get('headers') or {}
            body = result.get('body', '')
            is_base64 = result.get('isBase64Encoded', False)

            if is_base64 and body:
                content = base64.b64decode(body)
                return Response(
                    content=content,
                    status_code=status_code,
                    headers=headers,
                    media_type=headers.get('Content-Type', 'application/octet-stream'),
                )

            if isinstance(body, dict):
                body = json.dumps(body)

            return Response(
                content=body,
                status_code=status_code,
                headers=headers,
                media_type=headers.get('Content-Type', 'application/json'),
            )
        else:
            # Dict without statusCode → auto-wrap as JSON 200
            return JSONResponse(content=result, status_code=200)

    # String or primitive
    return Response(content=str(result), status_code=200)


def create_app(
    resources_data: dict,
    project_root: Path,
    event_format: str = 'v1',
    auth_context: dict | None = None,
) -> FastAPI:
    """Create a FastAPI app that routes requests to Lambda handlers.

    Args:
        resources_data: Loaded EasySAM resource definitions (from load.resources()).
        project_root: Root directory of the EasySAM project.
        event_format: 'v1' for REST API or 'v2' for HTTP API event format.
        auth_context: Authorization context dict to inject into events.
    """
    if auth_context is None:
        auth_context = {}

    app = FastAPI(title='EasySAM Local Server')

    # CORS: wide open for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_methods=['*'],
        allow_headers=['*'],
        allow_credentials=False,
    )

    # Build and register routes
    routes = build_routes(resources_data, project_root)
    functions = resources_data.get('functions', {})

    for route in routes:
        _register_route(app, route, functions, project_root, event_format, auth_context)

    return app


def _register_route(
    app: FastAPI,
    route: RouteInfo,
    functions: dict,
    project_root: Path,
    event_format: str,
    auth_context: dict,
) -> None:
    """Register a single route on the FastAPI app."""
    func_config = functions.get(route.function_name, {})
    func_envvars = func_config.get('envvars', {})

    all_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']

    async def route_handler(request: Request) -> Response:
        start = time.perf_counter()
        status_code = 500

        try:
            # Extract path params from the request's path_params
            path_params = dict(request.path_params)
            if route.is_greedy and 'path' in path_params:
                path_params['proxy'] = path_params.pop('path')

            # Build event OUTSIDE the lock (reads request body without blocking others)
            event = await build_event(
                request, path_params, route.resource_path, event_format, auth_context
            )
            context = MockLambdaContext(function_name=route.function_name)

            async with _invocation_lock:
                saved_env: dict[str, str | None] = {}
                try:
                    # Set per-function envvars
                    for key, value in func_envvars.items():
                        saved_env[key] = os.environ.get(key)
                        os.environ[key] = str(value)

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
            status_code = response.status_code

        except Exception:
            tb = traceback.format_exc()
            lg.error(f'Handler {route.function_name} raised an exception:\n{tb}')
            response = Response(content=tb, status_code=500, media_type='text/plain')
            status_code = 500

        duration_ms = (time.perf_counter() - start) * 1000
        lg.info(f'[{request.method}] {request.url.path} -> {route.function_name} ({status_code}, {duration_ms:.0f}ms)')

        return response

    # Give each handler a unique name to avoid FastAPI route conflicts
    sanitized_path = route.path.replace('/', '_').replace('{', '').replace('}', '')
    route_handler.__name__ = f'handle_{route.function_name}_{sanitized_path}'

    app.api_route(
        route.path,
        methods=all_methods,
        name=route_handler.__name__,
    )(route_handler)

"""CLI commands for local Lambda execution.

Provides:
- `easysam local .` — start local HTTP server
- `easysam local invoke <function>` — invoke a single function with a custom event
"""

import asyncio
import json
import logging as lg
import os
import sys
from pathlib import Path

import click

from easysam.load import resources as load_resources
from easysam.local_handler import MockLambdaContext, load_and_invoke
from easysam.local_server import create_app


def _parse_json_option(value: str | None, param_name: str) -> dict:
    """Parse a JSON option that can be a file path or inline JSON string.

    Returns {} if value is None.
    """
    if value is None:
        return {}

    # Try as file path first
    path = Path(value)
    if path.exists() and path.is_file():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            raise click.BadParameter(f'Invalid JSON in file {value}: {e}', param_hint=param_name)

    # Try as inline JSON
    try:
        result = json.loads(value)
        if not isinstance(result, dict):
            raise click.BadParameter(f'{param_name} must be a JSON object, got {type(result).__name__}')
        return result
    except json.JSONDecodeError as e:
        raise click.BadParameter(
            f'"{value}" is neither a valid file path nor valid JSON: {e}', param_hint=param_name
        )


@click.group(name='local', help='Run Lambda functions locally', invoke_without_command=True)
@click.pass_context
@click.option('--port', type=int, default=3000, help='Port to listen on')
@click.option('--host', type=str, default='127.0.0.1', help='Host to bind to')
@click.option(
    '--event-format',
    type=click.Choice(['v1', 'v2']),
    default='v1',
    help='API Gateway event format (v1=REST API, v2=HTTP API)',
)
@click.option(
    '--auth-context',
    type=str,
    default=None,
    help='Auth context: JSON file path or inline JSON string (injected into requestContext.authorizer)',
)
@click.option(
    '--directory', '-d',
    type=click.Path(exists=True, path_type=Path),
    default='.',
    help='Project directory (default: current directory)',
)
def local(ctx, directory, port, host, event_format, auth_context):
    """Start a local HTTP server that mocks API Gateway routing."""
    ctx.ensure_object(dict)
    # Store params for subcommands
    ctx.obj['local_params'] = {
        'directory': directory,
        'port': port,
        'host': host,
        'event_format': event_format,
        'auth_context': auth_context,
    }

    if ctx.invoked_subcommand is not None:
        return

    # Parse auth context
    auth_ctx = _parse_json_option(auth_context, '--auth-context')

    # Load resources
    deploy_ctx = ctx.obj.get('deploy_ctx', {'environment': 'dev', 'target_region': 'us-east-1'})
    errors = []
    resources_data = load_resources(directory, [], deploy_ctx, errors)

    if errors:
        for e in errors:
            lg.error(e)
        sys.exit(1)

    # Set global envvars
    for key, value in resources_data.get('envvars', {}).items():
        os.environ[key] = str(value)

    # Create app and run
    app = create_app(resources_data, directory, event_format, auth_ctx)

    import uvicorn

    lg.info(f'Starting local server on {host}:{port} (event format: {event_format})')
    uvicorn.run(app, host=host, port=port)


@local.command(name='invoke', help='Invoke a Lambda function locally with a custom event')
@click.pass_context
@click.argument('function_name', type=str)
@click.option(
    '--event',
    type=str,
    default=None,
    help='Event: JSON file path or inline JSON string (default: {})',
)
def invoke_cmd(ctx, function_name, event):
    """Invoke a single Lambda function with a custom event."""
    local_params = ctx.obj.get('local_params', {})
    directory = Path(local_params.get('directory', '.'))

    # Parse event
    event_data = _parse_json_option(event, '--event')

    # Load resources
    deploy_ctx = ctx.obj.get('deploy_ctx', {'environment': 'dev', 'target_region': 'us-east-1'})
    errors = []
    resources_data = load_resources(directory, [], deploy_ctx, errors)

    if errors:
        for e in errors:
            lg.error(e)
        sys.exit(1)

    # Resolve function
    functions = resources_data.get('functions', {})
    if function_name not in functions:
        available = list(functions.keys())
        lg.error(f"Function '{function_name}' not found. Available: {available}")
        sys.exit(1)

    func_config = functions[function_name]
    lambda_dir = Path(directory) / func_config['uri']

    # Set global envvars
    for key, value in resources_data.get('envvars', {}).items():
        os.environ[key] = str(value)

    # Set per-function envvars
    for key, value in func_config.get('envvars', {}).items():
        os.environ[key] = str(value)

    # Invoke
    context = MockLambdaContext(function_name=function_name)
    result = asyncio.run(load_and_invoke(Path(directory), lambda_dir, event_data, context))

    # Output
    click.echo(json.dumps(result, indent=2, default=str))

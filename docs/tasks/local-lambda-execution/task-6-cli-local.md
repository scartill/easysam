# Task 6: CLI `local` Command

- [ ] Complete

## Objective

Add `easysam local .` command that starts the local server.

## Implementation

Create `src/easysam/local_cli.py` with a Click group, then wire into `cli.py`.

### Click group: `local`

```python
@click.group(name='local', help='Run Lambda functions locally', invoke_without_command=True)
@click.pass_context
@click.argument('directory', type=click.Path(exists=True, path_type=Path), default='.')
@click.option('--port', type=int, default=3000, help='Port to listen on')
@click.option('--host', type=str, default='127.0.0.1', help='Host to bind to')
@click.option('--event-format', type=click.Choice(['v1', 'v2']), default='v1', help='API Gateway event format')
@click.option('--auth-context', type=str, default=None, help='Auth context: JSON file path or inline JSON string')
def local(ctx, directory, port, host, event_format, auth_context):
    """Start a local HTTP server that mocks API Gateway routing."""
    if ctx.invoked_subcommand is not None:
        # Store params for subcommands
        ctx.obj['local_params'] = { ... }
        return

    # Parse auth_context
    auth_ctx = parse_auth_context(auth_context)  # {} if None
    
    # Load resources
    deploy_ctx = ctx.obj.get('deploy_ctx')
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
    uvicorn.run(app, host=host, port=port)
```

### `parse_auth_context(value: str | None) -> dict`

- If `value` is `None`: return `{}`
- If `value` is a path to an existing file: read and parse JSON
- Otherwise: parse `value` as inline JSON string
- On parse error: raise `click.BadParameter`

### Wire into `cli.py`

In `cli.py`, add:
```python
from easysam.local_cli import local
# In main():
easysam.add_command(local)
```

## Files to Create/Modify

- `src/easysam/local_cli.py` (create)
- `src/easysam/cli.py` (modify — add `local` command registration)

## Test

- `uv run easysam local --help` shows options including `--port`, `--host`, `--event-format`, `--auth-context`
- `uv run easysam local invoke --help` shows the invoke subcommand

## Demo

```bash
uv run easysam --environment dev local . --port 3000 --auth-context '{"principalId": "debug_principal"}'
```

## Dependencies

- Task 1 (fastapi/uvicorn)
- Task 5 (`create_app`)
- Uses `easysam.load.resources` (existing)

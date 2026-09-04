# Task 7: CLI `local invoke` Command

- [ ] Complete

## Objective

Add `easysam local invoke <function> --event <file_or_json>` for non-HTTP trigger testing.

## Implementation

Add `invoke` subcommand to the `local` group in `src/easysam/local_cli.py`:

```python
@local.command(name='invoke', help='Invoke a Lambda function locally with a custom event')
@click.pass_context
@click.argument('function_name', type=str)
@click.option('--event', type=str, default=None, help='Event: JSON file path or inline JSON string (default: {})')
def invoke_cmd(ctx, function_name, event):
    """Invoke a single Lambda function with a custom event."""
    # Parse event
    event_data = parse_event(event)  # {} if None
    
    # Load resources
    deploy_ctx = ctx.obj.get('deploy_ctx')
    directory = ctx.obj['local_params']['directory']
    errors = []
    resources_data = load_resources(directory, [], deploy_ctx, errors)
    if errors:
        for e in errors:
            lg.error(e)
        sys.exit(1)
    
    # Resolve function
    functions = resources_data.get('functions', {})
    if function_name not in functions:
        lg.error(f"Function '{function_name}' not found. Available: {list(functions.keys())}")
        sys.exit(1)
    
    lambda_dir = directory / functions[function_name]['uri']
    context = MockLambdaContext(function_name=function_name)
    
    # Invoke (run async in sync context)
    result = asyncio.run(load_and_invoke(directory, lambda_dir, event_data, context))
    
    # Output
    click.echo(json.dumps(result, indent=2, default=str))
```

### `parse_event(value: str | None) -> dict`

- If `value` is `None`: return `{}`
- If `value` is a path to an existing file: read and parse JSON from file
- Otherwise: parse `value` as inline JSON string
- On parse error: raise `click.BadParameter`

### Handling `--event` parsing edge cases

- File path: `--event tests/fixtures/stream-event.json`
- Inline JSON: `--event '{"Records": [...]}'`
- Omitted: defaults to `{}`

## Files to Modify

- `src/easysam/local_cli.py` (add `invoke` subcommand)

## Test Fixtures

Create `tests/fixtures/stream-event.json`:
```json
{
  "Records": [
    {
      "eventID": "1",
      "eventName": "INSERT",
      "dynamodb": {
        "Keys": {"ItemID": {"S": "test-123"}},
        "NewImage": {"ItemID": {"S": "test-123"}, "data": {"S": "hello"}}
      }
    }
  ]
}
```

## Test

- Invoke with file path: verify stdout contains expected handler response
- Invoke with inline JSON: verify same behavior
- Invoke with no `--event`: verify handler receives `{}`
- Invoke with unknown function name: verify error message and exit code 1
- Verify output uses `json.dumps(result, indent=2, default=str)` (test with handler returning `Decimal` or `datetime`)

## Demo

```bash
uv run easysam --environment dev local invoke myfunction --event tests/fixtures/stream-event.json
uv run easysam --environment dev local invoke myfunction --event '{"key": "value"}'
uv run easysam --environment dev local invoke myfunction
```

## Dependencies

- Task 2 (`load_and_invoke`, `MockLambdaContext`)
- Task 6 (`local` group must exist for subcommand registration)

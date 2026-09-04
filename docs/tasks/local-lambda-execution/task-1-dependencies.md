# Task 1: Add FastAPI + uvicorn Dependencies

- [ ] Complete

## Objective

Add `fastapi` and `uvicorn[standard]` to project dependencies.

## Implementation

Update `pyproject.toml` dependencies list to include:

```toml
"fastapi>=0.115.0",
"uvicorn[standard]>=0.30.0",
```

Run `uv sync` to install.

## Files to Modify

- `pyproject.toml`

## Test

- `uv sync` succeeds without errors
- `python -c "import fastapi; import uvicorn"` exits 0

## Demo

```bash
uv sync && python -c "import fastapi; import uvicorn"
```

## Dependencies

None — this task has no dependencies on other tasks.

"""Tests for local_handler module isolation and invocation."""

import asyncio
from pathlib import Path

import pytest

from easysam.local_handler import MockLambdaContext, load_and_invoke


def test_isolated_handler_no_cross_contamination(tmp_path: Path):
    """Two lambdas with same-named helpers must not leak state between invocations."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    # Lambda A — returns 'alpha'
    lambda_a = project_root / "lambda_a"
    lambda_a.mkdir()
    (lambda_a / "helpers.py").write_text("VALUE = 'alpha'\n")
    (lambda_a / "index.py").write_text(
        "import helpers\n\ndef handler(event, context):\n    return {'value': helpers.VALUE}\n"
    )

    # Lambda B — returns 'beta'
    lambda_b = project_root / "lambda_b"
    lambda_b.mkdir()
    (lambda_b / "helpers.py").write_text("VALUE = 'beta'\n")
    (lambda_b / "index.py").write_text(
        "import helpers\n\ndef handler(event, context):\n    return {'value': helpers.VALUE}\n"
    )

    ctx = MockLambdaContext(function_name="test")

    result_a = asyncio.run(load_and_invoke(project_root, lambda_a, {}, ctx))
    result_b = asyncio.run(load_and_invoke(project_root, lambda_b, {}, ctx))

    assert result_a == {"value": "alpha"}
    assert result_b == {"value": "beta"}


def test_async_handler(tmp_path: Path):
    """An async handler should be awaited correctly."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    lambda_dir = project_root / "async_lambda"
    lambda_dir.mkdir()
    (lambda_dir / "index.py").write_text(
        "async def handler(event, context):\n    return {'statusCode': 200}\n"
    )

    ctx = MockLambdaContext(function_name="async_test")
    result = asyncio.run(load_and_invoke(project_root, lambda_dir, {}, ctx))

    assert result == {"statusCode": 200}


def test_mock_lambda_context():
    """MockLambdaContext should populate all expected fields."""
    ctx = MockLambdaContext(function_name="my-func")

    assert ctx.function_name == "my-func"
    assert ctx.memory_limit_in_mb == 128
    assert "my-func" in ctx.invoked_function_arn
    assert ctx.aws_request_id  # non-empty UUID string
    assert ctx.log_group_name == "/aws/lambda/local"
    assert "my-func" in ctx.log_stream_name
    assert ctx.get_remaining_time_in_millis() == 300000

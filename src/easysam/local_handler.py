"""Local Lambda handler loading with module isolation."""

import importlib.util
import inspect
import sys
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MockLambdaContext:
    """Minimal mock of the AWS Lambda context object for local invocation."""

    function_name: str
    memory_limit_in_mb: int = 128
    invoked_function_arn: str = field(default="")
    aws_request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    log_group_name: str = "/aws/lambda/local"
    log_stream_name: str = field(default="")

    def __post_init__(self) -> None:
        if not self.invoked_function_arn:
            self.invoked_function_arn = (
                f"arn:aws:lambda:us-east-1:123456789012:function:{self.function_name}"
            )
        if not self.log_stream_name:
            self.log_stream_name = f"local/{self.function_name}/{uuid.uuid4().hex[:8]}"

    def get_remaining_time_in_millis(self) -> int:
        """Return simulated remaining execution time."""
        return 300000


@contextmanager
def isolated_import_context(project_root: Path, lambda_dir: Path):
    """Context manager that temporarily adjusts sys.path and cleans up loaded modules on exit.

    Resolves paths to absolute for reliable module file matching.
    Also removes any 'common.*' modules on entry to ensure fresh resolution.
    """
    project_root_abs = str(project_root.resolve())
    lambda_dir_abs = str(lambda_dir.resolve())

    # Remove stale local modules (including common.*) before import
    # This handles cross-test pollution where common.utils from another project is cached
    for name in list(sys.modules.keys()):
        if name.startswith('common'):
            mod = sys.modules[name]
            if mod is None:
                del sys.modules[name]
                continue
            mod_file = getattr(mod, '__file__', None)
            if mod_file and mod_file.startswith(project_root_abs):
                del sys.modules[name]
            elif mod_file and not mod_file.startswith(project_root_abs):
                # Stale common module from a different project — remove it
                del sys.modules[name]

    original_path = sys.path.copy()
    sys.path = [lambda_dir_abs, project_root_abs] + sys.path
    try:
        yield
    finally:
        sys.path = original_path
        for name, module in list(sys.modules.items()):
            if module is None:
                continue
            module_file = getattr(module, "__file__", None)
            if module_file is None:
                continue
            if module_file.startswith(project_root_abs) or module_file.startswith(
                lambda_dir_abs
            ):
                del sys.modules[name]


async def load_and_invoke(
    project_root: Path, lambda_dir: Path, event: dict, context
) -> dict:
    """Load a Lambda handler from lambda_dir/index.py and invoke it with isolation."""
    handler_path = lambda_dir / "index.py"
    module_name = f"_easysam_local_{uuid.uuid4().hex[:8]}"

    with isolated_import_context(project_root, lambda_dir):
        spec = importlib.util.spec_from_file_location(module_name, handler_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        handler = module.handler

        if inspect.iscoroutinefunction(handler):
            result = await handler(event, context)
        else:
            result = handler(event, context)

    return result

from dataclasses import dataclass
from pathlib import Path


@dataclass
class RouteInfo:
    path: str              # FastAPI route path (e.g., '/items', '/items/{path:path}')
    function_name: str     # Lambda function name
    lambda_dir: Path       # Absolute path to lambda source directory
    is_greedy: bool        # Whether this is a catch-all route
    is_function_url: bool  # Whether this is a /__fn/ route
    resource_path: str     # Original EasySAM path template (for event building)


def build_routes(resources_data: dict, project_root: Path) -> list[RouteInfo]:
    """Build a sorted list of RouteInfo from resolved resources data."""
    routes: list[RouteInfo] = []
    functions = resources_data.get('functions', {})
    paths = resources_data.get('paths', {})

    # Process API Gateway paths
    for path_key, entry in paths.items():
        if entry.get('integration') == 'lambda' or 'function' in entry:
            function_name = entry['function']
            uri = functions[function_name]['uri']
            lambda_dir = project_root / uri

            greedy = entry.get('greedy', False) or path_key.endswith('/')

            if greedy:
                # Normalize: strip trailing slash for the exact route
                api_path = path_key.rstrip('/')

                # Add exact route
                routes.append(RouteInfo(
                    path=api_path,
                    function_name=function_name,
                    lambda_dir=lambda_dir,
                    is_greedy=False,
                    is_function_url=False,
                    resource_path=api_path,
                ))

                # Add catch-all route
                routes.append(RouteInfo(
                    path=f'{api_path}/{{path:path}}',
                    function_name=function_name,
                    lambda_dir=lambda_dir,
                    is_greedy=True,
                    is_function_url=False,
                    resource_path=f'{api_path}/{{proxy+}}',
                ))
            else:
                # Single non-greedy route
                routes.append(RouteInfo(
                    path=path_key,
                    function_name=function_name,
                    lambda_dir=lambda_dir,
                    is_greedy=False,
                    is_function_url=False,
                    resource_path=path_key,
                ))

    # Process function URLs
    for name, func_config in functions.items():
        if func_config.get('functionurl'):
            uri = func_config['uri']
            lambda_dir = project_root / uri
            routes.append(RouteInfo(
                path=f'/__fn/{name}',
                function_name=name,
                lambda_dir=lambda_dir,
                is_greedy=False,
                is_function_url=True,
                resource_path=f'/__fn/{name}',
            ))

    # Sort: non-greedy routes first, greedy catch-all routes last
    routes.sort(key=lambda r: r.is_greedy)

    return routes

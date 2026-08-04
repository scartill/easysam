from pathlib import Path
from easysam.local_routes import build_routes

def test_build_routes_basic():
    resources_data = {
        'functions': {
            'listfunc': {'uri': 'backend/function/listfunc'},
            'getfunc': {'uri': 'backend/function/getfunc'},
        },
        'paths': {
            '/items': {'function': 'listfunc', 'greedy': False, 'integration': 'lambda', 'open': True},
            '/proxy': {'function': 'getfunc', 'greedy': True, 'integration': 'lambda', 'open': True},
        }
    }
    project_root = Path('/project')
    routes = build_routes(resources_data, project_root)

    # Should have 3 routes: /items, /proxy (exact), /proxy/{path:path} (greedy)
    assert len(routes) == 3

    # Non-greedy routes come first
    non_greedy = [r for r in routes if not r.is_greedy]
    greedy = [r for r in routes if r.is_greedy]
    assert len(non_greedy) == 2
    assert len(greedy) == 1

    # Verify greedy route comes last
    assert routes[-1].is_greedy
    assert routes[-1].path == '/proxy/{path:path}'
    assert routes[-1].resource_path == '/proxy/{proxy+}'

def test_build_routes_function_url():
    resources_data = {
        'functions': {
            'hello': {'uri': 'backend/function/hello', 'functionurl': True},
        },
        'paths': {}
    }
    project_root = Path('/project')
    routes = build_routes(resources_data, project_root)

    assert len(routes) == 1
    assert routes[0].path == '/__fn/hello'
    assert routes[0].is_function_url
    assert routes[0].function_name == 'hello'

def test_build_routes_empty():
    resources_data = {'functions': {}, 'paths': {}}
    routes = build_routes(resources_data, Path('/project'))
    assert routes == []

def test_build_routes_sorting_order():
    """Verify exact routes always come before greedy routes."""
    resources_data = {
        'functions': {
            'a': {'uri': 'src/a'},
            'b': {'uri': 'src/b'},
            'c': {'uri': 'src/c'},
        },
        'paths': {
            '/z': {'function': 'a', 'greedy': True, 'integration': 'lambda', 'open': True},
            '/a': {'function': 'b', 'greedy': False, 'integration': 'lambda', 'open': True},
            '/m': {'function': 'c', 'greedy': True, 'integration': 'lambda', 'open': True},
        }
    }
    routes = build_routes(resources_data, Path('/project'))

    # All non-greedy should come before all greedy
    greedy_seen = False
    for r in routes:
        if r.is_greedy:
            greedy_seen = True
        else:
            assert not greedy_seen, 'Non-greedy route found after greedy route'

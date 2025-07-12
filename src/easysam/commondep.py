import logging as lg
from pathlib import Path
import ast


def commondep(common_base, target_dir):
    common_base = Path(common_base)
    target_dir = Path(target_dir)
    commons = find_commons(common_base)

    lg.debug(f'Commons: {commons}')
    common_imports = find_common_deps(target_dir, common_base, commons, set())
    return sorted(list(common_imports))


def find_commons(common_base):
    commons = []

    for item in common_base.iterdir():
        if item.is_dir():
            commons.append(item.name)

    for item in common_base.glob('*.py'):
        commons.append(item.stem)

    return list(sorted(filter(lambda x: not x.startswith('_'), commons)))


def is_common_package(name: str, commons: list[str]) -> str | None:
    split = name.split('.')

    if len(split) < 2:
        return None

    if split[0] != 'common':
        return None

    if split[1] not in commons:
        return None

    return split[1]


def find_common_deps_in_file(target_file, common_base, commons, common_imports):
    lg.debug(f'Processing {target_file}')
    file_imports = set()
    target_code = target_file.read_text()
    target_ast = ast.parse(target_code)

    for stmt in target_ast.body:
        if isinstance(stmt, ast.Import):
            for name in sorted(stmt.names, key=lambda x: x.name):
                lg.debug(f'Found import "{name.name}" in {target_file}')

                if package := is_common_package(name.name, commons):
                    lg.debug(f'Adding "{package}" to file imports')
                    file_imports.add(package)

        if isinstance(stmt, ast.ImportFrom):
            lg.debug(f'Found import from "{stmt.module}" in {target_file}')

            if stmt.module:
                if package := is_common_package(stmt.module, commons):
                    lg.debug(f'Adding "{package}" to file imports')
                    file_imports.add(package)

    lg.debug(f'File imports: {target_file}: {file_imports}')
    new_imports = set(file_imports) - common_imports
    common_imports.update(new_imports)
    lg.debug(f'Common imports: {common_imports}')
    lg.debug(f'New imports: {new_imports}')

    for file_import in sorted(list(new_imports)):
        dep_file = common_base / file_import

        if not dep_file.is_dir():
            dep_file = dep_file.with_suffix('.py')
            lg.debug(f'Processing nested file {dep_file}')
            find_common_deps_in_file(dep_file, common_base, commons, common_imports)
        else:
            lg.debug(f'Processing nested directory {dep_file}')
            find_common_deps(dep_file, common_base, commons, common_imports)


def find_common_deps(target, common_base, commons, common_imports):
    target_files = sorted(target.glob('**/*.py'), key=lambda x: str(x))
    lg.debug(f'For target {target} files are: {target_files}')

    for target_file in target_files:
        find_common_deps_in_file(target_file, common_base, commons, common_imports)

    return common_imports

from pathlib import Path
import logging as lg

import prismarine.prisma_client as client


def generate(directory: Path, resources: dict, errors: list[str]):
    prisma = resources['prismarine']

    if not prisma:
        return

    prisma_base = prisma.get('default-base')
    prisma_tables = prisma['tables'] or []
    access_module = prisma.get('access-module') or 'prismarine.runtime.dynamo_default'
    extra_imports_def = prisma.get('extra-imports')

    if extra_imports_def:
        extra_imports = [i.split(':') for i in extra_imports_def]

        lg.info('Prismarine imports collected')
        for i in extra_imports:
            lg.info(f'Class {i[0]}:{i[1]}')

    else:
        extra_imports = []
        lg.info('No extra prismarine imports')

    for prisma_integration in prisma_tables:
        base = prisma_integration.get('base') or prisma_base
        package = prisma_integration.get('package')
        base_dir = Path(directory, base)

        if not base:
            errors.append(f'No base found for {package}')
            continue

        if not package:
            errors.append(f'No package found for {base}')
            continue

        cluster = client.get_cluster(base_dir, package)

        if not cluster.prefix.startswith(resources['prefix']):
            errors.append(
                f'When using with EasySAM, a Prismarine Cluster prefix ({cluster.prefix}) must start with the master prefix ({resources["prefix"]})'
            )
            continue

        content = client.build_client(
            cluster, base_dir, base, access_module,
            extra_imports=extra_imports
        )

        if not errors:
            client.write_client(content, base_dir, package)
        else:
            lg.warning(f'Not writing client for {package} due to errors')

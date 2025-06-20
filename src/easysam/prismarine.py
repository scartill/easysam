from pathlib import Path

import prismarine.prisma_client as client


def generate(directory, resources):
    prisma = resources['prismarine']

    if not prisma:
        return

    prisma_base = prisma.get('default-base')
    prisma_tables = prisma['tables'] or []
    access_module = prisma.get('access-module') or 'prismarine.runtime.dynamo_default'

    for prisma_integration in prisma_tables:
        base = prisma_integration.get('base') or prisma_base
        package = prisma_integration.get('package')
        base_dir = Path(directory, base)

        if not base:
            raise UserWarning(f'No base found for {package}')

        if not package:
            raise UserWarning(f'No package found for {base}')

        cluster = client.get_cluster(base_dir, package)

        if not cluster.prefix.startswith(resources['prefix']):
            raise UserWarning(
                f'When using with EasySAM, a Prismarine Cluster prefix ({cluster.prefix}) must start with the master prefix ({resources["prefix"]})'
            )

        content = client.build_client(
            cluster, base_dir, base, access_module
        )

        client.write_client(content, base_dir, package)

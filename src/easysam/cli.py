from pathlib import Path
import logging as lg
import sys
from importlib.metadata import version
import traceback
from argparse import ArgumentParser

from benedict import benedict
import click
from rich.logging import RichHandler

from easysam.generate import generate
from easysam.deploy import deploy, delete
from easysam.deploy import remove_common_dependencies
from easysam.init import init

from easysam.inspect import inspect


@click.group(
    help='EasySAM is a tool for generating SAM templates from simple YAML files'
)
@click.version_option(version('easysam'))
@click.pass_context
@click.option('--aws-profile', type=str, help='AWS profile to use')
@click.option(
    '--with-context',
    'with_contexts',
    multiple=True,
    type=click.Path(exists=True, path_type=Path, dir_okay=False),
    help='A YAML file containing a default context for deployments. The context can override target_profile, target_region and environment. It can also be used to override resources.yaml properties. Can be used multiple times to deploy to multiple contexts.',  # noqa: E501
)
@click.option(
    '--target-region',
    type=str,
    help='A region to use for generation'
)
@click.option(
    '--environment',
    type=str,
    help='An environment (AWS stack) to use in generation',
    default='dev',
)
@click.option('--verbose', is_flag=True)
def easysam(
    ctx,
    verbose,
    aws_profile,
    with_contexts,
    target_region,
    environment,
):
    default_deploy_ctx = benedict({
        'target_profile': aws_profile,
        'target_region': target_region,
        'environment': environment,
    })

    ctx.obj = {
        'verbose': verbose,
        'aws_profile': aws_profile,
        'default_deploy_ctx': default_deploy_ctx,
    }

    lg.basicConfig(
        level=lg.DEBUG if verbose else lg.INFO,
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    lg.debug(f'Verbose: {verbose}')

    if with_contexts:
        ctx.obj['deploy_ctxs'] = []

        for with_context in with_contexts:
            deploy_ctx = default_deploy_ctx.copy()

            deploy_ctx.update(
                benedict.from_yaml(with_context)
            )

            ctx.obj['deploy_ctxs'].append(deploy_ctx)
            lg.info(f'Loaded context from {with_context}')
    else:
        ctx.obj['deploy_ctxs'] = [ctx.obj['default_deploy_ctx']]

    lg.info('Deployment contexts:')

    for deploy_ctx in ctx.obj['deploy_ctxs']:
        name = deploy_ctx.get("name", "default")
        lg.info(f'\n--- {name} ---\n{deploy_ctx.to_yaml(indent=4)}')


@easysam.command(
    name='generate',
    help='Generate a SAM template from a directory',
)
@click.pass_obj
@click.option(
    '--path', multiple=True, help='A additional Python path to use for generation'
)
@click.argument('directory', type=click.Path(exists=True))
def generate_cmd(obj, directory, path):
    directory = Path(directory)
    obj['pypath'] = [Path(p) for p in path]
    deploy_ctxs = obj.get('deploy_ctxs')
    resources_set, errors = generate(obj, directory, deploy_ctxs)

    if errors:
        for error in errors:
            lg.error(error)

        if len(errors) > 1:
            lg.error(f'There were {len(errors)} errors:')
        else:
            lg.error('There was an error')

        sys.exit(1)

    else:
        click.echo(resources_set.to_yaml())
        lg.info('Resources generated successfully')
        sys.exit(0)


@easysam.command(name='deploy', help='Deploy the application to an AWS environment')
@click.pass_obj
@click.option('--tag', type=str, multiple=True, help='AWS Tags')
@click.option('--dry-run', is_flag=True, help='Dry run the deployment')
@click.option('--sam-tool', type=str, help='Path to the SAM CLI', default='uv run sam')
@click.option(
    '--no-cleanup', is_flag=True, help='Do not clean the directory before deploying'
)
@click.option(
    '--override-main-template',
    type=click.Path(exists=True, path_type=Path),
    help='Override the main template',
)
@click.argument('directory', type=click.Path(exists=True, path_type=Path))
def deploy_cmd(obj, directory, **kwargs):
    obj.update(kwargs)  # noqa: F821
    deploy_ctx = obj.get('deploy_ctx')
    deploy(obj, directory, deploy_ctx)


@easysam.command(name='delete', help='Delete the environment from AWS')
@click.pass_obj
@click.option('--force', is_flag=True, help='Force delete the environment')
@click.option(
    '--await', 'await_deletion', is_flag=True, help='Await the deletion to complete'
)
def delete_cmd(obj, **kwargs):
    obj.update(kwargs)  # noqa: F821
    environment = obj.get('deploy_ctx').get('environment')
    delete(obj, environment)


@easysam.command(name='cleanup', help='Remove common dependencies from the directory')
@click.pass_obj
@click.argument('directory', type=click.Path(exists=True))
def cleanup_cmd(obj, directory):
    remove_common_dependencies(directory)


@easysam.command(
    name='init',
    help='Initialize a new application in the current directory (requires uv init to be run first)',
)
@click.pass_obj
@click.option(
    '--prismarine',
    is_flag=True,
    help='Scaffold a minimal application with Prismarine support',
)
def init_cmd(obj, prismarine):
    init(obj, prismarine=prismarine)


def main():
    try:
        easysam.add_command(inspect)
        easysam()

    except UserWarning as e:
        parser = ArgumentParser()
        parser.add_argument('--verbose', action='store_true')
        args, _ = parser.parse_known_args()

        if args.verbose:
            lg.error(traceback.format_exc())

        lg.error(e)
        sys.exit(1)

    except Exception as e:
        lg.error(traceback.format_exc())
        lg.error(f'An unexpected error occurred: {e}')
        sys.exit(2)


if __name__ == '__main__':
    main()

from pathlib import Path
import logging as lg
import sys
from importlib.metadata import version
import traceback
from argparse import ArgumentParser

import click
import yaml

from easysam.generate import generate
from easysam.deploy import deploy, delete
from easysam.deploy import remove_common_dependencies
from easysam.init import init

from easysam.inspect import inspect


@click.group(help='EasySAM is a tool for generating SAM templates from simple YAML files')
@click.version_option(version('easysam'))
@click.pass_context
@click.option(
    '--aws-profile', type=str, help='AWS profile to use'
)
@click.option(
    '--context-file', type=click.Path(exists=True),
    help='A YAML file containing additional context for the resources.yaml file. '
         'For example, overrides for resource properties.'
)
@click.option('--verbose', is_flag=True)
def easysam(ctx, verbose, aws_profile, context_file):
    ctx.obj = {
        'verbose': verbose,
        'aws_profile': aws_profile,
        'deploy_ctx': {}
    }

    if context_file:
        ctx.obj['context_file'] = Path(context_file)

    lg.basicConfig(level=lg.DEBUG if verbose else lg.INFO)
    lg.debug(f'Verbose: {verbose}')


@easysam.command(name='generate', help='Generate a SAM template from a directory')
@click.pass_obj
@click.option(
    '--path', multiple=True, help='A additional Python path to use for generation'
)
@click.option(
    '--environment', type=str, help='An environment (AWS stack) to use in generation'
)
@click.option(
    '--region', type=str, help='A region to use for generation'
)
@click.argument('directory', type=click.Path(exists=True))
def generate_cmd(obj, directory, path, environment, region):
    directory = Path(directory)
    pypath = [Path(p) for p in path]

    deploy_ctx = {}

    if environment:
        deploy_ctx['environment'] = environment

    if region:
        deploy_ctx['region'] = region

    context_file = obj.get('context_file')
    resources_data, errors = generate(directory, pypath, deploy_ctx, context_file)

    if errors:
        for error in errors:
            lg.error(error)

        if len(errors) > 1:
            lg.error(f'There were {len(errors)} errors:')
        else:
            lg.error('There was an error')

        sys.exit(1)

    else:
        click.echo(yaml.dump(resources_data, indent=4))
        lg.info('Resources generated successfully')
        sys.exit(0)


@easysam.command(name='deploy', help='Deploy the application to an AWS environment')
@click.pass_obj
@click.option(
    '--tag', type=str, multiple=True, help='AWS tags', required=True
)
@click.option(
    '--dry-run', is_flag=True, help='Dry run the deployment'
)
@click.option(
    '--sam-tool', type=str, help='Path to the SAM CLI', default='uv run sam'
)
@click.option(
    '--no-cleanup', is_flag=True, help='Do not clean the directory before deploying'
)
@click.argument('directory', type=click.Path(exists=True))
@click.argument('environment', type=str)
def deploy_cmd(obj, directory, environment, **kwargs):
    obj.update(kwargs)  # noqa: F821
    directory = Path(directory)
    context_file = obj.get('context_file')
    deploy(obj, directory, environment, context_file)


@easysam.command(name='delete', help='Delete the environment from AWS')
@click.pass_obj
@click.option('--force', is_flag=True, help='Force delete the environment')
@click.argument('environment', type=str)
def delete_cmd(obj, environment, force, **kwargs):
    obj.update(kwargs)  # noqa: F821
    delete(obj, environment, force)


@easysam.command(name='cleanup', help='Remove common dependencies from the directory')
@click.pass_obj
@click.argument('directory', type=click.Path(exists=True))
def cleanup_cmd(obj, directory):
    remove_common_dependencies(directory)


@easysam.command(name='init', help='Initialize a new application in a given directory')
@click.pass_obj
@click.argument('app-name', type=click.Path(exists=False))
def init_cmd(obj, app_name):
    init(obj, app_name)


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

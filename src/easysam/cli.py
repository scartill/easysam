from pathlib import Path
import click
import logging as lg
import sys


from easysam.generate import generate
from easysam.deploy import deploy, delete
from easysam.deploy import remove_common_dependencies
from easysam.init import init

from easysam.inspect import inspect


@click.group(help='EasySAM is a tool for generating SAM templates from simple YAML files')
@click.pass_context
@click.option('--aws-profile', type=str, help='AWS profile to use')
@click.option('--verbose', is_flag=True)
def easysam(ctx, verbose, aws_profile):
    ctx.obj = {'verbose': verbose, 'aws_profile': aws_profile}
    lg.basicConfig(level=lg.DEBUG if verbose else lg.INFO)
    lg.debug(f'Verbose: {verbose}')


@easysam.command(name='generate', help='Generate a SAM template from a directory')
@click.option('--path', multiple=True)
@click.option('--preprocess-only', is_flag=True, default=False)
@click.argument('directory', type=click.Path(exists=True))
def generate_cmd(directory, path, preprocess_only):
    generate(directory, path, preprocess_only)


@easysam.command(name='deploy', help='Deploy the application to an AWS stack')
@click.pass_obj
@click.option(
    '--region', type=str, help='AWS region'
)
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
@click.argument('stack', type=str)
def deploy_cmd(obj, directory, stack, **kwargs):
    obj.update(kwargs)
    directory = Path(directory)
    deploy(obj, directory, stack)


@easysam.command(name='delete', help='Delete the stack from AWS')
@click.pass_obj
@click.option('--force', is_flag=True, help='Force delete the stack')
@click.option('--region', type=str, help='AWS region')
@click.argument('stack', type=str)
def delete_cmd(obj, stack, force, **kwargs):
    obj.update(kwargs)
    delete(obj, stack, force)


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
        lg.error(e)
        sys.exit(1)

    except Exception as e:
        lg.error(e)
        sys.exit(2)


if __name__ == '__main__':
    main()

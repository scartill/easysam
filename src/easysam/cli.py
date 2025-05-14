import click
import logging as lg
import sys


from easysam.generate import generate_cmd
from easysam.deploy import deploy_cmd


@click.group(help='EasySAM is a tool for generating SAM templates from simple YAML files')
@click.pass_context
@click.option('--verbose', is_flag=True)
def easysam(ctx, verbose):
    ctx.obj = {'verbose': verbose}
    lg.basicConfig(level=lg.DEBUG if verbose else lg.INFO)
    lg.debug(f'Verbose: {verbose}')


def main():
    try:
        easysam.add_command(generate_cmd)
        easysam.add_command(deploy_cmd)
        easysam()

    except UserWarning as e:
        lg.error(e)
        sys.exit(1)


if __name__ == '__main__':
    main()

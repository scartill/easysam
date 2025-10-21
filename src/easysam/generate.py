from pathlib import Path
import traceback
import logging as lg
from typing import cast

from benedict import benedict
from jinja2 import Environment, FileSystemLoader
import yaml
from mergedeep import merge

from easysam.prismarine import generate as generate_prismarine_clients
from easysam.definitions import FatalError, ProcessingResult
from easysam.load import resources as load_resources
from easysam.cloud import scan as scan_cloud


def generate(
    cliparams: dict,
    resources_dir: Path,
    pypath: list[Path],
    deploy_ctx: dict[str, str],
) -> ProcessingResult:
    """
    Generate a SAM template from a directory.

    Args:
        resources_dir: The directory containing the resources.
        pypath: The Python path to use.
        deploy_ctx: The additional deployment context, including:
        - environment: the name of the environment (AWS stack) to deploy to
        - region: the region to deploy to (AWS region)

        A tuple containing the processed resources and any errors as a list.
    """

    try:
        errors = []
        resources_data = load_resources(resources_dir, pypath, deploy_ctx, errors)
        aws_profile = cliparams.get('aws_profile')
        scan_cloud(resources_data, errors, aws_profile)

        lg.debug('Resources processed:\n' + yaml.dump(resources_data, indent=4))

        try:
            build_dir = Path(resources_dir, 'build')
            swagger = Path(build_dir, 'swagger.yaml')
            template = Path(resources_dir, 'template.yml')

            if plugins := resources_data.get('plugins'):
                lg.info('The template has plugins, executing them')

                for plugin_name, plugin in cast(dict, plugins).items():
                    invoke_plugin(
                        resources_dir, resources_data, plugin_name, plugin, errors
                    )

            searchpath = [
                str(Path(__file__).parent.resolve()),
                str(resources_dir.resolve()),
            ]

            template_path = 'template.j2'

            if omt := cliparams.get('override_main_template'):
                lg.info(f'Overriding main template with {omt}')
                template_path = str(omt.name)
                lg.info(f'Adding {omt.parent} to search path')
                searchpath.append(str(omt.parent))

            loader = FileSystemLoader(searchpath=searchpath)
            jenv = Environment(loader=loader)

            sam_template = jenv.get_template(template_path)
            sam_output = sam_template.render(resources_data)

            write_result(template, sam_output)
            lg.info(f'SAM template generated: {template}')

            if resources_data.get('paths'):
                swagger_template = jenv.get_template('swagger.j2')
                swagger_output = swagger_template.render(resources_data)
                write_result(swagger, swagger_output)
                lg.info(f'Swagger file generated: {swagger}')

        except Exception as e:
            if cliparams.get('verbose'):
                traceback.print_exc()

            errors.append(f'Error generating template: {e}')
            return resources_data, errors

        if 'prismarine' in resources_data:
            lg.info('Generating prismarine clients')
            generate_prismarine_clients(resources_dir, resources_data, errors)

        return resources_data, errors

    except FatalError as e:
        return benedict(), e.errors


def invoke_plugin(
    resources_dir: Path,
    resources_data: benedict,
    plugin_name: str,
    plugin: benedict,
    errors: list[str],
):
    template_j2_filename = cast(str, plugin['template'])
    template_j2_path = Path(resources_dir, template_j2_filename)

    if not template_j2_path.exists():
        errors.append(f'Plugin {plugin} has no template file {template_j2_path}')
        return

    lg.info(f'Invoking plugin {plugin} with template {template_j2_path}')
    template_dir = template_j2_path.parent
    loader = FileSystemLoader(searchpath=[str(template_dir.resolve())])
    jenv = Environment(loader=loader)
    template = jenv.get_template(template_j2_filename)
    aux_data = dict(plugin.get('aux', {}))
    output = template.render(merge(resources_data, aux_data))
    output_yaml_path = Path(resources_dir, plugin_name).with_suffix('.yaml')
    write_result(output_yaml_path, output)


def write_result(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    sane_text = '\n'.join(line for line in text.splitlines() if line and line.strip())
    Path(path).write_text(sane_text)

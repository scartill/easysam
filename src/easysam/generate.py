from pathlib import Path
import traceback
import logging as lg
from typing import cast

from benedict import benedict
from jinja2 import Environment, FileSystemLoader
from mergedeep import merge

import easysam.utils as u
from easysam.prismarine import generate as generate_prismarine_clients
from easysam.definitions import FatalError, ProcessingResult
from easysam.load import resources as load_resources


def generate(
    toolparams: dict,
    resources_dir: Path,
    deploy_ctxs: list[benedict],
) -> benedict[str, ProcessingResult]:
    """
    Generate a SAM template from a directory.

    Args:
        resources_dir: The directory containing the resources.
        deploy_ctxs: The deployment contexts, including:
        - target_profile: the AWS profile to use
        - target_region: the AWS region to use
        - environment: the name of the environment (AWS stack) to deploy to

        A tuple containing the processed resources and any errors as a list.

        Note: other deployment contexts can be discovered by inspecting the resources.yaml file.
    """

    try:
        errors = []
        context_names = set()

        for deploy_ctx in deploy_ctxs:
            name = deploy_ctx.get('name', 'default')
            if name in context_names:
                errors.append(
                    f'Deployment context {name} already defined'
                )
                continue

            context_names.add(name)

            if 'name' not in deploy_ctx:
                deploy_ctx['name'] = 'default'

        if errors:
            raise FatalError(errors)

        results = benedict()

        for deploy_ctx in deploy_ctxs:
            resources_data = load_resources(
                toolparams=toolparams,
                resources_dir=resources_dir,
                deploy_ctx=deploy_ctx,
                errors=errors,
            )

            results[deploy_ctx['name']] = _generate_with_context(
                toolparams=toolparams,
                resources_dir=resources_dir,
                resources_data=resources_data,
                deploy_ctx=deploy_ctx,
                errors=errors,
            )

        return results, errors

    except FatalError as e:
        return None, e.errors


def _generate_with_context(
    *,
    toolparams: dict,
    resources_dir: Path,
    resources_data: benedict,
    deploy_ctx: benedict,
    errors: list[str],
) -> ProcessingResult:
    """
    Generate a SAM template from a directory with a specific deployment context.
    """

    lg.debug(f'Resources processed:\n\n{resources_data.to_yaml(indent=4)}')

    try:
        build_dir = u.get_build_dir(resources_dir, deploy_ctx)
        swagger = Path(build_dir, 'swagger.yaml')
        template = Path(build_dir, 'template.yml')

        if plugins := resources_data.get('plugins'):
            lg.info('The template has plugins, executing them')

            for plugin_name, plugin in cast(dict, plugins).items():
                invoke_plugin(
                    resources_dir=resources_dir,
                    resources_data=resources_data,
                    plugin_name=plugin_name,
                    plugin=plugin,
                    build_dir=build_dir,
                    errors=errors,
                )

        searchpath = [
            str(Path(__file__).parent.resolve()),
            str(resources_dir.resolve()),
        ]

        template_path = 'template.j2'

        if omt := toolparams.get('override_main_template'):
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
        if toolparams.get('verbose'):
            traceback.print_exc()

        errors.append(f'Error generating template: {e}')
        return None

    if 'prismarine' in resources_data:
        lg.info('Generating prismarine clients')
        generate_prismarine_clients(resources_dir, resources_data, errors)

    return resources_data


def invoke_plugin(
    *,
    resources_dir: Path,
    build_dir: Path,
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
    output_yaml_path = Path(build_dir, plugin_name).with_suffix('.yaml')
    write_result(output_yaml_path, output)


def write_result(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    sane_text = '\n'.join(line for line in text.splitlines() if line and line.strip())
    Path(path).write_text(sane_text)

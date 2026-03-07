# Plugins Example

This example demonstrates EasySAM plugin rendering with a custom Jinja template.

## What this example demonstrates

- `plugins` section in root `resources.yaml`
- Plugin template input via `aux` values
- Rendering custom SAM fragment to `<plugin-name>.yaml`

`resources.yaml`:

```yaml
plugins:
  myplugin:
    template: customlambda.j2
    aux:
      funname: mycustomfun
```

`customlambda.j2` renders a custom Lambda resource definition.

## Validate and generate

```bash
easysam --environment dev inspect schema example/plugins
easysam --environment dev generate example/plugins
```

After generation, check:

- `template.yml`
- `myplugin.yaml` (plugin output)

## Deploy

```bash
easysam --environment dev --aws-profile my-profile deploy example/plugins
```

## Invoke test script

From `example/plugins`:

```bash
python3 test/invoke_lambda.py --env dev
```

The script invokes `mycustomfun-<env>`.

## Cleanup

```bash
easysam --environment dev --aws-profile my-profile delete --await
```

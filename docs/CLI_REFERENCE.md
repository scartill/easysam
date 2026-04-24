# EasySAM CLI Reference

EasySAM uses a Click command group with global options.

## Syntax

```bash
easysam [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGS]
```

Global options must appear before the command name.

Example:

```bash
easysam --environment dev --aws-profile my-profile deploy . --tag team=platform
```

If you installed EasySAM with `uv add --dev easysam`, use `uv run easysam ...`.

## Global options

| Option | Description | Default |
| --- | --- | --- |
| `--aws-profile TEXT` | AWS named profile for API calls and SAM deploy | none |
| `--context-file PATH` | YAML deploy context (for conditionals/overrides) | none |
| `--target-region TEXT` | AWS region used in deploy context | none |
| `--environment TEXT` | Stack/environment name | `dev` |
| `--verbose` | Enable debug logs | `false` |
| `--version` | Print installed version | n/a |

## Commands

### `init`

Initialize EasySAM files in the current directory.

```bash
easysam init
easysam init --prismarine
```

Notes:

- Requires `pyproject.toml` in the current directory.
- Adds/merges EasySAM entries into `.gitignore`.

### `generate DIRECTORY`

Generate SAM template and optional Swagger output.

```bash
easysam --environment dev generate .
easysam --environment dev generate . --path ../shared-lib
```

Options:

- `--path PATH` (repeatable): additional Python import path(s)
- `--no-docker-build-on-win`: Skip adding Docker build metadata to the template on Windows.

Outputs:

- `template.yml`
- `build/swagger.yaml` (if HTTP paths are defined)

### `deploy DIRECTORY`

Generate, build, and deploy using SAM CLI.

```bash
easysam --environment dev --aws-profile my-profile deploy . --tag project=myapp
```

Options:

- `--tag TEXT` (repeatable): CloudFormation tags (`key=value`)
- `--dry-run`: print SAM deploy command without executing it
- `--sam-tool TEXT`: custom SAM invocation command (default: `uv run sam`)
- `--no-cleanup`: keep copied `common` dependencies after deploy
- `--override-main-template PATH`: use custom Jinja main template
- `--no-docker-build-on-win`: Skip adding Docker build metadata to the template on Windows.

### `delete`

Delete the stack for the selected environment.

```bash
easysam --environment dev --aws-profile my-profile delete
easysam --environment dev --aws-profile my-profile delete --force --await
```

Options:

- `--force`: use `FORCE_DELETE_STACK` deletion mode
- `--await`: wait until deletion is complete

### `cleanup DIRECTORY`

Remove copied `common` dependencies from lambda folders.

```bash
easysam cleanup .
```

### `inspect` commands

#### `inspect schema DIRECTORY`

Validate and render resolved resources.

```bash
easysam --environment dev inspect schema .
easysam --environment dev inspect schema . --select functions.myfunction
```

Options:

- `--path PATH` (repeatable): additional Python path(s)
- `--select TEXT`: keystring selector for a subsection of resolved resources

#### `inspect cloud DIRECTORY`

Validate required cloud resources for deployment.

```bash
easysam --environment dev --aws-profile my-profile inspect cloud .
```

Options:

- `--path PATH` (repeatable): additional Python path(s)

#### `inspect common-deps LAMBDA_DIR`

Show which modules from `common/` are needed by a lambda.

```bash
easysam inspect common-deps backend/function/myfunction
easysam inspect common-deps backend/function/myfunction --common-dir common
```

## Typical workflow

```bash
easysam --environment dev inspect schema .
easysam --environment dev generate .
easysam --environment dev --aws-profile my-profile deploy . --tag project=myapp
```

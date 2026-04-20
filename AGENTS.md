# EasySAM - Project Context

EasySAM is an opinionated YAML-to-SAM generator for modular AWS serverless applications. It allows developers to define complex AWS resource configurations (Lambda, DynamoDB, S3, SQS, Kinesis, etc.) in a compact and modular `resources.yaml` model, which is then used to generate and deploy standard AWS SAM templates.

## Architecture and Core Concepts

- **YAML-First Resource Definition:** Resources are defined in `resources.yaml` (root) and `easysam.yaml` (local modules).
- **Modular Design:** Uses a recursive import system where the root `resources.yaml` imports directories containing their own `easysam.yaml` files.
- **Shared Code:** Support for a `common/` directory to share code across different Lambda functions.
- **Validation Layers:**
  - **Schema Validation:** Ensures the YAML structure matches the project's requirements (defined in `src/easysam/schemas.json`).
  - **Cloud Validation:** Checks resource existence and configurations against the actual AWS environment (defined in `src/easysam/cloud.py`).
- **Templating:** Uses Jinja2 (`template.j2`, `swagger.j2`) to transform the YAML model into AWS SAM and Swagger/OpenAPI templates.
- **Prismarine Integration:** Built-in support for Prismarine model-driven DynamoDB tables and client generation.

## Key Technologies

- **Language:** Python 3.12+
- **Infrastructure as Code:** AWS SAM CLI
- **AWS SDK:** Boto3
- **CLI Framework:** Click
- **Templating Engine:** Jinja2
- **Validation:** jsonschema
- **Dependency Management:** uv
- **Linting & Formatting:** ruff

## Building and Running

### Development Setup
```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Core Commands
```bash
# Initialize a new project
uv run easysam init

# Validate YAML schema
uv run easysam --environment dev inspect schema .

# Validate against AWS cloud
uv run easysam --environment dev --aws-profile my-profile inspect cloud .

# Generate SAM template (template.yml)
uv run easysam --environment dev generate .

# Deploy to AWS
uv run easysam --environment dev --aws-profile my-profile deploy .

# Delete stack from AWS
uv run easysam --environment dev --aws-profile my-profile delete --await
```

## Project Structure

- `src/easysam/`: Core source code.
  - `cli.py`: CLI entry point and command definitions.
  - `generate.py`: Orchestrates the generation of SAM templates.
  - `load.py`: Handles recursive loading and merging of YAML files.
  - `schemas.json`: JSON schema for `resources.yaml` validation.
  - `template.j2`: The main Jinja2 template for SAM.
- `docs/`: Comprehensive documentation.
  - `CLI_REFERENCE.md`: Detailed CLI command usage.
  - `RESOURCE_REFERENCE.md`: Documentation for all supported resource types.
- `example/`: A collection of example applications demonstrating various features (Prismarine, TTL, IoT, etc.).
- `tests/`: Project test suite (run via `pytest`).

## Development Conventions

- **Linting:** Always use `ruff check .` for linting.
- **Formatting:** Always use `ruff format .` for code formatting.
- **Testing:** Add or update tests in `tests/` when modifying core logic. Run tests using `pytest`.
- **Schema Updates:** If adding a new resource type or property, update `src/easysam/schemas.json` and `src/easysam/template.j2`.
- **Documentation:** Ensure any CLI or resource changes are reflected in the files under `docs/`.

<!-- hippo:start -->
## Project Memory (Hippo)

At the start of every task, run:
```bash
hippo context --auto --budget 1500
```
Read the output before writing any code.

On errors or unexpected behaviour:
```bash
hippo remember "<description of what went wrong>" --error
```

On task completion:
```bash
hippo outcome --good
```
<!-- hippo:end -->

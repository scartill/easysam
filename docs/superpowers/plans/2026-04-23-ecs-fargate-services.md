# ECS Fargate Services Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a new `services` section in EasySAM to deploy long-running background workers or web services on AWS ECS Fargate.

**Architecture:** Extend the YAML model to support `services`, update the loading logic to handle these new resources, and modify the Jinja2 template to generate the corresponding ECS resources (Cluster, TaskDefinition, Service) and IAM roles.

**Tech Stack:** Python, Jinja2, AWS SAM/CloudFormation, JSON Schema.

---

### Task 1: Update Schema for Services

**Files:**
- Modify: `src/easysam/schemas.json`

- [ ] **Step 1: Add service definitions to the schema**
Update `src/easysam/schemas.json` to include `services_schema` and update the top-level `properties`.

```json
{
  "definitions": {
    "services_schema": {
      "type": "object",
      "properties": {
        "image": { "type": "string" },
        "build": { "type": "string" },
        "cpu": { "type": "integer", "enum": [256, 512, 1024, 2048, 4096] },
        "memory": { "type": "integer" },
        "count": { "type": "integer", "minimum": 0 },
        "ports": { "type": "array", "items": { "type": "integer" } },
        "envvars": { "type": "object", "patternProperties": { "^[A-Za-z0-9_]+$": { "type": "string" } } },
        "tables": { "type": "array", "items": { "type": "string" } },
        "buckets": { "type": "array", "items": { "type": "string" } },
        "queues": { "type": "array", "items": { "type": "string" } },
        "streams": { "type": "array", "items": { "type": "string" } }
      },
      "oneOf": [
        { "required": ["image"] },
        { "required": ["build"] }
      ],
      "additionalProperties": false
    }
  },
  "properties": {
    "services": {
      "type": "object",
      "patternProperties": {
        "^[a-z0-9-]+$": { "$ref": "#/definitions/services_schema" }
      },
      "additionalProperties": false
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/easysam/schemas.json
git commit -m "feat: add services to JSON schema"
```

---

### Task 2: Update Loading Logic

**Files:**
- Modify: `src/easysam/load.py`

- [ ] **Step 1: Add 'services' to SUPPORTED_SECTIONS and local import logic**
Update `SUPPORTED_SECTIONS` and ensure `preprocess_file` handles `services`.

```python
SUPPORTED_SECTIONS = [
    'tables',
    'paths',
    'functions',
    'buckets',
    'authorizers',
    'prismarine',
    'import',
    'lambda',
    'search',
    'mqtt',
    'services', # Add this
]

# Update preprocess_file to include:
if services_def := entry_data.get('services'):
    if 'services' not in resources_data:
        resources_data['services'] = {}
    resources_data['services'].update(services_def)
```

- [ ] **Step 2: Add defaults for services**
Create a `process_default_services` function and call it in `preprocess_defaults`.

```python
def process_default_services(resources_data: dict, errors: list[str]):
    if 'services' in resources_data:
        for name, service in resources_data['services'].items():
            service.setdefault('cpu', 256)
            service.setdefault('memory', 512)
            service.setdefault('count', 1)
```

- [ ] **Step 3: Commit**

```bash
git add src/easysam/load.py
git commit -m "feat: support services in loading logic"
```

---

### Task 3: Add CLI Flag

**Files:**
- Modify: `src/easysam/cli.py`

- [ ] **Step 1: Add --no-docker-build-on-win option**
Update `@click.command()` for `generate` and `deploy`.

```python
@click.option('--no-docker-build-on-win', is_flag=True, help='Skip Docker build metadata on Windows')
```

- [ ] **Step 2: Pass the flag to generate_template**
Ensure the flag is passed from CLI to the template generation logic.

- [ ] **Step 3: Commit**

```bash
git add src/easysam/cli.py
git commit -m "feat: add --no-docker-build-on-win CLI flag"
```

---

### Task 4: Update Template Generation

**Files:**
- Modify: `src/easysam/template.j2`

- [ ] **Step 1: Add ECS Cluster resource**
Render a single ECS Cluster if `services` are defined.

```jinja2
{% if services is defined %}
  {{ lprefix }}Cluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: !Sub "{{ lprefix }}-cluster-${Stage}"
{% endif %}
```

- [ ] **Step 2: Add ECS Task Definition and Service**
Loop through `services` and render TaskDefinition (with IAM roles) and Service.

- [ ] **Step 3: Handle --no-docker-build-on-win**
Use the flag to conditionally render `Metadata: BuildMethod: docker`.

- [ ] **Step 4: Commit**

```bash
git add src/easysam/template.j2
git commit -m "feat: render ECS resources in SAM template"
```

---

### Task 5: Verification and Testing

**Files:**
- Create: `tests/test_services.py`

- [ ] **Step 1: Write a test case for a simple service**
Verify that a `resources.yaml` with a service generates the expected CloudFormation resources.

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_services.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_services.py
git commit -m "test: add verification tests for ECS services"
```

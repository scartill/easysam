# Design Spec: ECS Fargate Services in EasySAM

## 1. Overview
Introduce a top-level `services` section to EasySAM to support long-running components (polling loops, real-time event consumers, or lightweight web services) using AWS ECS Fargate. This complements the existing Lambda-based `functions` by providing a persistent execution environment.

## 2. User Experience (YAML Model)

### 2.1 Top-level `services`
The `services` key will be a map where each key is a service name.

```yaml
services:
  poller:
    # Source (One of)
    image: 1234567890.dkr.ecr.us-east-1.amazonaws.com/my-repo:latest
    build: ./src/poller

    # Compute (Defaults)
    cpu: 256
    memory: 512
    count: 1

    # Networking (Optional)
    ports:
      - 8080

    # Permissions & Environment (Consistent with 'functions')
    envvars:
      POLL_INTERVAL: "19"
    tables:
      - MyTable
    buckets:
      - raw-data
    queues:
      - jobs
```

### 2.2 CLI Options
A new flag `--no-docker-build-on-win` will be added to `generate` and `deploy` commands.
- When active, EasySAM will omit the `Metadata: BuildMethod: docker` block in the SAM template for services using `build:`. This allows users to generate templates on Windows without a running Docker daemon if they intend to build elsewhere.

## 3. Architecture & Technical Details

### 3.1 Generated SAM Resources
For every stack containing `services`, EasySAM will generate:
1. **AWS::ECS::Cluster**: A single cluster named `<Prefix>Cluster-${Stage}`.
2. **AWS::ECS::TaskDefinition**:
   - `RequiresCompatibilities: [FARGATE]`
   - `NetworkMode: awsvpc`
   - `Cpu` and `Memory` mapped from YAML.
   - `ContainerDefinitions`:
     - Image mapped from `image` or handled by SAM via `build`.
     - `PortMappings` if `ports` are defined.
     - `LogConfiguration` pointing to a managed `AWS::Logs::LogGroup`.
3. **AWS::ECS::Service**:
   - `LaunchType: FARGATE`
   - `DesiredCount` mapped from `count`.
   - `NetworkConfiguration`:
     - `AwsvpcConfiguration`:
       - `Subnets`: Defaulting to Default VPC Public Subnets.
       - `AssignPublicIp: ENABLED` (defaulting to enabled for simple internet access).
4. **IAM Roles**:
   - `TaskRole`: Grants access to defined `tables`, `buckets`, etc.
   - `ExecutionRole`: Grants `ecs:PullImage` and `logs:CreateLogStream/PutLogEvents`.

### 3.2 Implementation Strategy
- **Schema:** Update `src/easysam/schemas.json` to include the `services` definition.
- **Loading:** Update `src/easysam/load.py` to support the `services` section and local `easysam.yaml` imports.
- **Generation:** Update `src/easysam/template.j2` to render ECS resources.
- **CLI:** Add the `--no-docker-build-on-win` option to `src/easysam/cli.py` and pass it through to the generation logic.

## 4. Success Criteria
- Validated `resources.yaml` with `services` generates a deployable SAM template.
- Services have the correct IAM permissions to access other EasySAM resources.
- The `--no-docker-build-on-win` flag correctly toggles metadata generation.

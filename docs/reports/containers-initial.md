# Gaps & Deficiencies Findings

- VPC/Subnet Customization: Only default VPC public subnets are mentioned. No support
for custom VPCs, private subnets, or security groups—critical for production.
- Service Discovery/Networking: No mention of service discovery, internal-only services, or load balancer integration.
- Scaling: Only static count is supported; no autoscaling or scheduled scaling.
- Health Checks: No configuration for container health checks.
- Secrets Management: No support for injecting secrets (e.g., from SSM or Secrets Manager).
- Logging: Only basic CloudWatch Logs; no log retention or advanced logging options.
- Lifecycle/Update Strategy: No mention of deployment strategies (rolling, blue/green, etc.).
- Resource Limits: No validation or documentation of allowed CPU/memory combinations.
- Error Handling: No details on error handling for failed deployments or misconfigurations.
- Testing/Local Dev: No guidance for local development or testing of services.
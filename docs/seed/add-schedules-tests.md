We need to add tests for the recently implemented `schedules` support for Lambda definitions.

The tests should cover the expected behavior when `schedules.target` is provided, including the generated CloudFormation resources and environment variables.

Lambda definitions without `schedules` should continue to work as before.

The tests should follow the existing testing patterns in the project.

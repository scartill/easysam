---
name: document-feature
description: Document a new EasySAM feature across the project. Use when the user asks to document a specific feature (e.g., "/document functionurl").
---

# Document Feature

This skill provides a standardized workflow for documenting a new EasySAM feature {{args}}.

## Workflow

### 1. Research

Understand how the feature is implemented and used.

- **Schema**: Search `src/easysam/schemas.json` for the feature name to find allowed properties, types, and enums.
- **Implementation**: Search `src/easysam/template.j2` to see how the YAML properties map to AWS SAM resources.
- **Usage**: Search the `example/` directory for any existing usages (e.g., in `resources.yaml` or `easysam.yaml`).
- **Tests**: Search `tests/` for related test cases to see expected behavior and edge cases.

### 2. Strategy

Plan the documentation updates across these key files:

- **Root `README.md`**: Add the feature to the "Native support for" list in the "Why EasySAM" section.
- **`docs/RESOURCE_REFERENCE.md`**:
    - Update the main resource example (e.g., in `## Functions`) to show basic usage.
    - Create a dedicated `## Feature Name` section with:
        - A brief description.
        - Code blocks for "Simple form" and "Advanced form".
        - A "Fields" list with descriptions, types, and defaults.
- **`example/README.md`**:
    - Add the feature's example to the "Example matrix".
    - Add a brief note under "Example notes" explaining what the example demonstrates.

### 3. Execution

Apply the changes using the `replace` tool to ensure precision and maintain existing formatting.

#### Root README.md
Add the feature to the bulleted list under "Native support for:".

#### docs/RESOURCE_REFERENCE.md
Ensure the new section follows the established style:
- Use `## Feature Name (Category)` for the header.
- Use `yaml` code blocks.
- Use a bulleted list for fields.

#### example/README.md
- Update the table in the "Example matrix" section.
- Add the note in alphabetical or logical order in "Example notes".

### 4. Validation

- Verify that all modified files render correctly in Markdown.
- Ensure technical accuracy by cross-referencing with `schemas.json` one last time.

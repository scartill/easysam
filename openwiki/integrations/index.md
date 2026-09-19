# Files

- [Conditionals and Deploy Overrides](conditional-overrides.md) - How EasySAM resolves `!Conditional` YAML tags and context-file overrides against the deploy context, and how these two mechanisms interact with loading, validation, and template generation.
- [Prismarine Integration Points](prismarine.md) - How EasySAM consumes the Prismarine package at two pipeline stages — preprocessing DynamoDB table definitions in load.py and post-template client code generation in prismarine.py — including configuration, prefix validation, trigger handling, modelling modes, and the db.py re-export pattern.

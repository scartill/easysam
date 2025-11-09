# Deploy to multiple regions

This example shows how to deploy a EasySAM application to multiple regions. It assumes that you have an AWS profile named `easysam-a` that has access to the regions `eu-west-1` and `eu-west-2`.

## CLI Deployment

```
uv run easysam --environment easysamdev --with-context .\example\multiregion\on_eu_west_1.yaml --with-context .\example\multiregion\on_eu_west_2.yaml deploy .\example\multiregion\
```

Note that all paths here are relative to the root of the EasySAM project. Amend accordingly to your project structure.

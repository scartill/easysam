# Deploy to multiple regions

This example shows how to deploy a EasySAM application to multiple regions. It assumes that you have an AWS profile named `easysam-a` that has access to the regions `eu-west-1` and `eu-west-2`.

## CLI Deployment

```
uv run easysam --environment easysamdev --aws-profile easysam-a deploy .\example\multiregion\
```
import pytest
from pathlib import Path
from easysam.load import resources
from easysam.definitions import FatalError

def test_local_validation_unexpected_section(tmp_path):
    resources_yaml = tmp_path / "resources.yaml"
    resources_yaml.write_text("prefix: test\nimport: [backend/func]", encoding="utf-8")
    
    backend_dir = tmp_path / "backend" / "func"
    backend_dir.mkdir(parents=True)
    
    easysam_yaml = backend_dir / "easysam.yaml"
    easysam_yaml.write_text("invalid_section: something\nlambda:\n  name: myfunc", encoding="utf-8")
    
    errors = []
    deploy_ctx = {"environment": "dev", "target_region": "us-east-1"}
    
    resources_data = resources(tmp_path, [], deploy_ctx, errors)
    
    assert any("Invalid local resources data" in err for err in errors)
    assert any("Additional properties are not allowed ('invalid_section' was unexpected)" in err for err in errors)

def test_local_validation_missing_lambda_name(tmp_path):
    resources_yaml = tmp_path / "resources.yaml"
    resources_yaml.write_text("prefix: test\nimport: [backend/func]", encoding="utf-8")
    
    backend_dir = tmp_path / "backend" / "func"
    backend_dir.mkdir(parents=True)
    
    easysam_yaml = backend_dir / "easysam.yaml"
    easysam_yaml.write_text("lambda:\n  timeout: 30", encoding="utf-8")
    
    errors = []
    deploy_ctx = {"environment": "dev", "target_region": "us-east-1"}
    
    resources_data = resources(tmp_path, [], deploy_ctx, errors)
    
    assert any("Invalid local resources data" in err for err in errors)
    assert any("'name' is a required property" in err for err in errors)

def test_local_validation_invalid_integration(tmp_path):
    resources_yaml = tmp_path / "resources.yaml"
    resources_yaml.write_text("prefix: test\nimport: [backend/func]", encoding="utf-8")
    
    backend_dir = tmp_path / "backend" / "func"
    backend_dir.mkdir(parents=True)
    
    easysam_yaml = backend_dir / "easysam.yaml"
    easysam_yaml.write_text("lambda:\n  name: myfunc\n  integration:\n    open: true", encoding="utf-8")
    
    errors = []
    deploy_ctx = {"environment": "dev", "target_region": "us-east-1"}
    
    resources_data = resources(tmp_path, [], deploy_ctx, errors)
    
    assert any("Invalid local resources data" in err for err in errors)
    assert any("'path' is a required property" in err for err in errors)

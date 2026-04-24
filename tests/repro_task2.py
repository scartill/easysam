from easysam.load import resources
from pathlib import Path
import pytest

def test_services_loading(tmp_path):
    resources_yaml = tmp_path / "resources.yaml"
    resources_yaml.write_text("prefix: test\nimport: [backend/service]", encoding="utf-8")
    
    service_dir = tmp_path / "backend" / "service"
    service_dir.mkdir(parents=True)
    
    easysam_yaml = service_dir / "easysam.yaml"
    easysam_yaml.write_text("services:\n  myservice:\n    image: myimage\n", encoding="utf-8")
    
    errors = []
    deploy_ctx = {"environment": "dev", "target_region": "us-east-1"}
    
    resources_data = resources(tmp_path, [], deploy_ctx, errors)
    
    if errors:
        print(f"Errors found: {errors}")
    
    assert "services" in resources_data
    assert "myservice" in resources_data["services"]
    assert resources_data["services"]["myservice"]["image"] == "myimage"
    # Test defaults
    assert resources_data["services"]["myservice"]["cpu"] == 256
    assert resources_data["services"]["myservice"]["memory"] == 512
    assert resources_data["services"]["myservice"]["count"] == 1

if __name__ == "__main__":
    pytest.main([__file__])

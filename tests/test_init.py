import pytest
from click.testing import CliRunner
from easysam.cli import easysam
from pathlib import Path
import os

def test_init_command(tmp_path):
    # Change to tmp_path to simulate a fresh project directory
    os.chdir(tmp_path)
    
    # Create a dummy pyproject.toml as easysam init requires it
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = "test-app"\n')
    
    runner = CliRunner()
    result = runner.invoke(easysam, ['init'])
    
    assert result.exit_code == 0
    
    # Check if files are created in the right places
    assert (tmp_path / 'resources.yaml').exists()
    assert (tmp_path / '.gitignore').exists()
    assert (tmp_path / 'common' / 'utils.py').exists()
    assert (tmp_path / 'backend' / 'database' / 'easysam.yaml').exists()
    assert (tmp_path / 'backend' / 'function' / 'myfunction' / 'easysam.yaml').exists()
    
    # Check backend .gitignore
    backend_gitignore = tmp_path / 'backend' / '.gitignore'
    assert backend_gitignore.exists()
    content = backend_gitignore.read_text()
    assert '**/common/' in content
    
    # Check that function .gitignore does NOT exist
    assert not (tmp_path / 'backend' / 'function' / '.gitignore').exists()

def test_init_prismarine_command(tmp_path):
    os.chdir(tmp_path)
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = "test-app-prismarine"\n')
    
    runner = CliRunner()
    result = runner.invoke(easysam, ['init', '--prismarine'])
    
    assert result.exit_code == 0
    
    # Check if files are created in the right places
    assert (tmp_path / 'resources.yaml').exists()
    assert (tmp_path / 'backend' / '.gitignore').exists()
    assert (tmp_path / 'common' / 'myobject' / 'models.py').exists()
    assert (tmp_path / 'backend' / 'function' / 'itemlogger' / 'easysam.yaml').exists()

    # Check backend .gitignore
    backend_gitignore = tmp_path / 'backend' / '.gitignore'
    assert backend_gitignore.exists()
    content = backend_gitignore.read_text()
    assert '**/common/' in content

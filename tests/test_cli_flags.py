import pytest
from click.testing import CliRunner
from easysam.cli import easysam
from unittest.mock import patch

def test_generate_no_docker_build_on_win_flag():
    runner = CliRunner()
    with patch('easysam.cli.generate') as mock_generate:
        mock_generate.return_value = ({}, [])
        # Create a dummy directory to pass exists=True check
        with runner.isolated_filesystem():
            Path("dummy_dir").mkdir()
            result = runner.invoke(easysam, ['generate', '--no-docker-build-on-win', 'dummy_dir'])
            
            # The flag should be in the obj passed to generate
            # In generate_cmd: resources_data, errors = generate(obj, directory, pypath, deploy_ctx)
            args, kwargs = mock_generate.call_args
            obj = args[0]
            assert obj.get('no_docker_build_on_win') is True

def test_deploy_no_docker_build_on_win_flag():
    runner = CliRunner()
    with patch('easysam.cli.deploy') as mock_deploy:
        with runner.isolated_filesystem():
            Path("dummy_dir").mkdir()
            result = runner.invoke(easysam, ['deploy', '--no-docker-build-on-win', 'dummy_dir'])
            
            # The flag should be in the obj passed to deploy
            # In deploy_cmd: deploy(obj, directory, deploy_ctx)
            args, kwargs = mock_deploy.call_args
            obj = args[0]
            assert obj.get('no_docker_build_on_win') is True

from pathlib import Path

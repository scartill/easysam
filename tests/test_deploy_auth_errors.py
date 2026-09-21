"""Tests for friendly AWS authentication error handling in deploy."""

import subprocess
from unittest import mock

import pytest
from botocore.exceptions import (
    NoCredentialsError,
    ProfileNotFound,
    TokenRetrievalError,
)

from easysam import deploy as d


# --- _looks_like_auth_error ---

def test_looks_like_auth_error_matches_sso_token_expiry():
    # The exact message the user reported, as emitted by the SAM CLI subprocess
    output = 'Error: Error when retrieving token from sso: Token has expired and refresh failed'
    assert d._looks_like_auth_error(output)


def test_looks_like_auth_error_matches_missing_credentials():
    assert d._looks_like_auth_error('Unable to locate credentials')


def test_looks_like_auth_error_ignores_unrelated_output():
    assert not d._looks_like_auth_error('Successfully created/updated stack')
    assert not d._looks_like_auth_error('')
    assert not d._looks_like_auth_error(None)


# --- verify_credentials ---

def _patch_session(monkeypatch, sts_client):
    fake_session = mock.MagicMock()
    fake_session.client.return_value = sts_client
    monkeypatch.setattr(d.boto3, 'Session', mock.MagicMock(return_value=fake_session))
    return fake_session


def test_verify_credentials_ok(monkeypatch):
    sts = mock.MagicMock()
    sts.get_caller_identity.return_value = {'Arn': 'arn:aws:iam::123456789012:user/dev'}
    _patch_session(monkeypatch, sts)

    # Should not raise
    d.verify_credentials({'aws_profile': 'easysam-a'}, {'target_region': 'us-east-1'})


def test_verify_credentials_sso_token_expired(monkeypatch):
    sts = mock.MagicMock()
    sts.get_caller_identity.side_effect = TokenRetrievalError(
        provider='sso', error_msg='Token has expired and refresh failed'
    )
    _patch_session(monkeypatch, sts)

    with pytest.raises(UserWarning) as exc:
        d.verify_credentials({'aws_profile': 'easysam-a'}, {'target_region': 'us-east-1'})

    msg = str(exc.value)
    assert 'AWS authentication failed' in msg
    assert 'easysam-a' in msg
    assert 'aws sso login' in msg


def test_verify_credentials_no_credentials(monkeypatch):
    sts = mock.MagicMock()
    sts.get_caller_identity.side_effect = NoCredentialsError()
    _patch_session(monkeypatch, sts)

    with pytest.raises(UserWarning) as exc:
        d.verify_credentials({}, {})

    assert 'AWS authentication failed' in str(exc.value)


def test_verify_credentials_profile_not_found(monkeypatch):
    monkeypatch.setattr(
        d.boto3, 'Session', mock.MagicMock(side_effect=ProfileNotFound(profile='nope'))
    )

    with pytest.raises(UserWarning) as exc:
        d.verify_credentials({'aws_profile': 'nope'}, {})

    assert "profile 'nope' was not found" in str(exc.value)


# --- sam_deploy failure path ---

def test_sam_deploy_translates_auth_error(monkeypatch, tmp_path):
    err = subprocess.CalledProcessError(
        returncode=1,
        cmd=['sam', 'deploy'],
        output='',
        stderr='Error: Error when retrieving token from sso: Token has expired and refresh failed',
    )
    monkeypatch.setattr(d.subprocess, 'run', mock.MagicMock(side_effect=err))

    cliparams = {'sam_tool': 'sam', 'dry_run': False, 'aws_profile': 'easysam-a', 'verbose': False}
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}

    with pytest.raises(UserWarning) as exc:
        d.sam_deploy(cliparams, tmp_path, deploy_ctx, {})

    msg = str(exc.value)
    assert 'AWS authentication failed' in msg
    assert 'aws sso login' in msg


def test_sam_deploy_generic_failure_still_raises(monkeypatch, tmp_path):
    err = subprocess.CalledProcessError(
        returncode=1,
        cmd=['sam', 'deploy'],
        output='',
        stderr='Some unrelated CloudFormation error',
    )
    monkeypatch.setattr(d.subprocess, 'run', mock.MagicMock(side_effect=err))

    cliparams = {'sam_tool': 'sam', 'dry_run': False, 'aws_profile': None, 'verbose': False}
    deploy_ctx = {'environment': 'dev', 'target_region': 'us-east-1'}

    with pytest.raises(UserWarning) as exc:
        d.sam_deploy(cliparams, tmp_path, deploy_ctx, {})

    # Falls back to the generic message, not the auth one
    assert 'Failed to deploy SAM template' in str(exc.value)
    assert 'authentication' not in str(exc.value)

"""Shared fixtures for repository tool tests."""

import shutil
from pathlib import Path

import pytest

from workrepo.policy import POLICY_PATH
from workrepo.schema import SCHEMA_PATH

PROJECT_ROOT = Path(__file__).parents[1]


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Create a minimal work repository with production schema and templates."""
    schema_target = tmp_path / SCHEMA_PATH
    schema_target.parent.mkdir(parents=True)
    shutil.copy(PROJECT_ROOT / SCHEMA_PATH, schema_target)
    shutil.copy(PROJECT_ROOT / POLICY_PATH, tmp_path / POLICY_PATH)
    shutil.copytree(PROJECT_ROOT / "90-templates", tmp_path / "90-templates")
    inbox = tmp_path / "00-inbox"
    inbox.mkdir()
    shutil.copy(PROJECT_ROOT / "00-inbox/README.md", inbox / "README.md")
    return tmp_path

"""Shared fixtures for repository tool tests."""

import shutil
from pathlib import Path

import pytest

from workrepo.schema import SCHEMA_PATH

PROJECT_ROOT = Path(__file__).parents[1]


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Create a minimal work repository with production schema and templates."""
    schema_target = tmp_path / SCHEMA_PATH
    schema_target.parent.mkdir(parents=True)
    shutil.copy(PROJECT_ROOT / SCHEMA_PATH, schema_target)
    shutil.copytree(PROJECT_ROOT / "90-templates", tmp_path / "90-templates")
    return tmp_path

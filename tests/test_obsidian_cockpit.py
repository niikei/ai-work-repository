"""Contract tests for the shared Obsidian cockpit experience."""

from pathlib import Path

from workrepo.yamlutil import load_yaml

PROJECT_ROOT = Path(__file__).parents[1]
COCKPIT_PATH = PROJECT_ROOT / "40-library/40-resources/views/cockpit.base"
SNIPPET_PATH = PROJECT_ROOT / ".obsidian/snippets/vault-focus.css"
EXPECTED_COCKPIT_VIEWS = {"Attention", "Active projects", "Area reviews", "Recent activity"}
HIDDEN_FOLDERS = {"src", "tests", ".github", ".workspace", ".venv"}
HIDDEN_FILES = {
    "pyproject.toml",
    "uv.lock",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "SECURITY.md",
}


def test_cockpit_exposes_operational_views_in_one_fixed_base() -> None:
    """Daily management switches views without a movable spatial canvas."""
    payload = load_yaml(COCKPIT_PATH.read_text(encoding="utf-8"))

    assert {view["name"] for view in payload["views"]} == EXPECTED_COCKPIT_VIEWS
    assert all(view["type"] == "table" for view in payload["views"])
    assert "formula.needs_attention" in payload["views"][0]["filters"]


def test_focus_snippet_hides_only_declared_repository_chrome() -> None:
    """Focused navigation remains explicit and reversible through one snippet."""
    css = SNIPPET_PATH.read_text(encoding="utf-8")

    for path in HIDDEN_FOLDERS | HIDDEN_FILES:
        assert f'data-path="{path}"' in css
    assert 'data-path="DASHBOARD.md"' not in css

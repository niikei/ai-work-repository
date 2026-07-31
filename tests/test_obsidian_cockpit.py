"""Contract tests for the shared Obsidian cockpit experience."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
COCKPIT_PATH = PROJECT_ROOT / "COCKPIT.canvas"
SNIPPET_PATH = PROJECT_ROOT / ".obsidian/snippets/vault-focus.css"
EXPECTED_COCKPIT_VIEWS = {
    "40-library/40-resources/views/attention.base": "#All attention",
    "40-library/40-resources/views/projects.base": "#Active",
    "40-library/40-resources/views/areas.base": "#Attention",
    "40-library/40-resources/views/recent-logs.base": "#Last 7 days",
}
HIDDEN_FOLDERS = {"src", "tests", ".github", ".workspace", ".venv"}
HIDDEN_FILES = {
    "pyproject.toml",
    "uv.lock",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "SECURITY.md",
}


def test_cockpit_places_each_operational_base_once() -> None:
    """The visual cockpit embeds the intended Base views in a two-by-two grid."""
    payload = json.loads(COCKPIT_PATH.read_text(encoding="utf-8"))
    nodes = payload["nodes"]
    file_nodes = [node for node in nodes if node["type"] == "file"]

    assert len({node["id"] for node in nodes}) == len(nodes)
    assert {node["file"]: node["subpath"] for node in file_nodes} == (
        EXPECTED_COCKPIT_VIEWS
    )
    assert {node["x"] for node in file_nodes} == {0, 950}
    assert {node["y"] for node in file_nodes} == {0, 550}
    assert all((PROJECT_ROOT / node["file"]).is_file() for node in file_nodes)


def test_focus_snippet_hides_only_declared_repository_chrome() -> None:
    """Focused navigation remains explicit and reversible through one snippet."""
    css = SNIPPET_PATH.read_text(encoding="utf-8")

    for path in HIDDEN_FOLDERS | HIDDEN_FILES:
        assert f'data-path="{path}"' in css
    assert 'data-path="DASHBOARD.md"' not in css
    assert 'data-path="COCKPIT.canvas"' not in css

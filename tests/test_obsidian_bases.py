"""Contract tests for shared Obsidian Bases."""

from pathlib import Path

from workrepo.yamlutil import load_yaml

PROJECT_ROOT = Path(__file__).parents[1]
BASES_ROOT = PROJECT_ROOT / "40-library" / "40-resources" / "views"
EXPECTED_BASES = {
    "areas.base": {"Attention", "By group", "Review cadence"},
    "external-resources.base": {"Needs verification", "By access", "All resources"},
    "projects.base": {"Attention", "Active", "Portfolio"},
    "recent-logs.base": {"Last 7 days", "Last 30 days", "All logs"},
}


def test_shared_bases_have_valid_structure() -> None:
    """Every committed Base has filters and named table views."""
    assert {path.name for path in BASES_ROOT.glob("*.base")} == EXPECTED_BASES.keys()

    for filename, expected_views in EXPECTED_BASES.items():
        payload = load_yaml((BASES_ROOT / filename).read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        assert "filters" in payload
        assert isinstance(payload.get("properties"), dict)
        views = payload.get("views")
        assert isinstance(views, list)
        assert {view["name"] for view in views} == expected_views
        assert all(view.get("type") == "table" for view in views)

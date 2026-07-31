"""Contract tests for shared Obsidian Bases."""

from pathlib import Path

from workrepo.yamlutil import load_yaml

PROJECT_ROOT = Path(__file__).parents[1]
BASES_ROOT = PROJECT_ROOT / "40-library" / "40-resources" / "views"
EXPECTED_BASES = {
    "attention.base": {"All attention", "Projects", "Areas", "External resources"},
    "areas.base": {"Attention", "By group", "Review cadence"},
    "external-resources.base": {"Needs verification", "By access", "All resources"},
    "library.base": {"Drafts", "Active library", "Retired"},
    "projects.base": {"Attention", "Active", "Portfolio"},
    "recent-logs.base": {"Last 7 days", "Last 30 days", "All logs"},
}
MAX_VIEW_LIMIT = 500


def test_shared_bases_have_valid_structure() -> None:
    """Every committed Base has filters and named table views."""
    assert {path.name for path in BASES_ROOT.glob("*.base")} == EXPECTED_BASES.keys()

    for filename, expected_views in EXPECTED_BASES.items():
        payload = load_yaml((BASES_ROOT / filename).read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        filters = payload.get("filters")
        assert isinstance(filters, dict)
        assert '!file.inFolder("90-templates")' in filters.get("and", [])
        assert isinstance(payload.get("properties"), dict)
        assert isinstance(payload.get("formulas"), dict)
        views = payload.get("views")
        assert isinstance(views, list)
        assert {view["name"] for view in views} == expected_views
        assert all(view.get("type") == "table" for view in views)
        assert all(isinstance(view.get("limit"), int) for view in views)
        assert all(0 < view["limit"] <= MAX_VIEW_LIMIT for view in views)
        assert all(
            isinstance(view.get("sort"), list)
            and all(item.get("direction") in {"ASC", "DESC"} for item in view["sort"])
            for view in views
        )


def test_area_base_derives_review_schedule() -> None:
    """Area attention includes overdue reviews derived from canonical cadence."""
    payload = load_yaml((BASES_ROOT / "areas.base").read_text(encoding="utf-8"))
    formulas = payload["formulas"]

    assert "last_reviewed" in formulas["next_review"]
    assert "review_cycle" in formulas["next_review"]
    assert formulas["review_overdue"] == "formula.next_review < today()"


def test_attention_base_combines_operational_signals() -> None:
    """The command center covers each managed attention source."""
    payload = load_yaml((BASES_ROOT / "attention.base").read_text(encoding="utf-8"))
    formulas = payload["formulas"]

    assert "target_date" in formulas["project_overdue"]
    assert "review_cycle" in formulas["area_review_overdue"]
    assert "last_verified" in formulas["resource_stale"]
    assert "formula.project_overdue" in formulas["needs_attention"]
    assert "formula.area_review_overdue" in formulas["needs_attention"]
    assert "formula.resource_stale" in formulas["needs_attention"]
    assert "Target overdue" in formulas["reason"]
    assert "Review overdue" in formulas["reason"]
    assert "Verification overdue" in formulas["reason"]

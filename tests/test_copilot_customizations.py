"""Structural checks for shared GitHub Copilot customizations."""

from pathlib import Path

from workrepo.yamlutil import load_yaml

PROJECT_ROOT = Path(__file__).parents[1]
MAX_ALWAYS_ON_WORDS = 220
EXPECTED_SKILLS = {
    "change-review",
    "inbox-triage",
    "record-maintenance",
    "workspace-status-review",
}


def _frontmatter(path: Path) -> dict[object, object]:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    assert lines[0] == "---", f"{path} must start with YAML frontmatter"
    closing = lines.index("---", 1)
    metadata = load_yaml("\n".join(lines[1:closing]))
    assert isinstance(metadata, dict), f"{path} frontmatter must be a mapping"
    assert "TODO" not in source, f"{path} contains an unfinished placeholder"
    return metadata


def test_always_on_instructions_stay_concise() -> None:
    """Task-specific detail belongs in conditional instructions or skills."""
    path = PROJECT_ROOT / ".github/copilot-instructions.md"
    assert len(path.read_text(encoding="utf-8").split()) <= MAX_ALWAYS_ON_WORDS


def test_always_on_instructions_require_unambiguous_paths() -> None:
    """Change reports must distinguish same-named entity dashboards."""
    source = (PROJECT_ROOT / ".github/copilot-instructions.md").read_text(encoding="utf-8")
    normalized = " ".join(source.split())

    assert (
        "Report touched files with full repository-relative paths as visible text, "
        "not basename-only labels or hidden link targets."
    ) in normalized


def test_agent_skills_have_discoverable_metadata() -> None:
    skills_root = PROJECT_ROOT / ".github/skills"
    skills = sorted(path for path in skills_root.iterdir() if path.is_dir())

    assert {skill.name for skill in skills} == EXPECTED_SKILLS
    for skill in skills:
        metadata = _frontmatter(skill / "SKILL.md")
        assert metadata["name"] == skill.name
        assert isinstance(metadata["description"], str)
        assert metadata["description"]


def test_change_review_uses_historical_snapshots_and_bounded_discovery() -> None:
    """Commit review cannot silently inspect HEAD or scan the whole repository."""
    source = (
        PROJECT_ROOT / ".github/skills/change-review/SKILL.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(source.split())

    assert "A lone Git ref identifies the commit itself" in normalized
    assert "review `REF^1..REF`, never `REF..HEAD`" in normalized
    assert "`git diff-tree --root` only for a root commit" in normalized
    assert "`git show REF:path`" in normalized
    assert "pipe the historical snapshot through `nl -ba`" in normalized
    assert "`git status`" in normalized
    assert "Never substitute the current worktree for historical content" in normalized
    assert (
        "Do not use workspace-wide search to rediscover paths already listed by Git."
        in normalized
    )
    assert "do not scan `**/*.md` or the full tree" in normalized
    assert (
        "`uv run workrepo check --ref REF --strict`, "
        "which checks and regenerates an isolated snapshot."
    ) in normalized
    assert (
        "Never run `workrepo refresh` in the current worktree during review"
        in normalized
    )
    assert "If isolated validation fails to run, say so." in normalized
    assert "full repository-relative paths as visible text" in normalized
    assert "Do not hide the path behind a basename-only link label." in normalized
    assert (
        "Area `last_reviewed` records an actual Area review, "
        "so differing dates are not inherently inconsistent."
    ) in normalized
    assert (
        "A generated file appearing in a commit is not proof of direct editing"
        in normalized
    )
    assert (
        "Copy every Git status and repository-relative path from the initial change list "
        "verbatim into a fenced code block."
    ) in normalized
    assert (
        "verify its count, statuses, and paths against the original `--name-status` output"
        in normalized
    )
    assert "../inbox-triage/SKILL.md" in source
    assert "../record-maintenance/SKILL.md" in source
    assert (
        "Do not require the same follow-up in a Log and a Project or Area."
        in normalized
    )

    metadata = _frontmatter(PROJECT_ROOT / ".github/skills/change-review/SKILL.md")
    assert metadata["argument-hint"] == "commit, range, --staged, or working tree"


def test_status_review_changes_last_reviewed_only_for_real_reviews() -> None:
    """Synchronizing Area state is not itself an operational review."""
    source = (
        PROJECT_ROOT / ".github/skills/workspace-status-review/SKILL.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(source.split())

    assert (
        "Change Area `last_reviewed` only when that Area was actually reviewed, "
        "not merely synchronized."
    ) in normalized


def test_path_instructions_define_application_scope() -> None:
    paths = sorted((PROJECT_ROOT / ".github/instructions").glob("*.instructions.md"))

    assert paths
    for path in paths:
        metadata = _frontmatter(path)
        assert isinstance(metadata["description"], str)
        assert isinstance(metadata["applyTo"], str)
        assert metadata["applyTo"]


def test_prompts_and_agents_have_selection_metadata() -> None:
    prompts = sorted((PROJECT_ROOT / ".github/prompts").glob("*.prompt.md"))
    agents = sorted((PROJECT_ROOT / ".github/agents").glob("*.agent.md"))

    assert prompts
    assert agents
    for path in prompts:
        metadata = _frontmatter(path)
        assert metadata["agent"] == "agent"
        assert isinstance(metadata["description"], str)
    for path in agents:
        metadata = _frontmatter(path)
        assert isinstance(metadata["name"], str)
        assert isinstance(metadata["description"], str)


def test_slash_commands_do_not_collide() -> None:
    """A human-facing prompt and an invocable skill cannot share one command."""
    prompt_names = {
        _frontmatter(path)["name"]
        for path in (PROJECT_ROOT / ".github/prompts").glob("*.prompt.md")
    }
    skill_names = {
        metadata["name"]
        for path in (PROJECT_ROOT / ".github/skills").glob("*/SKILL.md")
        if (metadata := _frontmatter(path)).get("user-invocable", True)
    }

    assert prompt_names.isdisjoint(skill_names)

"""Structural checks for shared GitHub Copilot customizations."""

from pathlib import Path

from workrepo.yamlutil import load_yaml

PROJECT_ROOT = Path(__file__).parents[1]
MAX_ALWAYS_ON_WORDS = 220


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


def test_agent_skills_have_discoverable_metadata() -> None:
    skills_root = PROJECT_ROOT / ".github/skills"
    skills = sorted(path for path in skills_root.iterdir() if path.is_dir())

    assert skills
    for skill in skills:
        metadata = _frontmatter(skill / "SKILL.md")
        assert metadata["name"] == skill.name
        assert isinstance(metadata["description"], str)
        assert metadata["description"]


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

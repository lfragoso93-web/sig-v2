from __future__ import annotations

import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPOSITORY_ROOT / ".agents" / "skills"
README = REPOSITORY_ROOT / "README.md"
EXPECTED_SKILLS = {
    "sgi-development": "stable-15jun",
    "sgi-financial-data": "transactions",
    "sgi-market-data": "BRAPI",
    "sgi-certification": "real_data_certification_events",
}


def _frontmatter(source: str) -> str:
    assert source.startswith("---\n")
    closing = source.find("\n---\n", 4)
    assert closing > 4
    return source[4:closing]


def test_agent_skills_have_complete_discoverable_contracts() -> None:
    assert {path.name for path in SKILLS_ROOT.iterdir() if path.is_dir()} == set(
        EXPECTED_SKILLS
    )

    for name, required_contract in EXPECTED_SKILLS.items():
        source = (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = _frontmatter(source)

        assert re.search(rf"^name: {re.escape(name)}$", frontmatter, re.MULTILINE)
        description = re.search(
            r"^description: (.+)$", frontmatter, re.MULTILINE
        )
        assert description is not None
        assert len(description.group(1)) >= 80
        assert "TODO" not in source
        assert required_contract in source


def test_agent_skill_interface_metadata_is_complete() -> None:
    for name in EXPECTED_SKILLS:
        source = (SKILLS_ROOT / name / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )

        assert 'display_name: "SGI ' in source
        assert re.search(r'^  short_description: ".+"$', source, re.MULTILINE)
        assert "TODO" not in source


def test_readme_routes_agents_to_versioned_skills() -> None:
    readme = README.read_text(encoding="utf-8")

    assert ".agents/skills" in readme
    assert all(name in readme for name in EXPECTED_SKILLS)

from pathlib import Path

from till.nodes import load_skill

ROOT = Path(__file__).resolve().parents[1]


def test_role_skill_files_exist_and_load():
    for role in ("cashier", "auditor", "clerk", "owner-gate"):
        path = ROOT / "skills" / role / "SKILL.md"
        assert path.is_file(), path
        text = load_skill(role)
        assert text == path.read_text(encoding="utf-8")
        assert role.replace("-", " ") in text.lower() or role in text.lower()

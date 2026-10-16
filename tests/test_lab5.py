"""Lab 5: the repository is set up for a team.

Reads the project's Claude Code files and checks them. No key, no cost.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRET = re.compile(r"sk-ant-|hl_[A-Za-z0-9]{8,}")


def frontmatter(path):
    """The YAML between the --- lines: {key: text or list of items}."""
    text = path.read_text()
    assert text.startswith("---\n"), f"{path.name}: no frontmatter"
    block = text.split("---\n")[1]
    found, key = {}, None
    for line in block.splitlines():
        if line.startswith("  - ") and key:
            found.setdefault(key, []).append(line[4:].strip().strip('"'))
        elif ":" in line:
            key, value = line.split(":", 1)
            found[key] = value.strip() or []
    return found


def test_mcp_json_uses_env_expansion_and_lists_codemap():
    raw = (ROOT / ".mcp.json").read_text()
    servers = json.loads(raw)["mcpServers"]
    assert {"harborline", "codemap"} <= set(servers)
    token = servers["harborline"]["env"]["HARBORLINE_API_TOKEN"]
    assert token == "${HARBORLINE_API_TOKEN}"
    assert not SECRET.search(raw), "a key or token is written in .mcp.json"


def test_claude_md_imports_exist():
    lines = (ROOT / "CLAUDE.md").read_text().splitlines()
    imports = [line[1:] for line in lines if line.startswith("@")]
    assert imports, "CLAUDE.md imports nothing"
    for name in imports:
        assert (ROOT / name).is_file(), f"CLAUDE.md imports a missing file: {name}"


def test_every_rule_is_scoped_to_files_that_exist():
    rules = sorted((ROOT / ".claude" / "rules").glob("*.md"))
    assert any(rule.name == "devtools.md" for rule in rules)
    for rule in rules:
        paths = frontmatter(rule).get("paths")
        assert paths, f"{rule.name} has no paths"
        for pattern in paths:
            assert list(ROOT.glob(pattern)), f"{rule.name}: {pattern} matches no file"


def test_map_module_runs_forked_and_read_only():
    skill = frontmatter(ROOT / ".claude" / "skills" / "map-module" / "SKILL.md")
    assert skill.get("description")
    assert skill.get("argument-hint")
    assert skill.get("context") == "fork"
    assert skill.get("agent") == "Explore"
    assert {"Write", "Edit", "Bash"} <= set(skill.get("disallowed-tools", "").split())
    assert "mcp__codemap__trace_export" in skill.get("allowed-tools", "")


def test_plan_or_direct():
    text = (ROOT / "notes" / "plan-or-direct.md").read_text().lower()
    choices = dict(re.findall(r"^([abc]): (plan|direct)\b", text, re.M))
    assert choices == {"a": "direct", "b": "plan", "c": "plan"}

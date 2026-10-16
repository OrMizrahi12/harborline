"""Generate tests for one module that cover behavior its existing tests don't.

python ci/testgen.py harborline/normalize.py
Writes tests/test_<module>_generated.py (never over an existing one) and runs it. Needs ANTHROPIC_API_KEY.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "imports": {"type": "string"},
        "tests": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "why_new": {"type": "string"}, "code": {"type": "string"}},
            "required": ["name", "why_new", "code"]}}},
    "required": ["imports", "tests"]})
PROMPT = """Write pytest tests for {module}, following the Testing section of CLAUDE.md.
Its existing tests are below. Don't test what they already test: for each new test, say in why_new
which behavior none of them covers. Put the imports in imports, and one complete test function in each code.
At most five tests.

{existing}"""


def existing_tests(module):
    name = Path(module).stem
    files = [p for p in sorted((ROOT / "tests").glob("test_*.py")) if name in p.read_text()]
    return "\n\n".join(f"# {p.relative_to(ROOT)}\n{p.read_text()}" for p in files) or "(none)"


def main(module):
    out = ROOT / "tests" / f"test_{Path(module).stem}_generated.py"
    if out.exists():
        sys.exit(f"{out.relative_to(ROOT)} exists: review it and commit or remove it first")
    prompt = PROMPT.format(module=module, existing=existing_tests(module))
    run = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json", "--json-schema", SCHEMA,
         "--permission-mode", "dontAsk", "--allowedTools", "Read,Grep,Glob"],
        capture_output=True, text=True, check=True)
    result = json.loads(run.stdout)
    tests = result["structured_output"]["tests"]
    for test in tests:
        print(f"{test['name']}: {test['why_new']}")
    body = [result["structured_output"]["imports"].strip()] + [t["code"].strip() for t in tests]
    out.write_text("\n\n\n".join(body) + "\n")
    print(f"{len(tests)} tests in {out.relative_to(ROOT)}; ${result['total_cost_usd']:.4f}")
    subprocess.run([sys.executable, "-m", "pytest", "-q", str(out)])


if __name__ == "__main__":
    main(sys.argv[1])

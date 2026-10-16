"""Review a pull request with Claude Code and post the findings as inline comments.

python ci/review.py <pr-number>   (in CI: .github/workflows/pr-review.yml)
Needs ANTHROPIC_API_KEY and a GitHub token (GH_TOKEN, or a gh login).
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = (ROOT / "ci" / "findings.schema.json").read_text()
MARK = "<!-- harborline-review -->"
PROMPT = """Review this pull request's diff for bugs and for breaks of this project's conventions.
Report each finding with its file and its line number in the new version of the file.
Earlier findings on this pull request are listed below. If one is still in the code, report it again
with status still_open; if it's fixed, leave it out. Give every other finding status new.
Earlier findings:
{prior}"""


def repo():
    url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True).stdout
    return os.environ.get("GITHUB_REPOSITORY") or re.sub(r"^.*github\.com[:/]|\.git\s*$", "", url.strip())


def gh(*args, data=None):
    run = subprocess.run(["gh", *args], input=data, capture_output=True, text=True, check=True)
    return run.stdout


def prior_findings(pr):
    comments = json.loads(gh("api", "--paginate", f"repos/{repo()}/pulls/{pr}/comments"))
    return [f"- {c['path']}:{c['original_line']}: {c['body'].replace(MARK, '').strip()}"
            for c in comments if MARK in c["body"]]


def review(diff, prior):
    prompt = PROMPT.format(prior="\n".join(prior) or "- none yet")
    run = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json", "--json-schema", SCHEMA,
         "--permission-mode", "dontAsk", "--allowedTools", "Read,Grep,Glob"],
        input=diff, capture_output=True, text=True, check=True)
    return json.loads(run.stdout)


def diff_lines(diff):
    """{path: line numbers of the new file shown in the diff}: the only lines GitHub can comment on."""
    lines, path, n = {}, None, 0
    for text in diff.splitlines():
        if text.startswith("+++ "):
            path = text[6:] if text.startswith("+++ b/") else None
        elif text.startswith("@@"):
            n = int(re.search(r"\+(\d+)", text).group(1))
        elif path and not text.startswith(("-", "\\")):
            lines.setdefault(path, set()).add(n)
            n += 1
    return lines


def comment(f):
    return f"**{f['severity']} · {f['category']}**: {f['issue']}\n\nFix: {f['fix']}\n{MARK}"


def post(pr, new, still, fixed, lines):
    """New findings as inline comments; the summary counts what's fixed and lists what's still open."""
    inline = [f for f in new if f["line"] in lines.get(f["path"], ())]
    rest = [f"- New, `{f['path']}:{f['line']}`: {f['issue']}" for f in new if f not in inline]
    rest += [f"- Still open, `{f['path']}:{f['line']}`: {f['issue']}" for f in still]
    head = f"Claude review: {len(new)} new, {len(still)} still open, {fixed} fixed."
    review_ = {"event": "COMMENT", "body": "\n".join([head] + rest),
               "comments": [{"path": f["path"], "line": f["line"], "side": "RIGHT", "body": comment(f)}
                            for f in inline]}
    gh("api", "-X", "POST", f"repos/{repo()}/pulls/{pr}/reviews", "--input", "-", data=json.dumps(review_))
    return len(inline)


def main(pr):
    diff = gh("pr", "diff", pr, "-R", repo())
    prior = prior_findings(pr)
    result = review(diff, prior)
    findings = result["structured_output"]["findings"]
    new = [f for f in findings if f["status"] == "new"]
    still = [f for f in findings if f["status"] == "still_open"]
    fixed = max(len(prior) - len(still), 0)
    inline = post(pr, new, still, fixed, diff_lines(diff))
    print(f"{len(prior)} earlier: {fixed} fixed, {len(still)} still open; {len(new)} new ({inline} inline); "
          f"{result['num_turns']} turns, ${result['total_cost_usd']:.4f}")


if __name__ == "__main__":
    main(sys.argv[1])

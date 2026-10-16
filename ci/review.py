"""Review a pull request with Claude Code and post the findings as inline comments.

python ci/review.py <pr-number>   (in CI: .github/workflows/pr-review.yml)
python ci/review.py --local <git range>   (prints the findings; posts nothing)
Needs ANTHROPIC_API_KEY, and a GitHub token (GH_TOKEN, or a gh login) to post.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = (ROOT / "ci" / "findings.schema.json").read_text()
CRITERIA = (ROOT / "ci" / "prompts" / "review.md").read_text()
CONFIG = json.loads((ROOT / "ci" / "review_config.json").read_text())
MARK = "<!-- harborline-review -->"
PROMPT = """
Report each finding with its file and its line number in the new version of the file.
Name the kind of problem in detected_pattern, in a few words joined by hyphens, such as refund-by-hand.
Earlier findings on this pull request are listed below. If one is still in the code, report it again
with status still_open; if it's fixed, leave it out. Give every other finding status new.
Earlier findings:
{prior}"""
CROSS = """
This is the whole pull request. Each file was already reviewed on its own: report only problems that span files,
such as a value one file produces in a unit or shape that another file reads differently."""
VERIFY = (ROOT / "ci" / "verify.schema.json").read_text()
CHECK = """You are checking findings that another reviewer wrote about this diff. Read the code each one points to.
For each finding, give its index, a verdict (confirmed, rejected or unsure) and your confidence from 0 to 1.
Findings:
{findings}"""


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


def claude(prompt, text, schema):
    run = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json", "--json-schema", schema,
         "--permission-mode", "dontAsk", "--allowedTools", "Read,Grep,Glob"],
        input=text, capture_output=True, text=True, check=True)
    return json.loads(run.stdout)


def files(diff):
    """{path: that file's part of the diff}"""
    parts = re.split(r"(?m)^(?=diff --git )", diff)
    return {re.search(r" b/(\S+)", p).group(1): p for p in parts if p.startswith("diff --git")}


def review(diff, prior):
    """One pass per file, one cross-file pass, then an independent check of every finding."""
    tail = PROMPT.format(prior="\n".join(prior) or "- none yet")
    passes = [(path, CRITERIA + tail, part) for path, part in files(diff).items()]
    if len(passes) > 1:
        passes.append(("cross-file", CRITERIA + CROSS + tail, diff))
    runs, found = [], []
    for name, prompt, text in passes:
        runs.append(claude(prompt, text, SCHEMA))
        found += [dict(f, found_by=name) for f in runs[-1]["structured_output"]["findings"]
                  if f["category"] not in CONFIG["disabled_categories"]]
    if found:
        listed = "\n".join(f"{i}. {f['path']}:{f['line']} {f['issue']}" for i, f in enumerate(found))
        runs.append(claude(CHECK.format(findings=listed), diff, VERIFY))
        for check in runs[-1]["structured_output"]["checks"]:
            found[check["index"]].update(verdict=check["verdict"], confidence=check["confidence"])
    return {"findings": [f for f in found if f.get("verdict") != "rejected"], "passes": len(runs),
            "num_turns": sum(run["num_turns"] for run in runs),
            "total_cost_usd": sum(run["total_cost_usd"] for run in runs)}


def log(findings):
    """Append findings to runs/review_log.jsonl, where ci/review_log.py tracks the ones developers dismiss."""
    path = ROOT / "runs" / "review_log.jsonl"
    path.parent.mkdir(exist_ok=True)
    with path.open("a") as out:
        out.writelines(json.dumps(f) + "\n" for f in findings)


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
    sure = [f for f in new if f.get("confidence", 0) >= CONFIG["inline_confidence"]]
    inline = [f for f in sure if f["line"] in lines.get(f["path"], ())]
    rest = [f"- New, `{f['path']}:{f['line']}`: {f['issue']}" for f in sure if f not in inline]
    rest += [f"- For a person to check ({f.get('confidence', 0):.2f}), `{f['path']}:{f['line']}`: {f['issue']}"
             for f in new if f not in sure]
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
    findings = result["findings"]
    new = [f for f in findings if f["status"] == "new"]
    still = [f for f in findings if f["status"] == "still_open"]
    fixed = max(len(prior) - len(still), 0)
    inline = post(pr, new, still, fixed, diff_lines(diff))
    print(f"{len(prior)} earlier: {fixed} fixed, {len(still)} still open; {len(new)} new ({inline} inline); "
          f"{result['num_turns']} turns, ${result['total_cost_usd']:.4f}")


def local(git_range):
    diff = subprocess.run(["git", "diff", git_range], capture_output=True, text=True, check=True).stdout
    result = review(diff, [])
    log(result["findings"])
    for f in result["findings"]:
        print(f"{f['path']}:{f['line']} {f['severity']} {f['category']} (found by {f['found_by']}; "
              f"{f.get('verdict', 'unchecked')} {f.get('confidence', 0):.2f}): {f['issue']}")
    print(f"{len(result['findings'])} findings from {result['passes']} passes; "
          f"{result['num_turns']} turns, ${result['total_cost_usd']:.4f}")


if __name__ == "__main__":
    if sys.argv[1] == "--local":
        local(sys.argv[2])
    else:
        main(sys.argv[1])

"""The review log: list findings, mark the ones developers dismissed, and see which patterns get dismissed.

python ci/review_log.py              list the logged findings, numbered
python ci/review_log.py dismiss 3 5  mark findings 3 and 5 as dismissed
python ci/review_log.py report       dismissals per detected_pattern
"""

import json
import sys
from collections import Counter
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / "runs" / "review_log.jsonl"


def load():
    return [json.loads(line) for line in LOG.read_text().splitlines()] if LOG.exists() else []


def main(args):
    findings = load()
    if args[:1] == ["dismiss"]:
        for n in args[1:]:
            findings[int(n) - 1]["dismissed"] = True
        LOG.write_text("".join(json.dumps(f) + "\n" for f in findings))
    elif args[:1] == ["report"]:
        seen = Counter(f["detected_pattern"] for f in findings)
        dropped = Counter(f["detected_pattern"] for f in findings if f.get("dismissed"))
        for pattern, n in seen.most_common():
            print(f"{pattern:32} {dropped[pattern]} of {n} dismissed")
    else:
        for i, f in enumerate(findings, 1):
            mark = "  (dismissed)" if f.get("dismissed") else ""
            print(f"{i:2}. {f['detected_pattern']:30} {f['path']}:{f['line']} {f['severity']}{mark}")


if __name__ == "__main__":
    main(sys.argv[1:])

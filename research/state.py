"""Each run's state on disk, so a crashed run can resume.

research/runs/<run_id>/manifest.json lists the question and every subagent
report saved so far; each report is its own JSON file next to it. A new
run with --resume <run_id> starts from the manifest instead of from zero.
The final report goes in report.json, where research.checker reads it.
"""

import json
import time
from pathlib import Path

RUNS = Path(__file__).resolve().parent / "runs"


def start(question):
    """A new run: its folder and an empty manifest."""
    run_id = time.strftime("%Y%m%d-%H%M%S")
    (RUNS / run_id).mkdir(parents=True)
    write(run_id, {"question": question, "reports": []})
    return run_id


def manifest(run_id):
    return json.loads((RUNS / run_id / "manifest.json").read_text())


def write(run_id, data):
    path = RUNS / run_id / "manifest.json"
    path.with_suffix(".tmp").write_text(json.dumps(data, indent=1))
    path.with_suffix(".tmp").replace(path)  # a crash never leaves half a file


def save(run_id, name, prompt, report, **more):
    """One subagent's report: its own file, then a line in the manifest.

    more: anything else the run needs to continue, kept in the manifest.
    """
    file = f"{name.replace(' ', '-')}.json"
    (RUNS / run_id / file).write_text(json.dumps(
        {"name": name, "prompt": prompt, "report": report}, indent=1))
    data = manifest(run_id)
    data["reports"].append({"name": name, "file": file})
    write(run_id, data | more)


def done(run_id):
    """Every saved report, in the order they finished."""
    return [json.loads((RUNS / run_id / entry["file"]).read_text())
            for entry in manifest(run_id)["reports"]]


def finish(run_id, report):
    """The run's final report, next to its manifest."""
    (RUNS / run_id / "report.json").write_text(json.dumps(report, indent=1))


def report(run_id):
    return json.loads((RUNS / run_id / "report.json").read_text())

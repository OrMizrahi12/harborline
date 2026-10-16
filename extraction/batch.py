"""Extract a folder of supplier documents with the Message Batches API: half the price, no latency promise.

python -m extraction.batch data/invoices/batch

Supplier invoices must be in the books within 36 hours of arriving, and a batch can take up to 24 hours,
so a batch goes out every 8 hours: at most 8 hours until the next batch, 24 to process it, 4 to spare.
"""

import json
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from extraction.extract import EXTRACT_METADATA, RECORD_DOCUMENT, request
from extraction.validate import RETRY, Checked, finish, problems
from harborline.config import ROOT_DIR
from harborline.costs import estimate_cost

OUTPUT = ROOT_DIR / "runs" / "batch.jsonl"
cost = []


def run(client, requests):
    """Send one batch, wait until it has ended, and return each result by its custom_id."""
    batch = client.messages.batches.create(
        requests=[{"custom_id": custom_id, "params": params} for custom_id, params in requests.items()])
    print(f"batch {batch.id}: {len(requests)} requests")
    while batch.processing_status != "ended":
        time.sleep(60)
        batch = client.messages.batches.retrieve(batch.id)
    counts = batch.request_counts
    minutes = (batch.ended_at - batch.created_at).total_seconds() / 60
    print(f"  ended after {minutes:.0f} min: {counts.succeeded} succeeded, {counts.errored} errored, "
          f"{counts.expired} expired")
    results = {item.custom_id: item.result for item in client.messages.batches.results(batch.id)}
    for result in results.values():
        if result.type == "succeeded":
            usage = result.message.usage
            cost.append(estimate_cost(result.message.model, usage.input_tokens, usage.output_tokens, batch=True))
    return results


def tool_input(result):
    """The input Claude gave the tool, or why there is none."""
    if result.type != "succeeded":  # errored, canceled or expired
        return None, result.type
    if result.message.stop_reason == "max_tokens":  # the reply was cut off
        return None, "max_tokens"
    return next(block for block in result.message.content if block.type == "tool_use").input, "ok"


def parts(text, size=8):
    """Split a long line table into parts of 8 lines (they fit in MAX_TOKENS), each with the header and the totals."""
    lines = text.splitlines()
    top, bottom = [n for n, line in enumerate(lines) if line.startswith("---")][:2]
    rows = lines[top + 1:bottom]
    return ["\n".join(lines[:top + 1] + rows[i:i + size] + lines[bottom:]) for i in range(0, len(rows), size)]


def check(record):
    """The finished record if it passes the checks; otherwise the errors, for a retry."""
    try:
        Checked.model_validate(record)
    except ValidationError as error:
        return None, problems(error)
    return finish(record), None


def main(folder):
    client = anthropic.Anthropic()
    docs = {path.stem: path.read_text() for path in sorted(Path(folder).glob("*.txt"))}

    # 1. What is each document? custom_id is the document's id: results come back in any order.
    meta = {doc: tool_input(result)[0] for doc, result in
            run(client, {doc: request(text, EXTRACT_METADATA) for doc, text in docs.items()}).items()}
    done = {doc: (m or {}) | {"status": "skipped" if m else "review: no metadata"} for doc, m in meta.items()
            if not m or m["doc_type"] not in ("invoice", "credit_note")}
    todo = {doc: request(docs[doc], RECORD_DOCUMENT) for doc in meta if doc not in done}

    # 2. Record the rest; then resubmit only the custom_ids that failed, each with its fix.
    pieces = {}
    for attempt in (1, 2):
        retry = {}
        for custom_id, result in run(client, todo).items():
            doc = custom_id.split("_")[0]  # INV-0008_part2 belongs to INV-0008
            record, why = tool_input(result)
            if why == "ok" and custom_id != doc:
                pieces.setdefault(doc, {})[custom_id] = record
                continue
            if why == "ok":
                finished, errors = check(record)
                if finished:
                    done[doc] = meta[doc] | finished
                    continue
                why = "failed the checks"
                note = RETRY.format(errors=errors, output=json.dumps(record))
                retry[doc] = request(docs[doc], RECORD_DOCUMENT, note)
            elif why == "max_tokens":  # too long for one reply: send it in parts
                for n, part in enumerate(parts(docs[doc]), 1):
                    retry[f"{doc}_part{n}"] = request(part, RECORD_DOCUMENT)
            else:  # errored or expired: send it again as it was
                retry[custom_id] = todo[custom_id]
            print(f"{custom_id}: {why}")
            done[doc] = meta[doc] | (record or {}) | {"status": f"review: {why} on attempt {attempt}"}
        if not retry:
            break
        todo = retry

    # 3. A document sent in parts becomes one record again: the first part's fields, every part's lines.
    for doc, records in pieces.items():
        if len(records) < len(parts(docs[doc])):
            continue  # a part is missing: the document stays with a person
        ordered = [records[f"{doc}_part{n}"] for n in range(1, len(records) + 1)]
        record = ordered[0] | {"line_items": [item for part in ordered for item in part["line_items"]]}
        finished, errors = check(record)
        done[doc] = meta[doc] | (finished or record | {"status": "review: failed the checks"}) | {"parts": len(ordered)}

    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w") as out:
        for doc in sorted(done):
            out.write(json.dumps({"doc_id": doc} | done[doc]) + "\n")
    statuses = [record["status"] for record in done.values()]
    for status in sorted(set(statuses)):
        print(f"{statuses.count(status):3}  {status}")
    print(f"{len(done)} documents, ${sum(cost):.4f} at batch prices (half of ${2 * sum(cost):.4f}) -> {OUTPUT.name}")


if __name__ == "__main__":
    load_dotenv()  # ANTHROPIC_API_KEY from .env
    main(sys.argv[1])

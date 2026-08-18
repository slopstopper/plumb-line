#!/usr/bin/env python3
"""trigger_check — tiered skill-trigger measurement against the installed plugin.

Measures whether a skill's description makes Claude consult it: each query runs
through `claude -p` in a neutral empty directory, and a trigger is an invocation
of the Skill tool whose "skill" FIELD names the target (field match, not
substring — a query that merely mentions `plumb-line-audit.md` must not count).

Tokenomics is built in, because the naive version of this measurement is
ruinously expensive: every probe boots a full session (system prompt, plugin
metadata, tools) before the query arrives, so the per-probe cost is dominated
by fixed overhead at whatever tier you run. The harness therefore runs in two
tiers:

  1. SCREEN — every query once, on a small model (default haiku).
  2. CONFIRM — only queries the screen tier got "wrong" (contested), re-run
     on the session-tier model, more runs.

Trigger behavior differs by model, so a rate is only a claim about the model
that produced it: every reported rate carries a `measured_by` field, and a
confirmed row keeps its screen result visible instead of overwriting it.
(A 2026-08-18 run without these guards consumed a full usage window in
minutes; see #291.)

Usage (from repo root):

    python3 scripts/trigger_check.py evals/trigger/audit-queries.json \
        plumb-line-audit results.json \
        [--screen-model claude-haiku-4-5-20251001] [--confirm-model MODEL] \
        [--screen-runs 1] [--confirm-runs 2] [--workers 4] [--timeout 150]

Omitting --confirm-model skips the confirm tier: screen results stand, labeled
as such. The eval-set JSON is a list of {"query": str, "should_trigger": bool}.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

THRESHOLD = 0.5


# ---------- pure logic (covered by scripts/test_trigger_check.py) ----------

def skill_match(input_json, target):
    """True iff the Skill tool input's "skill" field names the target.

    Field match, never substring: the skill name may be plugin-qualified
    ("plugin:name"), but a target string appearing in args is not a trigger.
    """
    try:
        payload = json.loads(input_json)
    except (json.JSONDecodeError, TypeError):
        return False
    name = payload.get("skill", "")
    return name == target or name.endswith(":" + target)


def score(rows, threshold=THRESHOLD):
    """rows: [{"should_trigger": bool, "runs": [bool, ...], ...}] -> scored."""
    out = []
    for r in rows:
        rate = sum(1 for x in r["runs"] if x) / len(r["runs"])
        out.append({**r, "trigger_rate": rate,
                    "pass": (rate >= threshold) == r["should_trigger"]})
    return out


def contested(scored):
    """The queries whose screen verdict was a miss — the only ones worth
    re-measuring at a costlier tier."""
    return [r for r in scored if not r["pass"]]


def merge(screen, confirm, screen_model, confirm_model):
    """Combine tiers; every row says which model measured its verdict, and a
    confirmed row keeps the screen result on the record."""
    confirmed = {r["query"]: r for r in confirm}
    merged = []
    for r in screen:
        if r["query"] in confirmed:
            c = confirmed[r["query"]]
            merged.append({**c, "measured_by": confirm_model,
                           "screen": {"trigger_rate": r["trigger_rate"],
                                      "pass": r["pass"]}})
        else:
            merged.append({**r, "measured_by": screen_model})
    return merged


# ---------- probing ----------

def probe(query, target, model, workdir, timeout):
    cmd = ["claude", "-p", query, "--output-format", "stream-json",
           "--verbose", "--include-partial-messages", "--model", model,
           "--max-turns", "2"]
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         cwd=workdir, env=env)
    pending = False
    acc = ""
    start = time.time()
    try:
        for raw in p.stdout:
            if time.time() - start > timeout:
                break
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") != "stream_event":
                continue
            se = ev.get("event", {})
            t = se.get("type", "")
            if t == "content_block_start":
                cb = se.get("content_block", {})
                if cb.get("type") == "tool_use" and cb.get("name") == "Skill":
                    pending = True
                    acc = ""
            elif t == "content_block_delta" and pending:
                d = se.get("delta", {})
                if d.get("type") == "input_json_delta":
                    acc += d.get("partial_json", "")
            elif t == "content_block_stop" and pending:
                return skill_match(acc, target)  # first Skill call decides
            elif t == "message_stop":
                break
    finally:
        p.kill()
    return False


def run_tier(evals, target, model, runs, workers, timeout, log):
    workdir = tempfile.mkdtemp(prefix="trigger-check-")
    rows = [{"query": e["query"], "should_trigger": e["should_trigger"],
             "runs": []} for e in evals]
    jobs = [(i, r) for i in range(len(evals)) for r in range(runs)]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(probe, evals[i]["query"], target, model,
                          workdir, timeout): i for i, _ in jobs}
        for f in futs:
            i = futs[f]
            hit = f.result()
            rows[i]["runs"].append(hit)
            print(f"[{'TRIG' if hit else 'no  '}] {model} "
                  f"expected={evals[i]['should_trigger']}: "
                  f"{evals[i]['query'][:70]}", file=log, flush=True)
    return score(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("eval_set")
    ap.add_argument("target")
    ap.add_argument("out")
    ap.add_argument("--screen-model", default="claude-haiku-4-5-20251001")
    ap.add_argument("--confirm-model", default=None)
    ap.add_argument("--screen-runs", type=int, default=1)
    ap.add_argument("--confirm-runs", type=int, default=2)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=150)
    args = ap.parse_args(argv)

    evals = json.load(open(args.eval_set))
    screen = run_tier(evals, args.target, args.screen_model, args.screen_runs,
                      args.workers, args.timeout, sys.stderr)
    hot = contested(screen)
    if args.confirm_model and hot:
        confirm = run_tier(hot, args.target, args.confirm_model,
                           args.confirm_runs, args.workers, args.timeout,
                           sys.stderr)
        merged = merge(screen, confirm, args.screen_model, args.confirm_model)
    else:
        merged = [{**r, "measured_by": args.screen_model} for r in screen]
        if hot and not args.confirm_model:
            print(f"note: {len(hot)} contested at screen tier; no confirm "
                  f"model given, screen verdicts stand", file=sys.stderr)

    passed = sum(1 for r in merged if r["pass"])
    json.dump({"target": args.target,
               "tiers": {"screen": args.screen_model,
                         "confirm": args.confirm_model},
               "summary": {"passed": passed, "total": len(merged)},
               "results": merged}, open(args.out, "w"), indent=1)
    print(f"{args.target}: {passed}/{len(merged)} pass "
          f"({len(hot)} went to confirm tier)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

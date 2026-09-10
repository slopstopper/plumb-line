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

The results JSON is a durable measurement record and carries its contract
(#317): a `results-format` version key, the pass `threshold` the verdicts were
derived under (`--threshold`, default 0.5 — a judgment call, so it is injected
and stamped rather than buried), and the per-tier `runs` counts. Validate a
stored file with:

    python3 scripts/trigger_check.py --validate results.json

which re-derives every row's verdict from its rate, the stamped threshold and
its expectation, so a stored pass is reproducible rather than asserted.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

# Pass threshold on the trigger rate: a query "triggers" when at least this
# fraction of its runs invoked the target. 0.5 is a judgment call with no
# derivation behind it (P5), so it is CLI-injectable and stamped into every
# results file rather than silently assumed by the reader.
THRESHOLD = 0.5

# The results file's contract (P7: version constant + key list + validator).
#   v1  #317 — first versioned shape: results-format, target, probed_installs,
#       tiers, runs, threshold, summary, results.
RESULTS_FORMAT = "v1"
KNOWN_RESULTS_FORMATS = {"v1"}
RESULTS_KEYS = ["results-format", "target", "probed_installs", "tiers", "runs",
                "threshold", "summary", "results"]


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


def skill_name(input_json):
    """The "skill" field of a Skill-tool input, or None. Lets a miss say
    which skill won instead of only that the target lost."""
    try:
        payload = json.loads(input_json)
    except (json.JSONDecodeError, TypeError):
        return None
    return payload.get("skill") or None


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


def build_payload(target, installs, tiers, runs, threshold, merged):
    """The results record, in RESULTS_KEYS order, contract key first."""
    passed = sum(1 for r in merged if r["pass"])
    return {"results-format": RESULTS_FORMAT,
            "target": target,
            "probed_installs": installs,
            "tiers": tiers,
            "runs": runs,
            "threshold": threshold,
            "summary": {"passed": passed, "total": len(merged)},
            "results": merged}


def validate_results(payload):
    """Issues with a stored results record; [] when it conforms.

    Beyond shape: every row's `pass` is re-derived from its `trigger_rate`,
    the stamped `threshold` and its `should_trigger`, and the summary is
    re-counted — a record whose verdicts cannot be reproduced from its own
    numbers is asserting, not measuring.
    """
    issues = []
    if not isinstance(payload, dict):
        return ["results file is not a JSON object"]
    for key in RESULTS_KEYS:
        if key not in payload:
            issues.append(f"missing required key: {key}")
    fmt = payload.get("results-format")
    if fmt is not None and fmt not in KNOWN_RESULTS_FORMATS:
        issues.append(f"unknown results-format {fmt!r} "
                      f"(this harness models {sorted(KNOWN_RESULTS_FORMATS)})")
    threshold = payload.get("threshold")
    # bool is an int subclass: a hand-edited `"threshold": true` must not
    # validate as 1.
    if threshold is not None and not (isinstance(threshold, (int, float))
                                      and not isinstance(threshold, bool)
                                      and 0 < threshold <= 1):
        issues.append(f"threshold must be a number in (0, 1], got {threshold!r}")
    rows = payload.get("results")
    if not isinstance(rows, list):
        return issues
    passed = 0
    for n, r in enumerate(rows, start=1):
        for key in ("query", "should_trigger", "trigger_rate", "pass", "measured_by"):
            if key not in r:
                issues.append(f"row {n}: missing {key}")
        if isinstance(threshold, (int, float)) and all(
                k in r for k in ("should_trigger", "trigger_rate", "pass")):
            expected = (r["trigger_rate"] >= threshold) == r["should_trigger"]
            if r["pass"] != expected:
                issues.append(f"row {n}: pass={r['pass']} but rate "
                              f"{r['trigger_rate']} against threshold {threshold} "
                              f"with should_trigger={r['should_trigger']} gives "
                              f"{expected}")
        if r.get("pass"):
            passed += 1
    summary = payload.get("summary")
    if isinstance(summary, dict) and summary != {"passed": passed, "total": len(rows)}:
        issues.append(f"summary {summary} does not match the rows "
                      f"({passed} passed of {len(rows)})")
    return issues


PLUGINS_ROOT = os.path.expanduser("~/.claude/plugins/cache")


def installed_locations(target, plugins_root=PLUGINS_ROOT):
    """Where the target skill is actually installed: [{plugin, version}].

    The probe sessions see only installed plugins, so a target missing here
    yields structural zeros that say nothing about its description. The
    2026-08-18 run measured exactly that and read as a trigger gap; this
    preflight makes absence loud and stamps results with what was probed.
    """
    hits = []
    if not os.path.isdir(plugins_root):
        return hits
    for owner in sorted(os.listdir(plugins_root)):
        owner_dir = os.path.join(plugins_root, owner)
        if not os.path.isdir(owner_dir):
            continue
        for plugin in sorted(os.listdir(owner_dir)):
            plugin_dir = os.path.join(owner_dir, plugin)
            if not os.path.isdir(plugin_dir):
                continue
            for version in sorted(os.listdir(plugin_dir)):
                if os.path.isdir(os.path.join(plugin_dir, version,
                                              "skills", target)):
                    hits.append({"plugin": f"{owner}/{plugin}",
                                 "version": version})
    return hits


def _semver(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return None


def stale_installs(installs, current_version):
    """Installs whose version parses lower than current_version.

    Plugin updates are manual and easy to miss (#295): the owner's install
    sat two releases behind and a whole measurement run probed a plugin
    missing the skill under test. Unknown version formats are not flagged —
    unparseable means unknown, never stale.
    """
    cur = _semver(current_version)
    if cur is None:
        return []
    return [i for i in installs
            if (_semver(i.get("version")) or cur) < cur]


def repo_version():
    """This repo's release version, from .claude-plugin/plugin.json."""
    manifest = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), ".claude-plugin", "plugin.json")
    try:
        with open(manifest, encoding="utf-8") as f:
            return json.load(f).get("version")
    except (OSError, json.JSONDecodeError):
        return None


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
                # first Skill call decides; report who won either way
                return skill_match(acc, target), skill_name(acc)
            elif t == "message_stop":
                break
    finally:
        p.kill()
    return False, None


def run_tier(evals, target, model, runs, workers, timeout, log, threshold=THRESHOLD):
    workdir = tempfile.mkdtemp(prefix="trigger-check-")
    rows = [{"query": e["query"], "should_trigger": e["should_trigger"],
             "runs": [], "winners": []} for e in evals]
    jobs = [(i, r) for i in range(len(evals)) for r in range(runs)]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(probe, evals[i]["query"], target, model,
                          workdir, timeout): i for i, _ in jobs}
        for f in futs:
            i = futs[f]
            hit, winner = f.result()
            rows[i]["runs"].append(hit)
            rows[i]["winners"].append(winner)
            print(f"[{'TRIG' if hit else 'no  '}] {model} "
                  f"expected={evals[i]['should_trigger']} "
                  f"winner={winner or '-'}: "
                  f"{evals[i]['query'][:70]}", file=log, flush=True)
    return score(rows, threshold)


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("eval_set", nargs="?")
    ap.add_argument("target", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--screen-model", default="claude-haiku-4-5-20251001")
    ap.add_argument("--confirm-model", default=None)
    ap.add_argument("--screen-runs", type=int, default=1)
    ap.add_argument("--confirm-runs", type=int, default=2)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=150)
    ap.add_argument("--threshold", type=float, default=THRESHOLD,
                    help=f"pass threshold on the trigger rate, in (0, 1] "
                         f"(default {THRESHOLD}); stamped into the results")
    ap.add_argument("--force", action="store_true",
                    help="probe even if the target skill is not installed")
    ap.add_argument("--validate", metavar="RESULTS_JSON",
                    help="validate a stored results file against the contract "
                         "and exit; no probing")
    args = ap.parse_args(argv)
    if args.validate is None and not (args.eval_set and args.target and args.out):
        ap.error("eval_set, target and out are required unless --validate is given")
    if not 0 < args.threshold <= 1:
        ap.error(f"--threshold must be in (0, 1], got {args.threshold}")
    return args


def main(argv=None):
    args = parse_args(argv)

    if args.validate:
        try:
            with open(args.validate, encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"✗ {args.validate}: cannot read as JSON ({exc})", file=sys.stderr)
            return 1
        issues = validate_results(payload)
        for issue in issues:
            print(f"✗ {args.validate}: {issue}", file=sys.stderr)
        if issues:
            return 1
        print(f"✓ {args.validate}: conforms to results-format "
              f"{payload['results-format']} (threshold {payload['threshold']}, "
              f"{payload['summary']['passed']}/{payload['summary']['total']} pass)",
              file=sys.stderr)
        return 0

    installs = installed_locations(args.target)
    if not installs and not args.force:
        print(f"ABORT: skill '{args.target}' is not installed in any plugin "
              f"under {PLUGINS_ROOT} — probes would measure its absence, not "
              f"its description. Install/update the plugin, or pass --force "
              f"to measure anyway.", file=sys.stderr)
        return 2
    print(f"probing installs: {installs or 'NONE (--force)'}", file=sys.stderr)
    current = repo_version()
    for s in stale_installs(installs, current) if current else []:
        print(f"WARNING: probing {s['plugin']}@{s['version']} but this repo "
              f"is at {current} — plugin updates are manual and easy to miss "
              f"(claude plugin update {s['plugin'].split('/')[-1]}); results "
              f"will describe the stale install (#295).", file=sys.stderr)

    evals = json.load(open(args.eval_set))
    screen = run_tier(evals, args.target, args.screen_model, args.screen_runs,
                      args.workers, args.timeout, sys.stderr, args.threshold)
    hot = contested(screen)
    if args.confirm_model and hot:
        confirm = run_tier(hot, args.target, args.confirm_model,
                           args.confirm_runs, args.workers, args.timeout,
                           sys.stderr, args.threshold)
        merged = merge(screen, confirm, args.screen_model, args.confirm_model)
    else:
        merged = [{**r, "measured_by": args.screen_model} for r in screen]
        if hot and not args.confirm_model:
            print(f"note: {len(hot)} contested at screen tier; no confirm "
                  f"model given, screen verdicts stand", file=sys.stderr)

    payload = build_payload(args.target, installs,
                            {"screen": args.screen_model,
                             "confirm": args.confirm_model},
                            # Confirm runs are stamped only when the tier
                            # actually executed: a model named but never
                            # invoked (nothing contested) is 0, so the record
                            # does not imply a tier that did not run.
                            {"screen": args.screen_runs,
                             "confirm": args.confirm_runs if (args.confirm_model and hot) else 0},
                            args.threshold, merged)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    passed = payload["summary"]["passed"]
    print(f"{args.target}: {passed}/{len(merged)} pass at threshold "
          f"{args.threshold} ({len(hot)} went to confirm tier); "
          f"results-format {RESULTS_FORMAT} -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

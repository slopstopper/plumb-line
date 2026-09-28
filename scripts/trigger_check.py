#!/usr/bin/env python3
"""trigger_check — tiered skill-trigger measurement against the installed plugin,
or an isolated checkout (--plugin-dir).

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
        [--screen-runs 1] [--confirm-runs 2] [--workers 4] [--timeout 150] \
        [--plugin-dir .]

--plugin-dir probes that checkout instead of the installed plugin, with
ISOLATION_FLAGS keeping the user's plugins, their SessionStart hooks and MCP
servers out. The record carries the flags (`probe.isolation_flags`) and what
each session reported loading (`environments`, results-format v3).

Omitting --confirm-model skips the confirm tier: screen results stand, labeled
as such. The eval-set JSON is a list of {"query": str, "should_trigger": bool}.

The results JSON is a durable measurement record and carries its contract
(#317, #400): a `results-format` version key, the pass `threshold` the verdicts
were derived under (`--threshold`, default 0.5 — a judgment call, so it is
injected and stamped rather than buried), the per-tier `runs` counts, and the
`probe` settings that change verdicts (`timeout_s`, since a timed-out run
records as a non-trigger, and `max_turns`). Validate a stored file with:

    python3 scripts/trigger_check.py --validate results.json

which re-derives every row's verdict from its rate, the stamped threshold and
its expectation, so a stored verdict is consistent with its own numbers rather
than asserted, and checks the environment each probe reported (see
_environment_issues). The record carries the settings that decide a verdict
and the `claude` CLI version each probe reported; it does not record
`--workers` (concurrency can push a probe past its timeout) or model
sampling, so a re-run is not guaranteed to reproduce the same rates.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
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
#   v2  #400 — adds `probe`: {timeout_s, max_turns}, the two probe settings
#       that change verdicts. v1 is refused: it cannot say what they were.
#   v3  #487 — `probe` adds `isolation_flags` (the CLI flags that kept the
#       user's environment out, [] for none), and a new `environments` key
#       records what each probe session reported loading (CLI version,
#       plugins, skills, MCP servers and plugin errors, from its init event),
#       and --validate checks it: the target loaded, no plugin errors, no MCP
#       server in an isolated run, one environment, every probe reporting.
#       On the owner's machine the
#       default environment was 19 plugins, 9 SessionStart hooks (superpowers'
#       tells the model to invoke a skill on even a 1% chance it applies) and
#       3 claude.ai connectors. v2 is refused: it records neither.
RESULTS_FORMAT = "v3"
KNOWN_RESULTS_FORMATS = {"v3"}

# --plugin-dir isolation, the flags the impossible-task spike used
# (docs/validation-results.md): user and local settings (enabledPlugins, their
# hooks) and every MCP server or connector stay out. Claude Code's built-in
# plugins (agents-md, telemetry) still load; `environments` shows them.
ISOLATION_FLAGS = ["--setting-sources", "project", "--strict-mcp-config"]
RESULTS_KEYS = ["results-format", "target", "probed_installs", "tiers", "runs",
                "threshold", "probe", "environments", "summary", "results"]

# Turn cap for each probe session. A Skill call must happen within it, so it
# bounds what can count as a trigger; stamped into every results file.
MAX_TURNS = 2


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


def summarise_environments(envs, unreplied=0):
    """Per-probe observed environments (None when a probe never reported
    one) -> {"observed": [{...environment, probes}], "unobserved_probes": n,
    "unreplied_probes": m}, one entry per distinct environment, so a record
    whose probes ran in different environments says so instead of averaging
    over them. unreplied counts probes whose model reply never began."""
    counts = {}
    for env in envs:
        if env is None:
            continue
        key = json.dumps(env, sort_keys=True)
        counts[key] = counts.get(key, 0) + 1
    return {"observed": [{**json.loads(k), "probes": n}
                         for k, n in sorted(counts.items())],
            "unobserved_probes": sum(1 for e in envs if e is None),
            "unreplied_probes": unreplied}


def build_payload(target, installs, tiers, runs, threshold, timeout, merged,
                  isolation_flags, environments):
    """The results record, in RESULTS_KEYS order, contract key first.
    isolation_flags and environments have no defaults: a record that forgot
    them would silently claim the wrong environment."""
    passed = sum(1 for r in merged if r["pass"])
    return {"results-format": RESULTS_FORMAT,
            "target": target,
            "probed_installs": installs,
            "tiers": tiers,
            "runs": runs,
            "threshold": threshold,
            "probe": {"timeout_s": timeout, "max_turns": MAX_TURNS,
                      "isolation_flags": list(isolation_flags)},
            "environments": environments,
            "summary": {"passed": passed, "total": len(merged)},
            "results": merged}


def _count(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _env_shape_ok(e):
    return (isinstance(e, dict)
            and set(e) == {"claude_code_version", *ENV_LISTS, "probes"}
            and (e["claude_code_version"] is None
                 or isinstance(e["claude_code_version"], str))
            and all(e[k] is None or (isinstance(e[k], list)
                                     and all(isinstance(x, str) for x in e[k]))
                    for k in ENV_LISTS)
            and _count(e["probes"]) and e["probes"] > 0)


def _environment_issues(envs, target, isolation_flags, installs=()):
    """What the probe sessions reported loading, checked rather than only
    recorded. A rate is refused unless every probe reported an environment
    and got a reply, the probes shared one environment, and the target skill
    loaded in it; an isolated run must also show no MCP server, no plugin
    error, and the probed checkout among its plugins. Otherwise a non-trigger
    may measure a skill that never loaded (the 2026-08-18 failure), a session
    that failed, or an environment the record does not claim.

    Default mode compares only what decides a trigger (CLI version, plugins,
    skills): a user's connector changing status mid-run, or an unrelated
    plugin's error, is recorded but does not void a paid-for run."""
    if envs is None:
        return []  # a missing key is reported by the RESULTS_KEYS check
    if not (isinstance(envs, dict)
            and set(envs) == {"observed", "unobserved_probes", "unreplied_probes"}
            and all(_count(envs[k]) and envs[k] >= 0
                    for k in ("unobserved_probes", "unreplied_probes"))
            and isinstance(envs["observed"], list)
            and all(_env_shape_ok(e) for e in envs["observed"])):
        return ["environments must be {observed: [{claude_code_version, "
                "plugins, skills, mcp_servers, plugin_errors, probes}], "
                "unobserved_probes: n, unreplied_probes: n}, got " + repr(envs)]
    issues = []
    observed = envs["observed"]
    if not observed:
        return ["environments: no probe reported the environment it ran in, "
                "so the rates describe no known session"]
    if not isinstance(target, str) or not target:
        issues.append(f"target must name a skill, got {target!r}")
    if envs["unobserved_probes"]:
        issues.append(f"environments: {envs['unobserved_probes']} probe(s) never "
                      "reported an environment, so their non-triggers may be "
                      "failures to start")
    if envs["unreplied_probes"]:
        issues.append(f"environments: {envs['unreplied_probes']} probe(s) started "
                      "but got no reply from the model (a usage limit, overload "
                      "or expired login, say), so their non-triggers measure the "
                      "failure, not the description")
    decisive = (lambda e: {k: v for k, v in e.items() if k != "probes"}) \
        if isolation_flags else \
        (lambda e: (e["claude_code_version"], e["plugins"], e["skills"]))
    if len({json.dumps(decisive(e), sort_keys=True) for e in observed}) > 1:
        issues.append(f"environments: probes ran in {len(observed)} different "
                      "environments, so one rate averages over them")
    probed = [i.get("plugin") for i in installs
              if isinstance(i, dict) and i.get("path")]
    for n, e in enumerate(observed, start=1):
        if e["skills"] is None:
            issues.append(f"environment {n}: the sessions did not report their "
                          "skills, so the target cannot be shown to have loaded")
        elif isinstance(target, str) and target and not any(
                s == target or s.endswith(":" + target) for s in e["skills"]):
            issues.append(f"environment {n}: the target skill {target!r} did not "
                          "load, so every non-trigger measures its absence")
        if not isolation_flags:
            continue
        if e["plugin_errors"]:
            issues.append(f"environment {n}: plugin errors {e['plugin_errors']}")
        if e["mcp_servers"] is None:
            issues.append(f"environment {n}: an isolated run did not report its "
                          "MCP servers, so it cannot be shown to have none")
        elif e["mcp_servers"]:
            issues.append(f"environment {n}: an isolated run reported MCP servers "
                          f"{e['mcp_servers']}")
        missing = [p for p in probed if e["plugins"] is None or p not in e["plugins"]]
        if missing:
            issues.append(f"environment {n}: the probed checkout {missing} is not "
                          "among the plugins the sessions loaded")
    return issues


def _probe_count_issues(payload):
    """The environments' probe counts must add up to the runs the record
    implies, or a trimmed or edited record could claim every probe reported
    when most never did."""
    envs, runs, rows = (payload.get(k) for k in ("environments", "runs", "results"))
    try:
        expected = (runs["screen"] * len(rows)
                    + runs["confirm"] * sum(1 for r in rows if "screen" in r))
        counted = (sum(e["probes"] for e in envs["observed"])
                   + envs["unobserved_probes"])
    except (TypeError, KeyError):
        return []  # malformed; reported by the shape checks
    if counted != expected:
        return [f"environments account for {counted} probes but the runs and "
                f"rows imply {expected}"]
    return []


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
    if fmt == "v1":
        issues.append("results-format 'v1' does not record the probe timeout or "
                      "turn cap, so the conditions its verdicts were measured "
                      f"under are unknown; re-run to get a {RESULTS_FORMAT} record")
    elif fmt == "v2":
        issues.append("results-format 'v2' does not record the environment its "
                      "probes ran in (the plugins, skills and MCP servers each "
                      "session reported), which moves trigger rates; re-run to "
                      f"get a {RESULTS_FORMAT} record")
    elif fmt is not None and fmt not in KNOWN_RESULTS_FORMATS:
        issues.append(f"unknown results-format {fmt!r} "
                      f"(this harness models {sorted(KNOWN_RESULTS_FORMATS)})")
    probe = payload.get("probe")
    if probe is not None and not (
            isinstance(probe, dict)
            and set(probe) == {"timeout_s", "max_turns", "isolation_flags"}
            and all(isinstance(probe[k], int) and not isinstance(probe[k], bool)
                    and probe[k] > 0 for k in ("timeout_s", "max_turns"))
            and isinstance(probe["isolation_flags"], list)
            and all(isinstance(f, str) for f in probe["isolation_flags"])):
        issues.append("probe must be {timeout_s, max_turns, isolation_flags}: "
                      "two positive integers and a list of strings, "
                      f"got {probe!r}")
    flags = probe.get("isolation_flags") if isinstance(probe, dict) else None
    issues += _environment_issues(payload.get("environments"),
                                  payload.get("target"), flags,
                                  payload.get("probed_installs") or [])
    issues += _probe_count_issues(payload)
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


def _frontmatter(skill_md):
    """A SKILL.md's frontmatter text (between the first two lines that are
    exactly `---`), or None when the file is unreadable or has none. A
    leading BOM is dropped; line endings are normalised."""
    try:
        with open(skill_md, encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            return "\n".join(lines[1:end]).strip()
    return None


def frontmatter_sha256(skill_md):
    """sha256 of a SKILL.md's frontmatter (name and description), or None.
    Two runs on one checkout share its path and version; this is what tells
    a before-record from an after-record when only the description changed."""
    fm = _frontmatter(skill_md)
    return None if fm is None else hashlib.sha256(fm.encode("utf-8")).hexdigest()


def skills_frontmatter_sha256(plugin_dir):
    """sha256 over every skill's frontmatter in a checkout, in name order.
    Sibling descriptions compete for the same queries (adopt and method both
    claim a mock near a production path), so a sibling's edit changes what a
    run measures even when the target's own frontmatter is unchanged."""
    root = os.path.join(plugin_dir, "skills")
    h = hashlib.sha256()
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        fm = _frontmatter(os.path.join(root, name, "SKILL.md"))
        if fm is not None:
            h.update(f"{name}\0{fm}\0".encode("utf-8"))
    return h.hexdigest()


def plugin_dir_install(target, plugin_dir):
    """The checkout a --plugin-dir run probes, as a probed_installs entry:
    [{plugin, version, path, frontmatter_sha256, skills_frontmatter_sha256}],
    or [] when it has no skills/<target>, so the same absence guard applies
    as for an installed plugin."""
    skill_dir = os.path.join(plugin_dir, "skills", target)
    if not os.path.isdir(skill_dir):
        return []
    try:
        with open(os.path.join(plugin_dir, ".claude-plugin", "plugin.json"),
                  encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError):
        manifest = {}
    return [{"plugin": f"{manifest.get('name', '?')}@inline",
             "version": manifest.get("version"), "path": plugin_dir,
             "frontmatter_sha256": frontmatter_sha256(
                 os.path.join(skill_dir, "SKILL.md")),
             "skills_frontmatter_sha256": skills_frontmatter_sha256(plugin_dir)}]


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

def probe_cmd(query, model, plugin_dir=None):
    cmd = ["claude", "-p", query, "--output-format", "stream-json",
           "--verbose", "--include-partial-messages", "--model", model,
           "--max-turns", str(MAX_TURNS)]
    if plugin_dir:
        # Isolation is not optional here: without it the checkout loads
        # beside the installed copy of the same plugin, and the user's other
        # plugins' SessionStart hooks and connectors run in every probe (#487).
        cmd += ["--plugin-dir", plugin_dir, *ISOLATION_FLAGS]
    return cmd


ENV_LISTS = ("plugins", "skills", "mcp_servers", "plugin_errors")


def init_environment(ev):
    """The environment a session reports in its system/init event, else None:
    {claude_code_version, plugins, skills, mcp_servers, plugin_errors}. A list
    the event does not carry, or carries in an unexpected shape, is None
    (unknown), never [] (nothing loaded): an older CLI must not read as a
    clean room."""
    if ev.get("type") != "system" or ev.get("subtype") != "init":
        return None

    def entries(items, render):
        if not isinstance(items, list):
            return None
        return sorted(render(i) for i in items)

    def plugin(i):
        if isinstance(i, dict):
            return str(i.get("source") or i.get("name") or json.dumps(i, sort_keys=True))
        return str(i)

    def server(i):
        # A failed or unauthenticated server is not a loaded one: keep status.
        if isinstance(i, dict):
            return f"{i.get('name')} ({i.get('status', 'status unknown')})"
        return str(i)

    def as_json(i):
        return i if isinstance(i, str) else json.dumps(i, sort_keys=True)

    version = ev.get("claude_code_version")
    return {"claude_code_version": version if isinstance(version, str) else None,
            "plugins": entries(ev.get("plugins"), plugin),
            "skills": entries(ev.get("skills"), as_json),
            "mcp_servers": entries(ev.get("mcp_servers"), server),
            "plugin_errors": entries(ev.get("plugin_errors"), as_json)}


def probe(query, target, model, workdir, timeout, plugin_dir=None):
    """(hit, winner, environment, replied).

    environment is what the session reported loading, or None if it never
    reported (it failed to start). replied is whether the model's reply ever
    began streaming: a session that starts and then fails (usage limit,
    overload, expired login) reports an environment but no reply, and its
    non-trigger measures the failure, not the description."""
    cmd = probe_cmd(query, model, plugin_dir)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         cwd=workdir, env=env)
    # The loop below only checks the clock when a line arrives, so a CLI that
    # hangs silently would block forever; the watchdog kills it on time.
    watchdog = threading.Timer(timeout, p.kill)
    watchdog.daemon = True
    watchdog.start()
    pending = False
    replied = False
    acc = ""
    env_seen = None
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
            env_seen = env_seen or init_environment(ev)
            if ev.get("type") != "stream_event":
                continue
            se = ev.get("event", {})
            t = se.get("type", "")
            if t == "message_start":
                replied = True
            elif t == "content_block_start":
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
                return skill_match(acc, target), skill_name(acc), env_seen, True
            elif t == "message_stop":
                break
    finally:
        watchdog.cancel()
        p.kill()
    return False, None, env_seen, replied


def run_tier(evals, target, model, runs, workers, timeout, log, threshold=THRESHOLD,
             plugin_dir=None):
    """(scored rows, per-probe observed environments, per-probe replied)."""
    workdir = tempfile.mkdtemp(prefix="trigger-check-")
    envs = []
    replies = []
    rows = [{"query": e["query"], "should_trigger": e["should_trigger"],
             "runs": [], "winners": []} for e in evals]
    jobs = [(i, r) for i in range(len(evals)) for r in range(runs)]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(probe, evals[i]["query"], target, model,
                          workdir, timeout, plugin_dir): i for i, _ in jobs}
        for f in futs:
            i = futs[f]
            hit, winner, env, replied = f.result()
            envs.append(env)
            replies.append(replied)
            rows[i]["runs"].append(hit)
            rows[i]["winners"].append(winner)
            print(f"[{'TRIG' if hit else 'no  '}] {model} "
                  f"expected={evals[i]['should_trigger']} "
                  f"winner={winner or '-'}: "
                  f"{evals[i]['query'][:70]}", file=log, flush=True)
    return score(rows, threshold), envs, replies


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
    ap.add_argument("--plugin-dir", default=None,
                    help="probe this plugin checkout instead of the installed "
                         "plugin, with " + " ".join(ISOLATION_FLAGS) + " so "
                         "the user's plugins, hooks and MCP servers stay out; "
                         "the record carries the flags and what each session "
                         "reported loading")
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
    if args.timeout <= 0:
        ap.error(f"--timeout must be a positive number of seconds, got {args.timeout}")
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

    plugin_dir = os.path.abspath(args.plugin_dir) if args.plugin_dir else None
    if plugin_dir:
        if not os.path.isdir(plugin_dir):
            # Not overridable by --force: claude would fail to start and every
            # probe would record a silent non-trigger.
            print(f"ABORT: --plugin-dir {plugin_dir} is not a directory.",
                  file=sys.stderr)
            return 2
        installs = plugin_dir_install(args.target, plugin_dir)
        fix = f"check that {plugin_dir}/skills/{args.target} exists"
    else:
        installs = installed_locations(args.target)
        fix = "install or update the plugin"
    if not installs and not args.force:
        print(f"ABORT: skill '{args.target}' is not in "
              f"{'the checkout ' + plugin_dir if plugin_dir else 'any plugin under ' + PLUGINS_ROOT}"
              f" — probes would measure its absence, not its description. "
              f"{fix[0].upper() + fix[1:]}, or pass --force to measure anyway.",
              file=sys.stderr)
        return 2
    isolation = ISOLATION_FLAGS if plugin_dir else []
    print(f"probing installs: {installs or 'NONE (--force)'}"
          f"{' (isolated: ' + ' '.join(isolation) + ')' if isolation else ''}",
          file=sys.stderr)
    current = repo_version()
    # A checkout is chosen, not updated: an older --plugin-dir is a deliberate
    # "before" run, and `claude plugin update` would be wrong advice for it.
    for s in (stale_installs(installs, current) if current and not plugin_dir else []):
        print(f"WARNING: probing {s['plugin']}@{s['version']} but this repo "
              f"is at {current} — plugin updates are manual and easy to miss "
              f"(claude plugin update {s['plugin'].split('/')[-1]}); results "
              f"will describe the stale install (#295).", file=sys.stderr)

    evals = json.load(open(args.eval_set))
    screen, envs, replies = run_tier(evals, args.target, args.screen_model,
                                     args.screen_runs, args.workers, args.timeout,
                                     sys.stderr, args.threshold, plugin_dir)
    hot = contested(screen)
    if args.confirm_model and hot:
        confirm, confirm_envs, confirm_replies = run_tier(
            hot, args.target, args.confirm_model, args.confirm_runs,
            args.workers, args.timeout, sys.stderr, args.threshold, plugin_dir)
        envs = envs + confirm_envs
        replies = replies + confirm_replies
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
                            args.threshold, args.timeout, merged,
                            isolation, summarise_environments(
                                envs, unreplied=sum(1 for r in replies if not r)))
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    passed = payload["summary"]["passed"]
    print(f"{args.target}: {passed}/{len(merged)} pass at threshold "
          f"{args.threshold} ({len(hot)} went to confirm tier); "
          f"results-format {RESULTS_FORMAT} -> {args.out}", file=sys.stderr)
    # The record is written either way, as evidence; but a run whose own
    # record fails validation (the target never loaded, probes never started,
    # a mixed environment) is not a measurement, and must not exit 0.
    issues = validate_results(payload)
    for issue in issues:
        print(f"✗ {args.out}: {issue}", file=sys.stderr)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())

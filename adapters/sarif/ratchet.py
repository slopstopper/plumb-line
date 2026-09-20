#!/usr/bin/env python3
"""ratchet.py — the provenance ratchet (#119, ROADMAP #26, ADR-0017).

A legacy repo cannot turn require-provenance-output on: every existing site
fails at once. The ratchet pins today's untagged output SITES (file::symbol)
in a committed file and refuses only NEW ones: "don't demand zero, refuse
regression". It is a debt register with a direction, never a grade.

    .plumb-line/ratchet.json   (ratchet-format v1; path named by the manifest)

Three parties touch it:
  - run_checks.py READS it (apply): a pinned site is a `note`, an unpinned
    site stays an `error`, a pinned site no longer reported is a
    PL/ratchet-stale note. The runner never writes.
  - `ratchet.py update --because "..."` WRITES it: sets the sites to what is
    reported now; a reason is required because the set may have grown.
  - `ratchet.py prune` WRITES it: removes stale sites only; no reason needed.

The manifest validator does not check this file exists — `update` creates
it; the runner is what fails on absence (PL/ratchet-invalid).

P7 contract: version constant + key lists + validator. Stdlib only.
"""
import argparse
import datetime
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from adapters.sarif import assemble as A  # noqa: E402

RATCHET_FORMAT = "v1"
KNOWN_RATCHET_FORMATS = {"v1"}
KEYS = ["ratchet-format", "sites", "history"]
OUTPUT_CAPS = ("js.output", "python.output")
_HISTORY_KEYS = {"date", "because", "change"}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# The two state notes run_checks.py writes for a `ran` output capability that
# measured nothing after all. Either one proves nothing about its sites.
NO_MATCH_NOTE = "no files matched the globs"
# #392: prefix + the surface files the tool could not read. Unmeasurability is
# per FILE, not per tool: one file inside the surface that ESLint or
# provenance_lint.py could not parse is one the output check never ran on, so
# the whole capability is unmeasured. Without this, `update` pins a set
# computed as though that file held no sites and `prune` erases the ones it
# used to hold — a silent shrink of the debt register.
UNPARSED_PREFIX = "unparsed surface file: "

KNOWN_PREFIX = "known (ratchet): "
NEW_SUFFIX = (" New untagged output (ratchet): wrap it with derive()/mark(), or accept it with: "
              'python3 <plumb-line>/adapters/sarif/ratchet.py update --because "..."')
STALE_TEXT = "stale ratchet entry: {site} is no longer reported; run ratchet.py prune"
DROPPED_TEXT = "stale ratchet entry: {cap} is pinned but the manifest no longer enforces it; run ratchet.py update"
BECAUSE_REQUIRED = "update requires `because`: a non-empty explanation of why the new state is correct"


def empty():
    return {"ratchet-format": RATCHET_FORMAT, "sites": {}, "history": []}


# ---------- contract ----------

def _site_problem(s):
    if not isinstance(s, str) or "::" not in s:
        return "must be a string of the form <file>::<symbol>"
    file, _, sym = s.partition("::")
    if not file or not sym:
        return "must be a string of the form <file>::<symbol>"
    if file.startswith("/") or os.path.isabs(file) or ".." in file.split("/"):
        return "file must be a relative path inside the repository"
    return None


def validate_ratchet(data):
    """Problems with a parsed ratchet file; [] when valid. Never raises."""
    if not isinstance(data, dict):
        return ["ratchet file is not a JSON object"]
    p = []
    for k in data:
        if k not in KEYS:
            p.append(f"unknown key: {k}")
    fmt = data.get("ratchet-format")
    if fmt not in KNOWN_RATCHET_FORMATS:
        p.append(f"unknown ratchet-format {json.dumps(fmt)} (this validator models {sorted(KNOWN_RATCHET_FORMATS)})")
    sites = data.get("sites")
    if not isinstance(sites, dict):
        p.append("sites must be an object keyed by output capability")
    else:
        for cap, lst in sites.items():
            if cap not in OUTPUT_CAPS:
                p.append(f"sites.{cap}: not an output capability (one of {list(OUTPUT_CAPS)})")
                continue
            if not isinstance(lst, list):
                p.append(f"sites.{cap} must be a list")
                continue
            for s in lst:
                why = _site_problem(s)
                if why:
                    p.append(f"sites.{cap}: {json.dumps(s)} {why}")
            if all(isinstance(s, str) for s in lst) and lst != sorted(set(lst)):
                p.append(f"sites.{cap} must be sorted and unique")
    hist = data.get("history")
    if not isinstance(hist, list):
        p.append("history must be a list")
    else:
        for i, h in enumerate(hist):
            if not isinstance(h, dict) or set(h) != _HISTORY_KEYS:
                p.append(f"history[{i}] must have exactly the keys date, because, change")
                continue
            if not isinstance(h["date"], str) or not _DATE.match(h["date"]):
                p.append(f"history[{i}].date must be YYYY-MM-DD")
            if not isinstance(h["because"], str) or not h["because"].strip():
                p.append(f"history[{i}].because must be a non-empty string")
            if not isinstance(h["change"], str) or not h["change"].strip():
                p.append(f"history[{i}].change must be a non-empty string")
    return p


def load_ratchet(path):
    """(data, problems). data is None when missing, unparsable or invalid."""
    if not os.path.isfile(path):
        return None, [f"ratchet file not found: {path}"]
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        return None, [f"cannot parse {path}: {e}"]
    p = validate_ratchet(data)
    return (data if not p else None), p


def dumps(data):
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def write_ratchet(path, data):
    """Canonical, atomic: tmp + os.replace, so a crash leaves the old file.

    If writing or replacing raises (disk full, permission), the tmp file is
    unlinked before the exception propagates — it must never linger inside
    .plumb-line/ where it could be committed."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(dumps(data))
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass  # tmp was never created, or is already gone — fine either way
        raise


# ---------- apply (read-only) ----------

def site_of(r):
    return f"{r['file']}::{r['site']}" if r.get("file") and r.get("site") else None


def unparsed_note(results, cap):
    """The note for an output capability whose tool could not parse a file
    inside the surface, or None. A capability's results come from its own
    command, which is given exactly that surface (the expanded globs, or
    ESLint's outputGlobs), so any PL/unparsed carrying a file is a surface
    file — no glob matching needed here. `whole` results are excluded: those
    stand in for an ENTIRE unreadable payload, which the orchestrator
    already calls `errored` (or keeps as one location-less finding)."""
    files = sorted({r["file"] for r in results
                    if r.get("capability") == cap and r["ruleId"] == "PL/unparsed"
                    and r.get("file") and not r.get("whole")})
    return UNPARSED_PREFIX + ", ".join(files) if files else None


def measures_nothing(note):
    """True for the notes a `ran` output capability carries when its tool
    never actually saw the surface: no file matched, or a file in it did
    not parse. Both leave the capability unmeasured."""
    return note == NO_MATCH_NOTE or (isinstance(note, str) and note.startswith(UNPARSED_PREFIX))


def measured(states, cap):
    st = states.get(cap)
    return st is not None and st[0] == "ran" and not measures_nothing(st[2])


def apply(results, states, ratchet):
    """Split PL/untagged-output results of every MEASURED output capability
    into known (note) / new (error), and add one PL/ratchet-stale note per
    pinned site that is no longer reported. A capability that did not run
    (tool-missing, errored, no files matched) is left untouched: a lint that
    did not run cannot prove a site fixed or new. Pure — inputs untouched."""
    pinned = {cap: set(ratchet["sites"].get(cap, [])) for cap in OUTPUT_CAPS}
    seen = {cap: set() for cap in OUTPUT_CAPS}
    out, known, new = [], 0, 0
    for r in results:
        cap = r.get("capability")
        s = site_of(r)
        if r["ruleId"] == "PL/untagged-output" and cap in OUTPUT_CAPS and s and measured(states, cap):
            seen[cap].add(s)
            if s in pinned[cap]:
                r = dict(r, level="note", message=KNOWN_PREFIX + r["message"])
                known += 1
            else:
                r = dict(r, message=r["message"] + NEW_SUFFIX)
                new += 1
        out.append(r)
    stale = 0
    for cap in ratchet["sites"]:
        if not pinned.get(cap):
            continue
        if cap not in states:
            r = A.result("PL/ratchet-stale", DROPPED_TEXT.format(cap=cap), tool="action")
            r["capability"] = cap
            out.append(r)
            stale += 1
            continue
        if not measured(states, cap):
            continue
        for s in sorted(pinned[cap] - seen[cap]):
            r = A.result("PL/ratchet-stale", STALE_TEXT.format(site=s), file=s.partition("::")[0],
                         tool="action", site=s.partition("::")[2])
            r["capability"] = cap
            out.append(r)
            stale += 1
    return out, {"known": known, "new": new, "stale": stale}


# ---------- measure / update / prune (the only writers) ----------

def _runner_for():
    """The real tools; tests monkeypatch this. Takes no argument: the runner
    is a plain (cmd, cwd) subprocess call and resolves nothing from root —
    `which` is what root parameterises, and measure() builds that separately.

    run_checks is imported HERE, not at module level: run_checks imports this
    module at import time, so an import back would close the cycle. Only its
    PUBLIC surface — default_runner, resolver, run_capabilities — may be used
    (see run_checks.py's "Dependency direction" note)."""
    from adapters.sarif import run_checks as R
    return R.default_runner


def measure(root, manifest, scripts_dir, runner=None):
    """{output capability: (state, sorted sites)} for every <lang>.output the
    manifest carries. sites is [] unless state is a real `ran`."""
    # Lazily imported for the cycle _runner_for() explains; public surface only.
    from adapters.sarif import run_checks as R
    from scripts.check_enforcement_manifest import capabilities
    runner = runner or _runner_for()
    which = getattr(runner, "which", None) or R.resolver(root)
    caps = capabilities(manifest)
    states, results = R.run_capabilities(root, caps, scripts_dir, runner, which, only=OUTPUT_CAPS)
    out = {}
    for cap in OUTPUT_CAPS:
        if cap not in caps:
            continue
        st = states[cap]
        sites = sorted({site_of(r) for r in results
                        if r.get("capability") == cap and r["ruleId"] == "PL/untagged-output" and site_of(r)})
        out[cap] = (st, sites if measured(states, cap) else [])
    return out


def _load_manifest(root, manifest_path):
    from scripts.check_enforcement_manifest import load_manifest
    from adapters.sarif.run_checks import BOOTSTRAP_HINT
    manifest, issues = load_manifest(manifest_path, root)
    if manifest is None:
        err = "manifest invalid: " + "; ".join(issues)
        if issues and issues[0].startswith("manifest not found"):
            err += " — " + BOOTSTRAP_HINT
        return None, None, err
    if not manifest.get("ratchet"):
        return None, None, "manifest names no ratchet file (add \"ratchet\": {\"file\": \".plumb-line/ratchet.json\"})"
    return manifest, os.path.join(root, manifest["ratchet"]["file"]), None


def _unmeasurable(measures):
    """Why the writers cannot pin this surface, or None. measure() threads
    each capability's RAW state through, so this asks measured() — the one
    predicate apply() reads — instead of re-deriving it over a second shape;
    reader and writers can then never drift apart about what `measured` means."""
    states = {cap: st for cap, (st, _) in measures.items()}
    bad = [f"{cap}: {st[0]}" + (f" ({st[2]})" if st[2] else "")
           for cap, st in states.items() if not measured(states, cap)]
    return "cannot pin what could not be measured — " + "; ".join(bad) if bad else None


def _count(n):
    return f"{n} site{'' if n == 1 else 's'}"


def update(root, manifest_path, scripts_dir, because, runner=None, today=None):
    if not isinstance(because, str) or not because.strip():
        return 2, BECAUSE_REQUIRED, None
    manifest, path, err = _load_manifest(root, manifest_path)
    if err:
        return 2, err, None
    if os.path.isfile(path):
        existing, problems = load_ratchet(path)
        if existing is None:
            return 2, "existing ratchet file is invalid: " + "; ".join(problems), None
    else:
        existing = None
    measured = measure(root, manifest, scripts_dir, runner)
    err = _unmeasurable(measured)
    if err:
        return 2, err, None
    new_sites = {cap: sites for cap, (_, sites) in measured.items()}
    if existing is not None and new_sites == existing["sites"]:
        # Idempotent: re-running update on an unchanged tree must not append
        # a history entry for a change that did not happen. Compared whole,
        # so an emptied list or a dropped capability still counts as change.
        return 0, "nothing changed", existing
    data = empty()
    data["sites"] = new_sites
    data["history"] = list(existing["history"]) if existing else []
    if existing is None:
        total = sum(len(v) for v in new_sites.values())
        change = f"pinned {_count(total)} (" + ", ".join(f"{c}: {len(new_sites[c])}" for c in sorted(new_sites)) + ")"
        msg = f"pinned {_count(total)} in {os.path.relpath(path, root)}"
    else:
        parts, plus, minus = [], 0, 0
        for cap in sorted(set(existing["sites"]) | set(new_sites)):
            old = set(existing["sites"].get(cap, []))
            if cap not in new_sites:
                parts.append(f"{cap}: dropped {len(old)}")
                minus += len(old)
                continue
            new = set(new_sites[cap])
            a, r = len(new - old), len(old - new)
            plus, minus = plus + a, minus + r
            parts.append(f"{cap}: +{a} -{r}")
        change = f"+{plus} -{minus} sites (" + "; ".join(parts) + ")"
        msg = f"updated {os.path.relpath(path, root)}: {change}"
    data["history"].append({"date": today or datetime.date.today().isoformat(), "because": because.strip(),
                            "change": change})
    write_ratchet(path, data)
    return 0, msg, data


def prune(root, manifest_path, scripts_dir, runner=None, today=None):
    manifest, path, err = _load_manifest(root, manifest_path)
    if err:
        return 2, err, None
    existing, problems = load_ratchet(path)
    if existing is None:
        return 2, "; ".join(problems), None
    measured = measure(root, manifest, scripts_dir, runner)
    err = _unmeasurable(measured)
    if err:
        return 2, err, None
    data = json.loads(dumps(existing))
    parts, removed = [], 0
    for cap in sorted(data["sites"]):
        if cap not in measured:
            continue  # a dropped capability is update's job; prune only shrinks lists
        seen = set(measured[cap][1])
        keep = [s for s in data["sites"][cap] if s in seen]
        gone = len(data["sites"][cap]) - len(keep)
        if gone:
            parts.append(f"{cap}: -{gone}")
            removed += gone
            data["sites"][cap] = keep
    if not removed:
        return 0, "nothing to prune", existing
    data["history"].append({"date": today or datetime.date.today().isoformat(), "because": "prune",
                            "change": f"-{removed} sites (" + "; ".join(parts) + ")"})
    write_ratchet(path, data)
    return 0, f"pruned {removed} stale site{'' if removed == 1 else 's'} from {os.path.relpath(path, root)}", data


def main(argv=None):
    ap = argparse.ArgumentParser(description="pin or prune the provenance ratchet (#119)")
    sub = ap.add_subparsers(dest="verb", required=True)
    for verb in ("update", "prune"):
        p = sub.add_parser(verb)
        p.add_argument("--root", default=".")
        p.add_argument("--manifest", default=os.path.join(".plumb-line", "enforcement.json"))
        p.add_argument("--scripts-dir", default=_ROOT)
        p.add_argument("--json", action="store_true", help="print the resulting file instead of a one-line result")
        if verb == "update":
            p.add_argument("--because", default="", help="why the new state is correct (required, non-empty)")
    a = ap.parse_args(argv)
    root = os.path.realpath(a.root)
    manifest = a.manifest if os.path.isabs(a.manifest) else os.path.join(root, a.manifest)
    if a.verb == "update":
        code, msg, data = update(root, manifest, os.path.abspath(a.scripts_dir), a.because)
    else:
        code, msg, data = prune(root, manifest, os.path.abspath(a.scripts_dir))
    if a.json and data is not None and code == 0:
        print(dumps(data), end="")
    else:
        print(("✓ " if code == 0 else "✗ ") + msg)
    return code


if __name__ == "__main__":
    sys.exit(main())

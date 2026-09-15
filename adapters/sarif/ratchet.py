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

P7 contract: version constant + key lists + validator. Stdlib only.
"""
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

# The only state note run_checks.py writes for a `ran` capability whose tool
# was never invoked. Such a capability proves nothing about its sites.
NO_MATCH_NOTE = "no files matched the globs"

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
            if not isinstance(h["change"], str) or not h["change"]:
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
    """Canonical, atomic: tmp + os.replace, so a crash leaves the old file."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(dumps(data))
    os.replace(tmp, path)


# ---------- apply (read-only) ----------

def site_of(r):
    return f"{r['file']}::{r['site']}" if r.get("file") and r.get("site") else None


def _measured(states, cap):
    st = states.get(cap)
    return st is not None and st[0] == "ran" and st[2] != NO_MATCH_NOTE


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
        if r["ruleId"] == "PL/untagged-output" and cap in OUTPUT_CAPS and s and _measured(states, cap):
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
        if not _measured(states, cap):
            continue
        for s in sorted(pinned[cap] - seen[cap]):
            r = A.result("PL/ratchet-stale", STALE_TEXT.format(site=s), file=s.partition("::")[0],
                         tool="action", site=s.partition("::")[2])
            r["capability"] = cap
            out.append(r)
            stale += 1
    return out, {"known": known, "new": new, "stale": stale}

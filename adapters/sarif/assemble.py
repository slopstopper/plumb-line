#!/usr/bin/env python3
"""assemble.py — turn plumb-line tool outputs into one SARIF 2.1.0 log (#118).

One assembler, one rules catalogue (RULES, below — the only copy). Each tool
speaks its own machine-readable form:

    eslint --format json                 -> parse_eslint
    provenance_lint.py --json            -> parse_provenance_lint
    baseline validate --json             -> parse_baseline
    lint-imports (TEXT; no JSON upstream)-> parse_import_linter   [partial]

Anything a parser cannot map becomes a PL/unparsed WARNING carrying the raw
line, so a tool changing its output degrades to visible noise, never
silence. A tool the manifest needs but the runner lacks is a PL/tool-missing
ERROR, uploaded like any finding — never counted as a clean check.

Stdlib only. Pure functions; run_checks.py is the orchestrator.
"""
import json
import os
import re

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
SUMMARY_FORMAT = "v1"
_REPO = "https://github.com/slopstopper/plumb-line"
_BLOB = _REPO + "/blob/main/"

RULES = {
    "PL/boundary": {"name": "OneWayLayering", "level": "error",
                    "shortDescription": "An import crosses a layer boundary in the forbidden direction (Principle 2).",
                    "helpUri": _BLOB + "reference/portable-principles.md#principle-2--one-way-layering"},
    "PL/PB1": {"name": "LaunderedMeta", "level": "error",
               "shortDescription": "PB1: a clean source asserted on an explicitly mock-tainted value.",
               "helpUri": _BLOB + "primitives/SPEC.md#5-the-checker"},
    "PL/PB2": {"name": "HandBuiltLineage", "level": "error",
               "shortDescription": "PB2: lineage or weakestSource written by hand instead of computed.",
               "helpUri": _BLOB + "primitives/SPEC.md#5-the-checker"},
    "PL/PB3": {"name": "DeriveOverrideClearsTaint", "level": "error",
               "shortDescription": "PB3: a derive override that would clear taint or lineage.",
               "helpUri": _BLOB + "primitives/SPEC.md#5-the-checker"},
    "PL/PB4": {"name": "RemarkDropsLineage", "level": "error",
               "shortDescription": "PB4: re-marking an unwrapped value, dropping its lineage.",
               "helpUri": _BLOB + "primitives/SPEC.md#5-the-checker"},
    "PL/untagged-output": {"name": "UntaggedOutput", "level": "error",
                           "shortDescription": "An exported function in the declared surface returns a raw computation not wrapped by mark/derive (ADR-0011).",
                           "helpUri": _BLOB + "docs/adr/0011-enforcement-rule-scoping.md"},
    "PL/baseline-invalid": {"name": "BaselineInvalid", "level": "error",
                            "shortDescription": "A baseline record fails its own contract (baseline-format v1).",
                            "helpUri": _BLOB + "primitives/README.md#baseline-principle-9"},
    "PL/tool-missing": {"name": "ToolMissing", "level": "error",
                        "shortDescription": "The manifest enforces a capability whose tool is not installed on the runner.",
                        "helpUri": _BLOB + "ACTION.md#tools"},
    "PL/unparsed": {"name": "Unparsed", "level": "warning",
                    "shortDescription": "A tool produced output the assembler could not map to a rule; the raw line is in the message.",
                    "helpUri": _BLOB + "ACTION.md#unparsed"},
}

_ESLINT_RULE = {
    "import/no-restricted-paths": "PL/boundary",
    "plumb-line/no-provenance-bypass": None,       # PB<n> is read from the message
    "plumb-line/require-provenance-output": "PL/untagged-output",
}
_PB = re.compile(r"^PB([1-4])\b")
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_IL_VIOLATION = re.compile(r"^- (?P<importer>[\w.]+) -> (?P<imported>[\w.]+) \((?P<lines>l\.[^)]*)\)$")
_IL_LINENO = re.compile(r"l\.(\d+|\?)")
_IL_HEADER = re.compile(r"^(?P<a>[\w.]+) is not allowed to import (?P<b>[\w.]+):$")
_IL_SUMMARY = re.compile(r"^Contracts: (?P<kept>\d+) kept, (?P<broken>\d+) broken\.$")


def result(rule_id, message, file=None, line=None, column=None, tool="action", parser="json"):
    return {"ruleId": rule_id, "level": RULES[rule_id]["level"], "message": message,
            "file": file, "line": line, "column": column, "tool": tool, "parser": parser,
            "whole": False}


def unparsed(text, tool, *, file=None, line=None, column=None, parser="text", whole=False):
    """whole=True marks a result standing in for an ENTIRE payload that
    could not be parsed at all (non-JSON, wrong-shaped JSON, or a text
    report missing its summary line) — as opposed to one unmappable item
    inside an otherwise-parsed payload (whole=False, the default). The
    orchestrator's errored-vs-ran distinction depends on this: a crashed
    tool looks like the former, one unknown rule id looks like the latter."""
    r = result("PL/unparsed", f"unparsed {tool} output: {text}", file=file, line=line,
              column=column, tool=tool, parser=parser)
    r["whole"] = whole
    return r


def tool_missing(capability, hint):
    return result("PL/tool-missing", f"{capability}: tool not installed on the runner — {hint}", tool="action")


def _rel(path, root):
    if not path:
        return None
    p = os.path.normpath(path)
    r = os.path.normpath(root)
    if p.startswith(r + os.sep):
        p = p[len(r) + 1:]
    return p.replace(os.sep, "/")


def _line(n):
    return n if isinstance(n, int) and n > 0 else None


# ---------- parsers ----------

def parse_eslint(text, root):
    try:
        files = json.loads(text)
    except ValueError:
        return [unparsed(text.strip()[:200], "eslint", whole=True)]
    if not isinstance(files, list):
        # Valid JSON, wrong shape (object/null/number/...): a shape change
        # must never read as "no findings" — see parse_provenance_lint/parse_baseline.
        return [unparsed(text.strip()[:200], "eslint", whole=True)]
    out = []
    for f in files:
        if not isinstance(f, dict) or not isinstance(f.get("messages", []), list):
            out.append(unparsed(json.dumps(f)[:200], "eslint"))
            continue
        for m in f.get("messages", []):
            rid = m.get("ruleId")
            mapped = _ESLINT_RULE.get(rid, "missing")
            if mapped is None:
                pb = _PB.match(m.get("message", ""))
                mapped = f"PL/PB{pb.group(1)}" if pb else "missing"
            if mapped == "missing":
                out.append(unparsed(f"{rid}: {m.get('message', '')}", "eslint",
                                    file=_rel(f.get("filePath"), root), line=_line(m.get("line")),
                                    column=_line(m.get("column")), parser="json"))
                continue
            out.append(result(mapped, m.get("message", ""), file=_rel(f.get("filePath"), root),
                              line=_line(m.get("line")), column=_line(m.get("column")), tool="eslint"))
    return out


def parse_provenance_lint(text, root):
    try:
        issues = json.loads(text)
    except ValueError:
        return [unparsed(text.strip()[:200], "provenance_lint", whole=True)]
    if not isinstance(issues, list):
        return [unparsed(text.strip()[:200], "provenance_lint", whole=True)]
    out = []
    for i in issues:
        if not isinstance(i, dict):
            out.append(unparsed(json.dumps(i)[:200], "provenance_lint"))
            continue
        rule = i.get("rule", "")
        if rule in ("PB1", "PB2", "PB3", "PB4"):
            rid = "PL/" + rule
        elif rule == "REQ-OUTPUT":
            rid = "PL/untagged-output"
        else:
            out.append(unparsed(f"{rule}: {i.get('message', '')}", "provenance_lint",
                                file=_rel(i.get("filename"), root), line=_line(i.get("line")), parser="json"))
            continue
        out.append(result(rid, i.get("message", ""), file=_rel(i.get("filename"), root),
                          line=_line(i.get("line")), tool="provenance_lint"))
    return out


def parse_baseline(text, root):
    try:
        data = json.loads(text)
    except ValueError:
        return [unparsed(text.strip()[:200], "baseline", whole=True)]
    if not isinstance(data, dict):
        return [unparsed(text.strip()[:200], "baseline", whole=True)]
    out = []
    d = _rel(data.get("dir"), root) or ""
    for f in data.get("files", []):
        if (not isinstance(f, dict) or not isinstance(f.get("file"), str)
                or not isinstance(f.get("issues", []), list)
                or not all(isinstance(x, str) for x in f.get("issues", []))):
            # Malformed entry (no dict / no "file" string / non-list or
            # non-string "issues"): report it, don't KeyError/TypeError.
            out.append(unparsed(json.dumps(f)[:200], "baseline"))
            continue
        if f.get("issues"):
            out.append(result("PL/baseline-invalid", "; ".join(f["issues"]),
                              file=(d + "/" if d else "") + f["file"], tool="baseline"))
    return out


def _module_to_file(module, root, root_package):
    if not module.startswith(root_package + ".") and module != root_package:
        return None
    rel = module.replace(".", "/")
    for cand in (rel + ".py", rel + "/__init__.py"):
        if os.path.isfile(os.path.join(root, cand)):
            return cand
    return None


def parse_import_linter(text, root, root_package):
    """import-linter 2.x text report -> results. `partial`: the report is not
    a versioned contract; anything unrecognised in the Broken contracts
    section becomes PL/unparsed, and a report with no Contracts: summary line
    is one PL/unparsed result for the whole text.

    Section headings (the contract-name line under "Broken contracts", e.g.
    "plumb-line one-way layering" or a user-chosen contract name) are
    recognised structurally — a non-blank line immediately followed by a
    dash-only line — never by matching a hardcoded name/prefix. A single
    violation line can carry more than one location, joined by import-linter
    as "(l.7, l.12)", or an unresolvable "(l.?)"; each number in that list
    becomes its own result sharing the violation's message."""
    lines = [_ANSI.sub("", ln).rstrip() for ln in text.splitlines()]
    summary = next((m for m in (_IL_SUMMARY.match(ln) for ln in lines) if m), None)
    if summary is None:
        body = " ".join(ln for ln in lines if ln.strip())
        return [unparsed(body[:200], "import-linter", whole=True)]
    out = []
    in_broken = False
    header = None
    for i, ln in enumerate(lines):
        if ln == "Broken contracts":
            in_broken = True
            continue
        if not in_broken:
            continue
        if not ln.strip():
            continue
        if set(ln) <= {"-"}:
            continue
        if ln.startswith(("Contracts:", "Analyzed", "Checking")):
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if nxt.strip() and set(nxt) <= {"-"}:
            # A heading of any name: this line is text, the next is its
            # dash underline. Structural — no name/prefix matching.
            continue
        h = _IL_HEADER.match(ln)
        if h:
            header = f"{h.group('a')} is not allowed to import {h.group('b')}"
            continue
        v = _IL_VIOLATION.match(ln)
        if v:
            msg = f"{v.group('importer')} -> {v.group('imported')}"
            if header:
                msg += f": {header}"
            file = _module_to_file(v.group("importer"), root, root_package)
            for lm in _IL_LINENO.finditer(v.group("lines")):
                n = lm.group(1)
                out.append(result("PL/boundary", msg, file=file, line=(int(n) if n != "?" else None),
                                  tool="import-linter", parser="text"))
            continue
        out.append(unparsed(ln, "import-linter"))
    broken = int(summary.group("broken"))
    if broken > 0 and not any(r["ruleId"] == "PL/boundary" for r in out):
        out.append(unparsed(f"Contracts: {broken} broken reported but no violation line was recognised",
                            "import-linter"))
    return out


# ---------- SARIF ----------

def build_sarif(results, version, src_root=None):
    """src_root: the checkout every result's `file` is relative to. When
    given, %SRCROOT% is declared as that directory's file: URI so viewers
    other than GitHub (which resolves %SRCROOT% itself) can open the files;
    when None, originalUriBaseIds is omitted rather than asserting a base
    the assembler does not know."""
    import pathlib
    rule_ids = list(RULES)
    rules = [{"id": rid, "name": r["name"], "shortDescription": {"text": r["shortDescription"]},
              "helpUri": r["helpUri"], "defaultConfiguration": {"level": r["level"]}}
             for rid, r in RULES.items()]
    out = []
    for r in results:
        item = {"ruleId": r["ruleId"], "ruleIndex": rule_ids.index(r["ruleId"]), "level": r["level"],
                "message": {"text": r["message"]}, "properties": {"tool": r["tool"], "parser": r["parser"]}}
        if r.get("file"):
            phys = {"artifactLocation": {"uri": r["file"], "uriBaseId": "%SRCROOT%"}}
            region = {}
            if r.get("line"):
                region["startLine"] = r["line"]
                if r.get("column"):
                    region["startColumn"] = r["column"]
            if region:
                phys["region"] = region
            item["locations"] = [{"physicalLocation": phys}]
        out.append(item)
    run = {"tool": {"driver": {"name": "plumb-line", "version": version,
                               "informationUri": _REPO, "rules": rules}}}
    if src_root is not None:
        run["originalUriBaseIds"] = {"%SRCROOT%": {"uri": pathlib.Path(os.path.abspath(src_root)).as_uri() + "/"}}
    run["results"] = out
    return {"$schema": SARIF_SCHEMA, "version": SARIF_VERSION, "runs": [run]}


# ---------- summary ----------

def build_summary(capability_states, results, fail_on, sarif_path):
    """capability_states: {key: (state, parser|None, note|None)}."""
    caps = {}
    for key, (state, parser, note) in capability_states.items():
        caps[key] = {"state": state, "parser": parser, "note": note,
                     "results": sum(1 for r in results if _owner(r) == key)}
    return {"summary-format": SUMMARY_FORMAT, "fail_on": fail_on, "capabilities": caps,
            "findings": len(results),
            "unlocated": sum(1 for r in results if not r.get("file")),
            "unparsed": sum(1 for r in results if r["ruleId"] == "PL/unparsed"),
            "sarif": sarif_path}


def _owner(r):
    return r.get("capability")


def summary_text(s):
    states = [c["state"] for c in s["capabilities"].values()]
    ran = states.count("ran")
    missing = states.count("tool-missing")
    findings = s["findings"]
    parts = [f"{ran} check{'s' if ran != 1 else ''} ran",
             f"{states.count('not-enforced')} not enforced here",
             f"{missing} tool{'' if missing == 1 else 's'} missing",
             f"{states.count('errored')} errored"]
    head = ", ".join(parts) + f"; {findings} finding{'' if findings == 1 else 's'}"
    lines = [f"plumb-line enforcement — {head} (fail-on: {s['fail_on']})", ""]
    lines.append("| capability | state | results | parser | note |")
    lines.append("| --- | --- | --- | --- | --- |")
    for key in sorted(s["capabilities"]):
        c = s["capabilities"][key]
        lines.append(f"| {key} | {c['state']} | {c['results']} | {c['parser'] or '—'} | {c['note'] or ''} |")
    lines.append("")
    lines.append(f"unlocated results: {s['unlocated']} · unparsed lines: {s['unparsed']} · SARIF: {s['sarif']}")
    return "\n".join(lines)

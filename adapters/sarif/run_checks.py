#!/usr/bin/env python3
"""run_checks.py — the orchestrator behind action.yml (#118).

Reads the manifest (and ONLY the manifest), preflights the tools it needs,
runs each enabled capability, feeds the outputs to assemble.py, writes the
SARIF log + summary JSON + a GitHub step summary, and returns the exit code.

Every outcome is a named state — ran | not-enforced | tool-missing | errored —
and the step summary states the denominators, so an empty green is legible
as empty, never as clean.

    python3 adapters/sarif/run_checks.py --root . --manifest .plumb-line/enforcement.json \
        --scripts-dir <plumb-line checkout> --fail-on findings|none \
        --sarif out.sarif --summary summary.json [--step-summary $GITHUB_STEP_SUMMARY] --version <tag>
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)
from scripts.check_enforcement_manifest import load_manifest, capabilities  # noqa: E402
from adapters.sarif import assemble as A  # noqa: E402

BOOTSTRAP_HINT = ("no enforcement manifest — run the plumb-line-bootstrap skill (Step 4d writes "
                  ".plumb-line/enforcement.json), or write it by hand: "
                  '{"enforcement-format": "v1", "languages": [...], ...} — see ACTION.md')

# capability -> (tool binary to preflight, install hint)
TOOLS = {
    "js.boundary": ("npx", "npm ci (eslint + eslint-plugin-import-x from the consumer's package.json)"),
    "js.provenance": ("npx", "npm ci (eslint from the consumer's package.json)"),
    "js.output": ("npx", "npm ci (eslint from the consumer's package.json)"),
    "python.boundary": ("lint-imports", "pip install import-linter"),
    "python.provenance": ("python3", "python3 on PATH"),
    "python.output": ("python3", "python3 on PATH"),
    "baselines": ("node", "node >= 22 on PATH"),
}


def _default_runner(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def _which(tool):
    return shutil.which(tool)


def _command(key, cfg, scripts_dir):
    """The exact command per capability. cwd is always the consumer root."""
    if key == "js.boundary":
        return ["npx", "eslint", "--no-config-lookup", "--config", cfg["config"], "--format", "json", "."]
    if key == "js.provenance":
        return ["npx", "eslint", "--no-config-lookup", "--config", cfg["config"], "--format", "json", *cfg["globs"]]
    if key == "js.output":
        return ["npx", "eslint", "--no-config-lookup", "--config", cfg["config"], "--format", "json", *cfg["outputGlobs"]]
    lint = os.path.join(scripts_dir, "adapters", "python", "provenance_lint.py")
    if key == "python.provenance":
        return ["python3", lint, "--json", *cfg["globs"]]
    if key == "python.output":
        return ["python3", lint, "--require-output", "--json", *cfg["outputGlobs"]]
    if key == "python.boundary":
        return ["lint-imports", "--config", cfg["config"], "--no-cache"]
    if key == "baselines":
        return ["node", os.path.join(scripts_dir, "primitives", "js", "baseline-cli.mjs"),
                 "validate", "--json", "--dir", cfg["dir"]]
    raise KeyError(key)


def _expand(root, patterns):
    """Globs for the Python tools (ESLint expands its own)."""
    import glob
    out = []
    for pat in patterns:
        out.extend(sorted(glob.glob(os.path.join(root, pat), recursive=True)))
    return [os.path.relpath(p, root) for p in out]


def _root_package(root, cfg_path):
    """import-linter's root_package, read from the consumer's own config.
    A config that doesn't parse as ini (or lacks the key) degrades to ""
    rather than taking the run down — parse_import_linter treats that as
    "can't resolve a file for this violation", not a crash."""
    import configparser
    cp = configparser.ConfigParser()
    try:
        cp.read(os.path.join(root, cfg_path), encoding="utf-8")
    except configparser.Error:
        return ""
    return cp.get("importlinter", "root_package", fallback="")


def _looks_unparsed(parsed, out):
    """True when a tool's stdout amounts to nothing usable: empty, or the
    parser's total-failure fallback — a single whole=True PL/unparsed,
    which is what the parsers each return when the ENTIRE payload didn't
    parse (non-JSON, wrong-shaped JSON, or a text report with no summary
    line). A single unmappable ITEM inside an otherwise-parsed payload
    (whole=False — an unknown ESLint/provenance_lint rule id, a malformed
    entry, ...) is a real finding, not evidence the tool crashed."""
    return not out.strip() or (len(parsed) == 1 and parsed[0]["ruleId"] == "PL/unparsed" and parsed[0].get("whole"))


def run(root, manifest_path, scripts_dir, fail_on, sarif_path, summary_path, step_summary_path=None,
        version="dev", runner=None):
    runner = runner or _default_runner
    which = getattr(runner, "which", _which)
    manifest, issues = load_manifest(manifest_path, root)
    if manifest is None:
        for i in issues:
            print(f"✗ {i}")
        if issues and issues[0].startswith("manifest not found"):
            print(f"  {BOOTSTRAP_HINT}")
        return 1
    caps = capabilities(manifest)
    states, results = {}, []
    for key, cfg in caps.items():
        tool, hint = TOOLS[key]
        if which(tool) is None:
            states[key] = ("tool-missing", None, hint)
            r = A.tool_missing(key, hint)
            r["capability"] = key
            results.append(r)
            continue
        cmd = _command(key, cfg, scripts_dir)
        if key in ("python.provenance", "python.output"):
            globs = cfg["globs"] if key == "python.provenance" else cfg["outputGlobs"]
            files = _expand(root, globs)
            if not files:
                states[key] = ("ran", "json", "no files matched the globs")
                continue
            cmd = cmd[:-len(globs)] + files
        rc, out, err = runner(cmd, root)
        try:
            if key in ("js.boundary", "js.provenance", "js.output"):
                parsed, parser = A.parse_eslint(out, root), "json"
            elif key in ("python.provenance", "python.output"):
                parsed, parser = A.parse_provenance_lint(out, root), "json"
            elif key == "python.boundary":
                parsed, parser = A.parse_import_linter(out, root, _root_package(root, cfg["config"])), "text"
            else:
                parsed, parser = A.parse_baseline(out, root), "json"
        except Exception as e:  # a parser must never take the run down
            parsed, parser = [A.unparsed(f"{type(e).__name__}: {e}", key)], "text"
        if rc != 0 and _looks_unparsed(parsed, out):
            note = f"exit {rc}: {(err or out).strip()[:500]}"
            states[key] = ("errored", parser, " ".join(note.split()))
            continue
        if key == "js.provenance":
            parsed = [r for r in parsed if r["ruleId"] != "PL/untagged-output"]
        if key == "js.output":
            parsed = [r for r in parsed if r["ruleId"] == "PL/untagged-output"]
        for r in parsed:
            r["capability"] = key
        results.extend(parsed)
        states[key] = ("ran", parser, None)
    log = A.build_sarif(results, version)
    os.makedirs(os.path.dirname(os.path.abspath(sarif_path)), exist_ok=True)
    with open(sarif_path, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2)
    summary = A.build_summary(states, results, fail_on, sarif_path)
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    text = A.summary_text(summary)
    print(text)
    if step_summary_path:
        with open(step_summary_path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    fail = (any(s[0] in ("tool-missing", "errored") for s in states.values())
            or (summary["findings"] > 0 and fail_on == "findings"))
    return 1 if fail else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="run plumb-line enforcement and emit SARIF")
    ap.add_argument("--root", default=".")
    ap.add_argument("--manifest", default=os.path.join(".plumb-line", "enforcement.json"))
    ap.add_argument("--scripts-dir", default=_ROOT)
    ap.add_argument("--fail-on", choices=["findings", "none"], default="findings")
    ap.add_argument("--sarif", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--step-summary", default=os.environ.get("GITHUB_STEP_SUMMARY"))
    ap.add_argument("--version", default="dev")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    manifest = a.manifest if os.path.isabs(a.manifest) else os.path.join(root, a.manifest)
    return run(root, manifest, os.path.abspath(a.scripts_dir), a.fail_on, a.sarif, a.summary,
               a.step_summary, a.version)


if __name__ == "__main__":
    sys.exit(main())

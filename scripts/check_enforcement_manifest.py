#!/usr/bin/env python3
"""check_enforcement_manifest.py — validate .plumb-line/enforcement.json (#118).

    python3 scripts/check_enforcement_manifest.py [<manifest>] [--root <repo root>]

The manifest is the one place a repo states which plumb-line enforcement it
carries. The GitHub Action reads ONLY this file (ADR-0016): every capability
is optional, absence means "not enforced here" (stated, never counted as a
pass), and nothing in it is a default — bootstrap fills it from the
interview, or a maintainer writes it by hand.

P7 contract: version constant + key lists + validator. Exit 0 when valid,
1 with one issue per line otherwise.
"""
import argparse
import json
import os
import sys

MANIFEST_FORMAT = "v1"
KNOWN_MANIFEST_FORMATS = {"v1"}
DEFAULT_PATH = os.path.join(".plumb-line", "enforcement.json")

CAPABILITY_KEYS = ["js.boundary", "js.provenance", "js.output",
                   "python.boundary", "python.provenance", "python.output", "baselines"]

_TOP_KEYS = {"enforcement-format", "languages", "js", "python", "baselines"}
_LANG_KEYS = {"boundary", "provenance"}
_BOUNDARY_KEYS = {"config"}
_PROVENANCE_KEYS = {"js": {"config", "globs", "outputGlobs"}, "python": {"globs", "outputGlobs"}}
_BASELINES_KEYS = {"dir"}
_LANGUAGES = ["js", "python"]


def _glob_list(value, where, issues):
    if not isinstance(value, list) or not value or not all(isinstance(g, str) and g for g in value):
        issues.append(f"{where} must be a non-empty list of non-empty strings")


def _unknown(obj, allowed, where, issues):
    for k in obj:
        if k not in allowed:
            issues.append(f"unknown key: {where}{k}")


def _inside(root, rel):
    """Verify rel is a relative path inside root. Return joined path or None."""
    if os.path.isabs(rel):
        return None
    joined = os.path.normpath(os.path.join(root, rel))
    root_norm = os.path.normpath(root)
    if joined == root_norm or joined.startswith(root_norm + os.sep):
        return joined
    return None


def validate_manifest(manifest, root):
    """Issues with a parsed manifest; [] when valid. Never raises."""
    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]
    issues = []
    _unknown(manifest, _TOP_KEYS, "", issues)
    fmt = manifest.get("enforcement-format")
    if fmt not in KNOWN_MANIFEST_FORMATS:
        issues.append(f"unknown enforcement-format {json.dumps(fmt)} "
                      f"(this validator models {sorted(KNOWN_MANIFEST_FORMATS)})")
    langs = manifest.get("languages")
    if not isinstance(langs, list) or not langs:
        issues.append("languages must be a non-empty list")
        langs = []
    for lang in langs:
        if lang not in _LANGUAGES:
            issues.append(f"languages: unknown language {json.dumps(lang)}")
        elif lang not in manifest:
            issues.append(f"languages names {lang} but there is no {lang} section")
    for lang in _LANGUAGES:
        if lang in manifest and lang not in langs:
            issues.append(f"languages omits {lang} but a {lang} section is present")
    for lang in _LANGUAGES:
        section = manifest.get(lang)
        if section is None:
            continue
        if not isinstance(section, dict):
            issues.append(f"{lang} must be an object")
            continue
        _unknown(section, _LANG_KEYS, f"{lang}.", issues)
        b = section.get("boundary")
        if b is not None:
            if not isinstance(b, dict):
                issues.append(f"{lang}.boundary must be an object")
            else:
                _unknown(b, _BOUNDARY_KEYS, f"{lang}.boundary.", issues)
                cfg = b.get("config")
                if not isinstance(cfg, str) or not cfg:
                    issues.append(f"{lang}.boundary.config must be a non-empty string")
                elif _inside(root, cfg) is None:
                    issues.append(f"{lang}.boundary.config must be a relative path inside the repository: {cfg}")
                elif not os.path.isfile(_inside(root, cfg)):
                    issues.append(f"{lang}.boundary.config not found: {cfg}")
        p = section.get("provenance")
        if p is not None:
            if not isinstance(p, dict):
                issues.append(f"{lang}.provenance must be an object")
            else:
                _unknown(p, _PROVENANCE_KEYS[lang], f"{lang}.provenance.", issues)
                if lang == "js":
                    cfg = p.get("config")
                    if not isinstance(cfg, str) or not cfg:
                        issues.append("js.provenance.config must be a non-empty string")
                    elif _inside(root, cfg) is None:
                        issues.append(f"js.provenance.config must be a relative path inside the repository: {cfg}")
                    elif not os.path.isfile(_inside(root, cfg)):
                        issues.append(f"js.provenance.config not found: {cfg}")
                if "globs" in p:
                    _glob_list(p["globs"], f"{lang}.provenance.globs", issues)
                else:
                    issues.append(f"{lang}.provenance.globs is required")
                if "outputGlobs" in p:
                    _glob_list(p["outputGlobs"], f"{lang}.provenance.outputGlobs", issues)
    bl = manifest.get("baselines")
    if bl is not None:
        if not isinstance(bl, dict):
            issues.append("baselines must be an object")
        else:
            _unknown(bl, _BASELINES_KEYS, "baselines.", issues)
            d = bl.get("dir")
            if not isinstance(d, str) or not d:
                issues.append("baselines.dir must be a non-empty string")
            elif _inside(root, d) is None:
                issues.append(f"baselines.dir must be a relative path inside the repository: {d}")
            elif not os.path.isdir(_inside(root, d)):
                issues.append(f"baselines.dir not found: {d}")
    return issues


def capabilities(manifest):
    """{capability key: its config block} for every capability the manifest carries."""
    caps = {}
    for lang in _LANGUAGES:
        section = manifest.get(lang) or {}
        if "boundary" in section:
            caps[f"{lang}.boundary"] = section["boundary"]
        if "provenance" in section:
            caps[f"{lang}.provenance"] = section["provenance"]
            if "outputGlobs" in section["provenance"]:
                caps[f"{lang}.output"] = section["provenance"]
    if "baselines" in manifest:
        caps["baselines"] = manifest["baselines"]
    return caps


def load_manifest(path, root):
    """(manifest, issues). manifest is None when missing or unparsable; issues
    is non-empty whenever the manifest is unusable."""
    if not os.path.isfile(path):
        return None, [f"manifest not found: {path}"]
    try:
        with open(path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError) as e:
        return None, [f"cannot parse {path}: {e}"]
    issues = validate_manifest(manifest, root)
    return (manifest if not issues else None), issues


def main(argv=None):
    ap = argparse.ArgumentParser(description="validate a plumb-line enforcement manifest")
    ap.add_argument("manifest", nargs="?", default=DEFAULT_PATH)
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    manifest, issues = load_manifest(args.manifest, args.root)
    if issues:
        for i in issues:
            print(f"✗ {i}")
        return 1
    caps = capabilities(manifest)
    print(f"✓ {args.manifest}: enforcement-format {manifest['enforcement-format']}, "
          f"{len(caps)} capabilit{'y' if len(caps) == 1 else 'ies'} enforced: {', '.join(sorted(caps)) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

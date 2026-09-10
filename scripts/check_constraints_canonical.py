#!/usr/bin/env python3
"""check_constraints_canonical.py — hold docs/constraints.md to the repo it describes (#248).

    python3 scripts/check_constraints_canonical.py            # from the repo root

`docs/constraints.md` is the canonical home of the repo's exact values, and
`scripts/check-constraints-drift.sh` fails any downstream *copy* that
differs from it. Nothing checked the canonical file itself: a PR that moved
the CI matrix, or a release that bumped the manifests, could leave the
block asserting a value the repo no longer holds — and every sha-pinned copy
would inherit the false claim. The 0.10.0 release did exactly that: the
manifests moved and the block kept saying 0.9.0 with every gate green.

This gate parses each machine-readable line of the block and compares it
to its source of truth:

    release version        primitives/js/package.json  (check-versions.mjs
                           already holds the three manifests to each other)
    PROVENANCE_VERSION     primitives/js/provenance.mjs and provenance.py
    package name           package.json name / pyproject name
    license                package.json license / pyproject license
    Python floor           pyproject requires-python
    Python CI matrix       .github/workflows/ci.yml  `python: [...]`
    Node floor             package.json engines.node
    Node CI matrix         .github/workflows/ci.yml  `node: [...]`

Deliberately NOT checked, and said so on every run: the report-contract
line (the validator declares its formats in prose, not as a constant) and
the lines that state discipline rather than a value (envelope shapes,
tag-triggered releases). A block line the parser cannot find is a finding,
not a pass — checking fewer constraints than the block states is the #249
failure shape, so the run prints how many it checked.

Exit 0 when every checked line matches; exit 1 naming each drift.
"""
import json
import os
import re
import sys
from collections import namedtuple

BEGIN = "<!-- constraints:begin -->"
END = "<!-- constraints:end -->"

Finding = namedtuple("Finding", "key stated actual where")

# key -> (regex over the block, human label, source-of-truth description)
BLOCK_PATTERNS = {
    "release_version": (r"Release version is \*\*([^*]+)\*\*", "release version",
                        "primitives/js/package.json version"),
    "provenance_version": (r"`PROVENANCE_VERSION` is \*\*(\d+)\*\*", "PROVENANCE_VERSION",
                           "primitives/js/provenance.mjs + primitives/python/provenance.py"),
    "package_name": (r"Published package name is \*\*`([^`]+)`\*\*", "package name",
                     "package.json name + pyproject name"),
    "license": (r"License is \*\*([^*]+)\*\*", "license",
                "package.json license + pyproject license"),
    "python_floor": (r"`requires-python = \"([^\"]+)\"`", "Python floor",
                     "pyproject requires-python"),
    "python_matrix": (r"Python floor[^\n]*the CI matrix tests \*\*([^*]+)\*\*", "Python CI matrix",
                      "ci.yml python matrix"),
    "node_floor": (r"`engines\.node ([^`]+)`", "Node floor",
                   "package.json engines.node"),
    "node_matrix": (r"Node floor[^\n]*the CI matrix tests \*\*Node ([^*]+)\*\*", "Node CI matrix",
                    "ci.yml node matrix"),
}

UNCHECKED = [
    "report contracts (report-format / remediation-format — validator states them in prose, no constant to read)",
    "envelope shapes + conformance parity (a discipline, held by the conformance suites)",
    "tag-triggered releases (a discipline, held by release.yml)",
]


class ConstraintsError(Exception):
    """The canonical file is not in the shape the gate can read."""


def _strip_fences(text):
    # The canonical file shows the marker format inside a code fence as a
    # worked example; the drift gate skips fenced markers for the same reason.
    return re.sub(r"^[ \t]*```.*?^[ \t]*```[ \t]*$", "", text, flags=re.M | re.S)


def extract_block(text):
    text = _strip_fences(text)
    start = text.find(BEGIN)
    end = text.find(END)
    if start < 0 or end < 0 or end < start:
        raise ConstraintsError("constraints:begin/end markers not found")
    return text[start + len(BEGIN):end].lstrip("\n")


def normalise_range(spec):
    return re.sub(r"\s+", "", spec)


def _version_list(prose):
    return re.findall(r"\d+(?:\.\d+)?", prose)


def read_block_values(block):
    values = {}
    for key, (pattern, _label, _src) in BLOCK_PATTERNS.items():
        m = re.search(pattern, block)
        if not m:
            continue
        raw = m.group(1).strip()
        if key.endswith("_matrix"):
            values[key] = _version_list(raw)
        elif key.endswith("_floor"):
            values[key] = normalise_range(raw)
        else:
            values[key] = raw
    return values


def read_ci_matrix(ci_text, name):
    m = re.search(r"^\s+%s:\s*\[([^\]]*)\]" % re.escape(name), ci_text, re.M)
    if not m:
        raise ConstraintsError("ci.yml: no `%s: [...]` matrix list found" % name)
    return [item.strip().strip("\"'") for item in m.group(1).split(",") if item.strip()]


def _read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as fh:
        return fh.read()


def _first(pattern, text, where, flags=re.M):
    m = re.search(pattern, text, flags)
    if not m:
        raise ConstraintsError("%s: pattern %r not found" % (where, pattern))
    return m.group(1)


def read_source_values(root):
    pkg = json.loads(_read(root, "primitives/js/package.json"))
    pyproject = _read(root, "primitives/python/pyproject.toml")
    ci = _read(root, ".github/workflows/ci.yml")
    prov_js = _first(r"^export const PROVENANCE_VERSION = (\d+)",
                     _read(root, "primitives/js/provenance.mjs"), "provenance.mjs")
    prov_py = _first(r"^PROVENANCE_VERSION = (\d+)",
                     _read(root, "primitives/python/provenance.py"), "provenance.py")
    py_name = _first(r'^name\s*=\s*"([^"]+)"', pyproject, "pyproject name")
    py_license = _first(r'^license\s*=\s*"([^"]+)"', pyproject, "pyproject license")

    # Where two sources must agree, a disagreement is reported as the source
    # value so the finding shows it rather than silently picking one.
    def agree(a, b, what):
        return a if a == b else "%s (%s disagree: %r vs %r)" % (a, what, a, b)

    return {
        "release_version": pkg["version"],
        "provenance_version": agree(prov_js, prov_py, "js/python"),
        "package_name": agree(pkg["name"], py_name, "npm/pypi"),
        "license": agree(pkg.get("license"), py_license, "npm/pypi"),
        "python_floor": normalise_range(_first(r'^requires-python\s*=\s*"([^"]+)"', pyproject,
                                               "pyproject requires-python")),
        "python_matrix": read_ci_matrix(ci, "python"),
        "node_floor": normalise_range(pkg.get("engines", {}).get("node", "")),
        "node_matrix": read_ci_matrix(ci, "node"),
    }


def compare(block_values, source_values):
    findings = []
    for key, (_pattern, _label, src) in BLOCK_PATTERNS.items():
        stated = block_values.get(key)
        actual = source_values.get(key)
        if stated != actual:
            findings.append(Finding(key, stated, actual, src))
    return findings


def format_finding(f):
    label = BLOCK_PATTERNS[f.key][1]
    if f.stated is None:
        return "✗ %s: no line in the constraints block matched (reworded? the gate cannot check it)" % label
    return "✗ %s: constraints.md states %r but %s holds %r" % (label, f.stated, f.where, f.actual)


def run(root):
    block = extract_block(_read(root, "docs/constraints.md"))
    return compare(read_block_values(block), read_source_values(root))


def main(argv):
    root = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    try:
        findings = run(root)
    except ConstraintsError as exc:
        print("✗ check_constraints_canonical: %s" % exc)
        return 1
    checked = len(BLOCK_PATTERNS)
    for f in findings:
        print(format_finding(f))
    if findings:
        print("  %d of %d checked constraint(s) drifted. Fix docs/constraints.md (or the source it "
              "describes); downstream copies re-pin on their next edit." % (len(findings), checked))
        return 1
    print("✓ docs/constraints.md matches its sources on %d checked constraints" % checked)
    print("  not checked (no machine-readable source): " + "; ".join(UNCHECKED))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""Tests for scripts/check_constraints_canonical.py — the canonical-file gate (#248).

Run from the repo root:

    python3 -m pytest -q scripts/test_constraints_canonical.py

Mirrors the scripts/test_version_prose.py precedent: a pytest suite for a
repo-infrastructure script that lives outside any package, loaded by path
under a private module name.
"""
import importlib.util
import os
import textwrap

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SCRIPT = os.path.join(_HERE, "check_constraints_canonical.py")
_spec = importlib.util.spec_from_file_location("_check_constraints_canonical", _SCRIPT)
ccc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ccc)


BLOCK = textwrap.dedent("""\
    - Release version is **0.10.0**, and the three manifests must always agree: `primitives/js/package.json`, `primitives/python/pyproject.toml`, `.claude-plugin/plugin.json`. Bump only via `node scripts/bump-version.mjs <version>`.
    - `PROVENANCE_VERSION` is **2**, identical in `primitives/js/provenance.mjs` and `primitives/python/provenance.py`. It is the envelope wire version and moves independently of the release version; `bump-version` does not touch it.
    - Published package name is **`plumb-line-provenance`**, identical on npm and PyPI.
    - License is **Apache-2.0** in both manifests.
    - Python floor is **`requires-python = ">=3.11"`**; the CI matrix tests **3.11, 3.12 and 3.13**.
    - Node floor as published is **`engines.node >= 22`**; the CI matrix tests **Node 22 and 24**.
    - Report contracts are **report-format v3** and **remediation-format v1**, validated by `scripts/check_report_format.py`.
    """)

DOC = "# Constraints\n\nprose\n\n<!-- constraints:begin -->\n" + BLOCK + "<!-- constraints:end -->\n\n## Why\n"

SOURCES = {
    "release_version": "0.10.0",
    "provenance_version": "2",
    "package_name": "plumb-line-provenance",
    "license": "Apache-2.0",
    "python_floor": ">=3.11",
    "python_matrix": ["3.11", "3.12", "3.13"],
    "node_floor": ">=22",
    "node_matrix": ["22", "24"],
}


def test_extract_block_takes_only_the_marked_region():
    assert ccc.extract_block(DOC) == BLOCK


def test_extract_block_skips_a_fenced_worked_example():
    # constraints.md shows the marker format inside a code fence before the
    # real block; the example must not be taken for the canonical block.
    # The real file indents the fence under a numbered list item.
    doc = "intro\n\n1. copy it:\n\n   ```\n   <!-- constraints:begin -->\n   ...example...\n   <!-- constraints:end -->\n   ```\n\n" + DOC
    assert ccc.extract_block(doc) == BLOCK


def test_extract_block_missing_markers_raises():
    try:
        ccc.extract_block("no markers here")
    except ccc.ConstraintsError:
        return
    raise AssertionError("expected ConstraintsError")


def test_block_values_parse_every_checked_line():
    assert ccc.read_block_values(BLOCK) == SOURCES


def test_compare_is_clean_when_block_matches_sources():
    assert ccc.compare(SOURCES, SOURCES) == []


def test_stale_release_version_is_flagged():
    # The real-world case: manifests moved 0.9.0 -> 0.10.0 and the canonical
    # file kept saying 0.9.0 while every gate stayed green.
    block = dict(SOURCES, release_version="0.9.0")
    findings = ccc.compare(block, SOURCES)
    assert [f.key for f in findings] == ["release_version"]
    assert findings[0].stated == "0.9.0"
    assert findings[0].actual == "0.10.0"


def test_ci_matrix_drift_is_flagged():
    # ci.yml gains a version without constraints.md being touched (#248).
    sources = dict(SOURCES, python_matrix=["3.11", "3.12", "3.13", "3.14"])
    findings = ccc.compare(SOURCES, sources)
    assert [f.key for f in findings] == ["python_matrix"]


def test_node_matrix_drift_is_flagged():
    sources = dict(SOURCES, node_matrix=["22"])
    findings = ccc.compare(SOURCES, sources)
    assert [f.key for f in findings] == ["node_matrix"]


def test_missing_block_line_is_a_finding_not_a_pass():
    # If a line is reworded so the parser cannot find it, the gate must say
    # so — silently checking fewer constraints is the #249 failure shape.
    block = {k: v for k, v in SOURCES.items() if k != "node_floor"}
    findings = ccc.compare(block, SOURCES)
    assert [f.key for f in findings] == ["node_floor"]
    assert findings[0].stated is None


def test_node_floor_spacing_is_normalised():
    assert ccc.normalise_range(">= 22") == ">=22"
    assert ccc.normalise_range(">=22") == ">=22"


def test_ci_matrix_lists_are_read_from_yaml_text():
    ci = textwrap.dedent("""\
        jobs:
          js:
            strategy:
              matrix:
                node: ["20", "22"]
          python:
            strategy:
              matrix:
                python: ["3.11", "3.12", "3.13"]
        """)
    assert ccc.read_ci_matrix(ci, "node") == ["20", "22"]
    assert ccc.read_ci_matrix(ci, "python") == ["3.11", "3.12", "3.13"]


def test_the_real_repo_is_consistent():
    # The gate applied to this checkout: the canonical file must state what
    # the manifests, provenance source, pyproject, and ci.yml actually hold.
    findings = ccc.run(_ROOT)
    assert findings == [], "\n".join(ccc.format_finding(f) for f in findings)

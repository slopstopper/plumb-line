"""test_eval_scaffolds — each eval case stages the committed fixture, and
only it (#530 review of the 2026-09-30 run).

A scaffold copied the fixture directory whole, including files git ignores,
then deleted every line naming a violation from every file. The js fixture's
untracked node_modules held ESLint, whose source has such lines, so every js
run audited a fixture whose linter crashed. A run must audit what the
repository holds: the fixture's tracked files, less the answer key and
README, with no line naming a violation.

Run from the repo root:  python3 -m pytest -q scripts/test_eval_scaffolds.py
"""
import glob
import os
import subprocess

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAFFOLDS = sorted(glob.glob(os.path.join(_ROOT, "evals", "audit-*", "scaffold.sh")))
FIXTURE = {
    "audit-js-broken": "examples/js-payments-service/broken",
    "audit-js-clean": "examples/js-payments-service/clean",
    "audit-py-broken": "examples/python-data-pipeline/broken",
    "audit-py-clean": "examples/python-data-pipeline/clean",
}


def _tracked(rel):
    out = subprocess.run(["git", "ls-files", "-z", "--", "."], cwd=os.path.join(_ROOT, rel),
                         capture_output=True, check=True).stdout
    return {p.decode() for p in out.split(b"\0") if p}


def _staged(dest):
    found = set()
    for base, dirs, files in os.walk(dest):
        for f in files:
            found.add(os.path.relpath(os.path.join(base, f), dest))
    return found


def test_four_scaffolds_found():
    assert [os.path.basename(os.path.dirname(s)) for s in SCAFFOLDS] == sorted(FIXTURE)


@pytest.mark.parametrize("scaffold", SCAFFOLDS, ids=lambda s: os.path.basename(os.path.dirname(s)))
def test_a_scaffold_stages_the_committed_fixture_and_only_it(scaffold, tmp_path):
    case = os.path.basename(os.path.dirname(scaffold))
    subprocess.run(["bash", scaffold], cwd=tmp_path, check=True, capture_output=True)
    dest = tmp_path / "fixture"
    expected = _tracked(FIXTURE[case]) - {"VIOLATIONS.md", "README.md"}
    assert _staged(dest) == expected
    for rel in expected:
        text = (dest / rel).read_bytes().decode("utf-8", "replace")
        assert "violation" not in text.lower(), rel

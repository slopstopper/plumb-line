"""test_eval_scaffolds — each eval case stages the committed fixture, and
only it (#530 review of the 2026-09-30 run).

A scaffold copied the fixture directory whole, including files git ignores,
then deleted every line naming a violation from every file. The js fixture's
untracked node_modules held ESLint, whose source has such lines, so every js
run audited a fixture whose linter crashed. A run must audit the fixture the
record names: its files at HEAD, less the answer key and README, with no line
naming a violation, and never nothing.

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


def _committed(rel):
    """The fixture's files at HEAD, the commit a run's record names."""
    out = subprocess.run(["git", "ls-tree", "-r", "-z", "--name-only", f"HEAD:{rel}"], cwd=_ROOT,
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
    expected = _committed(FIXTURE[case]) - {"VIOLATIONS.md", "README.md"}
    assert expected, "the fixture has no committed files: an empty staging would pass"
    assert _staged(dest) == expected
    for rel in expected:
        text = (dest / rel).read_bytes().decode("utf-8", "replace")
        assert "violation" not in text.lower(), rel


def test_a_scaffold_fails_loudly_when_no_fixture_is_committed(tmp_path):
    # The 2026-09-28 failure mode: a case auditing an empty directory. A
    # scaffold copied into a repository where its fixture is not committed
    # must exit non-zero, not stage nothing.
    repo = tmp_path / "repo"
    case = repo / "evals" / "audit-x"
    fixture = repo / "examples" / "js-payments-service" / "broken"
    case.mkdir(parents=True)
    fixture.mkdir(parents=True)
    (fixture / "a.js").write_text("export const a = 1;\n")
    src = open(SCAFFOLDS[0], encoding="utf-8").read()
    (case / "scaffold.sh").write_text(src)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q",
                    "--allow-empty", "-m", "empty"], cwd=repo, check=True)
    work = tmp_path / "work"
    work.mkdir()
    r = subprocess.run(["bash", str(case / "scaffold.sh")], cwd=work, capture_output=True, text=True)
    assert r.returncode != 0, r.stdout + r.stderr

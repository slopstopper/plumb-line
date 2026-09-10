"""Tests for scripts/check-constraints-drift.sh — the constraints-copy drift gate.

Run from the repo root:

    python3 -m pytest -q scripts/test_constraints_drift.py

The gate is a bash script over git history, so each case builds a throwaway
git repo under tmp_path, commits a canonical docs/constraints.md, and runs
the script there. Until #249 the gate had no tests at all: an empty, exit-0
run was indistinguishable from a run that verified every copy clean.
"""
import os
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SCRIPT = os.path.join(_HERE, "check-constraints-drift.sh")

BLOCK = "- Release version is **1.2.3**.\n- Floor is **x**.\n"
CANONICAL = (
    "# Constraints\n\nCopy it like this:\n\n"
    "   ```\n   <!-- constraints-copy: docs/constraints.md @ 0000000 -->\n"
    "   <!-- constraints:begin -->\n   ...example...\n   <!-- constraints:end -->\n   ```\n\n"
    "<!-- constraints:begin -->\n" + BLOCK + "<!-- constraints:end -->\n\n## Why\n"
)


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True).stdout.strip()


def _repo(tmp_path, canonical=CANONICAL):
    repo = str(tmp_path / "repo")
    os.makedirs(os.path.join(repo, "docs"))
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    with open(os.path.join(repo, "docs", "constraints.md"), "w") as fh:
        fh.write(canonical)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "canonical")
    return repo, _git(repo, "rev-parse", "--short", "HEAD")


def _add_copy(repo, sha, block=BLOCK, name="docs/plan.md"):
    with open(os.path.join(repo, name), "w") as fh:
        fh.write("# Plan\n\n<!-- constraints-copy: docs/constraints.md @ %s -->\n"
                 "<!-- constraints:begin -->\n%s<!-- constraints:end -->\n" % (sha, block))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "copy")


def _run(repo):
    p = subprocess.run(["bash", _SCRIPT], cwd=repo, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def test_zero_copies_passes_but_says_so(tmp_path):
    repo, _sha = _repo(tmp_path)
    rc, out = _run(repo)
    assert rc == 0
    assert "0 copies" in out, out
    assert "docs/constraints.md" in out


def test_one_clean_copy_is_counted(tmp_path):
    repo, sha = _repo(tmp_path)
    _add_copy(repo, sha)
    rc, out = _run(repo)
    assert rc == 0
    assert "1 cop" in out and "0 drifted" in out, out


def test_drifted_copy_fails_and_is_counted(tmp_path):
    repo, sha = _repo(tmp_path)
    _add_copy(repo, sha, block="- Release version is **9.9.9**.\n- Floor is **x**.\n")
    rc, out = _run(repo)
    assert rc == 1
    assert "DRIFT-GATE FAIL" in out
    assert "1 cop" in out and "1 drifted" in out, out


def test_fenced_example_in_canonical_is_not_a_copy(tmp_path):
    # The canonical file's own worked example must count as documentation.
    repo, _sha = _repo(tmp_path)
    rc, out = _run(repo)
    assert rc == 0
    assert "0 copies" in out, out


def test_renamed_markers_in_canonical_fail_loudly(tmp_path):
    # The #249 case: a refactor renames the markers, so the gate's grep finds
    # nothing anywhere and would previously exit 0 as a silent no-op.
    canonical = CANONICAL.replace("constraints:begin", "limits:begin").replace("constraints:end", "limits:end")
    repo, _sha = _repo(tmp_path, canonical=canonical)
    rc, out = _run(repo)
    assert rc == 1
    assert "DRIFT-GATE FAIL" in out and "docs/constraints.md" in out, out


def test_missing_canonical_file_fails_loudly(tmp_path):
    repo, _sha = _repo(tmp_path)
    os.remove(os.path.join(repo, "docs", "constraints.md"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "moved")
    rc, out = _run(repo)
    assert rc == 1
    assert "DRIFT-GATE FAIL" in out, out


def test_the_real_repo_passes_and_reports_a_count():
    p = subprocess.run(["bash", _SCRIPT], cwd=_ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "copies" in p.stdout, p.stdout



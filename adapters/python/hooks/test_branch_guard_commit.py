"""The git commit hook's pure parts, and the hook as bootstrap Step 4 wires it
(#464). Behaviour against a real repository is the shared table's
(test_commit_hook_cases.py). JS twin:
adapters/js/hooks/__tests__/branch-guard-commit.test.mjs."""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from branch_guard_commit import (  # noqa: E402
    branch_from_ref, judge_commit, rebase_branch, staged_paths, update_ref_branches)

_HERE = os.path.dirname(os.path.abspath(__file__))


def test_branch_from_ref_strips_refs_heads_slashes_kept():
    assert branch_from_ref("refs/heads/main") == "main"
    assert branch_from_ref("refs/heads/release/1.x") == "release/1.x"


def test_branch_from_ref_is_none_outside_refs_heads_or_for_gits_short_form():
    assert branch_from_ref("refs/tags/v1") is None
    assert branch_from_ref("heads/main") is None
    assert branch_from_ref("main") is None


def test_staged_paths_splits_nul_terminated_paths_spaces_and_newlines_kept():
    assert staged_paths(b"a b.md\0src/x\ny.js\0") == ["a b.md", "src/x\ny.js"]


def test_staged_paths_is_empty_for_nothing_staged():
    assert staged_paths(b"") == []


def test_staged_paths_decodes_bytes_that_are_not_utf8_as_ufffd_and_keeps_a_bom():
    assert staged_paths(bytes.fromhex("7372632fff2e6a7300efbbbf612e6d6400")) == ["src/�.js", "﻿a.md"]


def test_judge_commit_allows_every_path_on_an_unprotected_branch():
    assert judge_commit("feat", ["src/a.js"], {})["allow"] is True


def test_judge_commit_uses_the_guards_defaults_with_an_empty_config():
    assert judge_commit("main", ["src/a.js"], {}) == {
        "allow": False,
        "reason": "blocked: code edit to src/a.js on protected branch main. Branch first.",
    }


def test_judge_commit_stops_at_the_first_blocked_path():
    r = judge_commit("main", ["docs/a.md", "src/b.js", "src/c.js"], {"docsAllowlist": ["docs/"]})
    assert "src/b.js" in r["reason"]


def test_judge_commit_names_head_not_plumbline_branch_when_head_is_on_no_branch():
    r = judge_commit(None, ["src/a.js"], {})
    assert r["reason"] == ("blocked: code edit to src/a.js with the branch unknown "
                           "(HEAD is not on a branch). Switch to a branch first.")
    assert "PLUMBLINE_BRANCH" not in r["reason"]


def test_judge_commit_names_head_for_a_branch_git_would_not_accept():
    r = judge_commit("-x", ["src/a.js"], {"protectedBranches": []})
    assert r["reason"] == ('blocked: code edit to src/a.js with the branch unknown '
                           '(HEAD is on "-x", which is not a branch name). Switch to a branch first.')


def test_the_wrapper_imports_its_guard_under_python_dash_p(tmp_path):
    """-P (PYTHONSAFEPATH) leaves the script's directory off sys.path; the
    wrapper names it itself, so it runs and judges rather than failing to
    import (exit 1)."""
    env = dict(_ENV, GIT_CEILING_DIRECTORIES=str(tmp_path))
    r = subprocess.run([sys.executable, "-P", os.path.join(_HERE, "branch_guard_commit.py")],
                       cwd=tmp_path, env=env, capture_output=True, text=True)
    assert r.returncode == 2
    assert r.stderr == ("blocked: the branch guard's commit hook could not read the branch "
                        "(git symbolic-ref exited 128).\n")


def test_judge_commit_allows_docs_on_no_branch_and_nothing_staged_anywhere():
    assert judge_commit(None, ["docs/a.md"], {"docsAllowlist": ["docs/"]})["allow"] is True
    assert judge_commit("main", [], {})["allow"] is True


# The wiring bootstrap Step 4 writes: the wrapper copied next to the guard in
# .claude/guards/, and a pre-commit hook that runs it, then the test gate. Run
# through a real `git commit`, so the verification is of the wiring, not of the
# wrapper alone. JS twin: "the hook as bootstrap Step 4 wires it".
_ENV = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "PLUMBLINE_"))}
_ENV.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, env=_ENV, capture_output=True, text=True)


def _hook_path(repo):
    hooks = os.path.join(repo, _git(repo, "rev-parse", "--git-path", "hooks").stdout.strip())
    os.makedirs(hooks, exist_ok=True)
    return os.path.join(hooks, "pre-commit")


def _write_hook(repo, text):
    hook = _hook_path(repo)
    with open(hook, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(hook, 0o755)


def _wired_repo(tmp_path):
    repo = str(tmp_path / "repo")
    os.mkdir(repo)
    _git(repo, "init", "-q")
    _git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    guards = os.path.join(repo, ".claude", "guards")
    os.makedirs(guards)
    for f in ("branch_guard.py", "branch_guard_commit.py", "pre_commit_gate.py"):
        shutil.copy(os.path.join(_HERE, f), guards)
    with open(os.path.join(guards, "branch-guard.json"), "w", encoding="utf-8") as f:
        f.write('{"protectedBranches": ["main"], "docsAllowlist": ["docs/", "*.md"]}\n')
    py = sys.executable
    _write_hook(repo, "\n".join([
        "#!/bin/sh",
        "# plumb-line (bootstrap Step 4): the branch guard, then the test gate.",
        'PLUMBLINE_CFG="$(cat .claude/guards/branch-guard.json)"',
        "export PLUMBLINE_CFG",
        f"'{py}' .claude/guards/branch_guard_commit.py || exit 1",
        f"""PLUMBLINE_TEST_CMD="'{py}' -c pass" '{py}' .claude/guards/pre_commit_gate.py || exit 1""",
        "",
    ]))
    _stage(repo, "README.md")
    assert _git(repo, "commit", "-q", "-m", "base").returncode == 0  # docs on main: allowed
    return repo


def _stage(repo, p):
    full = os.path.join(repo, p)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write("x\n")
    _git(repo, "add", p)


def _head(repo):
    return _git(repo, "rev-parse", "HEAD").stdout


def test_the_bootstrap_wiring_refuses_a_code_commit_on_main_and_makes_no_commit(tmp_path):
    repo = _wired_repo(tmp_path)
    before = _head(repo)
    _stage(repo, "src/a.py")
    r = _git(repo, "commit", "-q", "-m", "code")
    assert r.returncode == 1
    assert r.stderr == "blocked: code edit to src/a.py on protected branch main. Branch first.\n"
    assert _head(repo) == before


def test_the_bootstrap_wiring_commits_docs_on_main_and_code_on_a_branch(tmp_path):
    repo = _wired_repo(tmp_path)
    _stage(repo, "docs/guide.md")
    assert _git(repo, "commit", "-q", "-m", "docs").returncode == 0
    _stage(repo, "src/a.py")
    _git(repo, "switch", "-q", "-c", "feat")  # the staged change comes along
    r = _git(repo, "commit", "-q", "-m", "code")
    assert r.stderr == ""
    assert r.returncode == 0


def test_added_to_an_existing_hook_with_lines_after_it_a_failing_gate_still_refuses(tmp_path):
    repo = _wired_repo(tmp_path)
    py = sys.executable
    _write_hook(repo, "\n".join([
        "#!/bin/sh",
        "echo existing-before",
        'PLUMBLINE_CFG="$(cat .claude/guards/branch-guard.json)"',
        "export PLUMBLINE_CFG",
        f"'{py}' .claude/guards/branch_guard_commit.py || exit 1",
        f"""PLUMBLINE_TEST_CMD="'{py}' -c 'raise SystemExit(1)'" '{py}' .claude/guards/pre_commit_gate.py || exit 1""",
        "echo existing-after",
        "",
    ]))
    _git(repo, "switch", "-q", "-c", "feat")
    _stage(repo, "src/a.py")
    before = _head(repo)
    r = _git(repo, "commit", "-q", "-m", "code")
    assert r.returncode == 1
    assert "pre-commit blocked:" in r.stderr
    assert _head(repo) == before


def test_the_bootstrap_wiring_still_runs_the_test_gate_after_the_branch_guard(tmp_path):
    repo = _wired_repo(tmp_path)
    py = sys.executable
    # A failing test command: the gate, not the branch guard, refuses.
    _write_hook(repo, f"#!/bin/sh\n'{py}' .claude/guards/branch_guard_commit.py || exit 1\n"
                      f"""PLUMBLINE_TEST_CMD="'{py}' -c 'raise SystemExit(1)'" exec '{py}' """
                      ".claude/guards/pre_commit_gate.py\n")
    _git(repo, "switch", "-q", "-c", "feat")
    _stage(repo, "src/a.py")
    r = _git(repo, "commit", "-q", "-m", "code")
    assert r.returncode == 1
    assert "pre-commit blocked:" in r.stderr


def test_judge_commit_gives_the_reason_it_is_handed_when_the_branch_is_unknown():
    # #547: the reason a rebase in progress gives, and ignored when known.
    assert judge_commit(None, ["src/a.js"], {}, "a reason")["reason"] == (
        "blocked: code edit to src/a.js with the branch unknown (a reason). Switch to a branch first.")
    assert judge_commit("main", ["src/a.js"], {}, "a reason")["reason"] == (
        "blocked: code edit to src/a.js on protected branch main. Branch first.")


def test_rebase_branch_takes_the_branch_from_a_head_name_ref():
    assert rebase_branch("rebase-merge", b"refs/heads/feat\n", None) == {"branch": "feat"}
    assert rebase_branch("rebase-apply", b"refs/heads/main", None) == {"branch": "main"}


def test_rebase_branch_names_a_head_name_it_cannot_read():
    assert rebase_branch("rebase-merge", None, "ENOENT") == {
        "branch": None, "why": "HEAD is detached by a rebase whose rebase-merge/head-name cannot be read: ENOENT"}


def test_rebase_branch_refuses_a_head_name_that_is_not_a_branch_or_branch_name():
    assert rebase_branch("rebase-merge", b"detached HEAD\n", None) == {
        "branch": None, "why": 'HEAD is detached by a rebase of "detached HEAD", which is not a branch'}
    assert rebase_branch("rebase-merge", b"refs/heads/-x\n", None) == {
        "branch": "-x", "why": 'HEAD is detached by a rebase of "-x", which is not a branch name'}


def test_rebase_branch_decodes_a_head_name_that_is_not_utf8_with_replacement():
    assert rebase_branch("rebase-merge", b"refs/heads/f\xff\n", None)["branch"] == "f\ufffd"


def test_rebase_branch_keeps_a_leading_bom_as_the_js_twin_does():
    # #547 review: JS's default TextDecoder stripped it.
    assert rebase_branch("rebase-merge", b"\xef\xbb\xbfrefs/heads/feat\n", None) == {
        "branch": None, "why": 'HEAD is detached by a rebase of "\ufeffrefs/heads/feat", which is not a branch'}


def test_rebase_branch_names_git_am_beside_a_rebase_for_rebase_apply():
    assert rebase_branch("rebase-apply", None, "ENOENT")["why"] == (
        "HEAD is detached by a rebase or git am whose rebase-apply/head-name cannot be read: ENOENT")


def test_update_ref_branches_takes_each_refs_first_line_branches_only():
    z = b"0" * 40
    assert update_ref_branches(b"refs/heads/main\n" + b"a" * 40 + b"\n" + z + b"\nrefs/heads/other\n"
                               + z + b"\n" + z + b"\n") == ["main", "other"]
    assert update_ref_branches(b"refs/tags/v1\n" + z + b"\n" + z + b"\n") == []
    assert update_ref_branches(b"") == []

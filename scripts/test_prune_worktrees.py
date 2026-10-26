"""Tests for scripts/prune_worktrees.py — removes linked git worktrees that are
provably safe to remove (GH #668).

Run from the repo root:

    python3 -m pytest -q scripts/test_prune_worktrees.py

Every test drives a real throwaway repository (a bare "origin", a clone, and
real `git worktree add` checkouts), because the script's whole job is to be
right about what git says. Needs git >= 2.32 (`GIT_CONFIG_GLOBAL`, which keeps
the user's config out of the tests). Mirrors scripts/test_content_language.py:
the script is loaded by path under a private module name.

The cases are the ones the 2026-10-23 manual cleanup (44 of 45 worktrees) had
to handle by hand — a local `main` behind `origin/main`, ignored files that
exist nowhere else, branches that only look merged, agent locks — plus the
ways "clean" can be wrong that an independent review of the first version found
(edits git is told not to see, config that hides untracked files, submodules,
a change landing after the check, two worktrees with one name).
"""
import importlib.util
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "prune_worktrees.py")
_spec = importlib.util.spec_from_file_location("_prune_worktrees", _SCRIPT)
pw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pw)
_REAL_PROCESS_CWDS = pw.process_cwds

_GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@example.com",
}


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch):
    """Git sees no user config; no real process is ever 'inside' a worktree
    unless a test says so."""
    for k, v in _GIT_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(pw, "process_cwds", lambda: [])


def git(cwd, *args, check=True):
    return subprocess.run(["git", "-C", str(cwd), *args], check=check,
                          capture_output=True, text=True)


def admin_dir(path):
    return git(path, "rev-parse", "--absolute-git-dir").stdout.strip()


class Repo:
    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.ages = {}
        self.origin = tmp_path / "origin.git"
        self.work = tmp_path / "work"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.work)],
                       check=True, capture_output=True)
        (self.work / ".gitignore").write_text("node_modules/\ndocs/plans/\n*.log\n")
        (self.work / "README.md").write_text("base\n")
        git(self.work, "add", "-A")
        git(self.work, "commit", "-q", "-m", "base")
        git(self.work, "push", "-q", "-u", "origin", "main")

    def worktree(self, name, branch=None, detach=False, age_hours=48, where="wts", checkout=None):
        path = self.tmp / where / name
        if checkout:
            git(self.work, "worktree", "add", "-q", str(path), checkout)
        elif detach:
            git(self.work, "worktree", "add", "-q", "--detach", str(path), "origin/main")
        else:
            git(self.work, "worktree", "add", "-q", "-b", branch or f"b-{name}",
                str(path), "origin/main")
        self.ages[path] = age_hours
        return path

    @staticmethod
    def age(path, hours):
        """Make the worktree look untouched for `hours` hours."""
        t = time.time() - hours * 3600
        for f in ("index", "HEAD"):
            p = os.path.join(admin_dir(path), f)
            if os.path.exists(p):
                os.utime(p, (t, t))

    def commit(self, path, fname=None, text="x\n"):
        """Commit one file. The message is unique per call: the same content
        committed twice in one second would otherwise be the same commit."""
        self.commits = getattr(self, "commits", 0) + 1
        fname = fname or f"change-{self.commits}.txt"
        (path / fname).write_text(text)
        git(path, "add", "-A")
        git(path, "commit", "-q", "-m", f"edit {fname} (#{self.commits})")
        return git(path, "rev-parse", "HEAD").stdout.strip()

    def merge_into_origin_main(self, sha):
        """Land `sha` on origin/main the way a merged PR does (fast-forward
        here), without touching the local `main` branch."""
        git(self.work, "push", "-q", "origin", f"{sha}:refs/heads/main")


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path)


def run_prune(repo, *args):
    # Setup commits touch a worktree; backdate each one just before the run so
    # "how long since it was touched" is what the test says it is.
    for path, hours in repo.ages.items():
        if path.exists():
            Repo.age(path, hours)
    return pw.run(["--repo", str(repo.work), *args])


def verdict_line(out, name):
    lines = [ln for ln in out.splitlines() if f" {name} " in f" {ln} "]
    assert len(lines) == 1, f"expected one line for {name!r}, got {lines!r} in:\n{out}"
    return lines[0]


def archived(arch, name):
    """The one archive directory for worktree `name` (named <name>-<hash>)."""
    found = [d for d in Path(arch).iterdir() if d.name.startswith(f"{name}-")]
    assert len(found) == 1, f"expected one archive for {name!r} in {arch}, got {found}"
    return found[0]


# --- the safe case -------------------------------------------------------

def test_dry_run_reports_a_merged_clean_worktree_and_changes_nothing(repo, capsys):
    wt = repo.worktree("done")
    repo.merge_into_origin_main(repo.commit(wt))
    before = git(repo.work, "worktree", "list", "--porcelain").stdout

    assert run_prune(repo) == 0
    out = capsys.readouterr().out

    assert verdict_line(out, "done").startswith("REMOVE")
    assert "dry run" in out
    assert wt.exists()
    assert git(repo.work, "worktree", "list", "--porcelain").stdout == before
    assert git(repo.work, "rev-parse", "--verify", "-q", "b-done").stdout.strip()


def test_apply_removes_the_worktree_and_its_merged_branch(repo, capsys):
    wt = repo.worktree("done")
    repo.merge_into_origin_main(repo.commit(wt))

    assert run_prune(repo, "--apply") == 0
    capsys.readouterr()

    assert not wt.exists()
    assert "done" not in git(repo.work, "worktree", "list").stdout
    assert git(repo.work, "rev-parse", "--verify", "-q", "b-done", check=False).returncode != 0


def test_a_fresh_worktree_with_no_commits_of_its_own_is_removable_once_old(repo, capsys):
    # Sitting exactly at origin/main is an ancestor of it: nothing is lost.
    wt = repo.worktree("empty")
    assert run_prune(repo, "--apply") == 0
    capsys.readouterr()
    assert not wt.exists()


# --- what must never be removed: "clean" ---------------------------------

def test_keeps_a_worktree_with_tracked_changes(repo, capsys):
    wt = repo.worktree("dirty")
    (wt / "README.md").write_text("edited\n")
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "dirty").startswith("KEEP")
    assert "tracked changes" in verdict_line(out, "dirty")
    assert (wt / "README.md").read_text() == "edited\n"


def test_keeps_a_worktree_with_untracked_files(repo, capsys):
    wt = repo.worktree("scratch")
    (wt / "notes.png").write_bytes(b"\x89PNG")
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "scratch").startswith("KEEP")
    assert "untracked files" in verdict_line(out, "scratch")
    assert (wt / "notes.png").exists()


@pytest.mark.parametrize("flag", ["--skip-worktree", "--assume-unchanged"])
def test_keeps_a_worktree_whose_edits_git_is_told_not_to_see(repo, capsys, flag):
    # `git status` is blind to both flags (skip-worktree is what sparse
    # checkout sets), so an edit under either looks clean.
    wt = repo.worktree("hidden")
    git(wt, "update-index", flag, "README.md")
    (wt / "README.md").write_text("precious edit\n")
    assert git(wt, "status", "--porcelain").stdout == ""  # the premise
    assert run_prune(repo, "--apply") == 0
    line = verdict_line(capsys.readouterr().out, "hidden")
    assert line.startswith("KEEP") and "hidden from status" in line
    assert (wt / "README.md").read_text() == "precious edit\n"


def test_untracked_files_are_seen_even_when_config_says_to_hide_them(repo, capsys):
    wt = repo.worktree("cfg")
    git(repo.work, "config", "status.showUntrackedFiles", "no")
    (wt / "precious.txt").write_text("only copy\n")
    assert git(wt, "status", "--porcelain").stdout == ""  # the premise
    assert run_prune(repo, "--apply") == 0
    line = verdict_line(capsys.readouterr().out, "cfg")
    assert line.startswith("KEEP") and "untracked files" in line
    assert (wt / "precious.txt").exists()


def test_keeps_a_worktree_with_an_initialised_submodule(repo, capsys, tmp_path):
    # A submodule's git dir lives inside the worktree's admin dir, so removing
    # the worktree takes its local commits with it; superproject status is clean.
    sub = tmp_path / "sub-src"
    subprocess.run(["git", "init", "-q", "-b", "main", str(sub)], check=True)
    (sub / "f.txt").write_text("f\n")
    git(sub, "add", "-A")
    git(sub, "commit", "-q", "-m", "sub")
    git(repo.work, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(sub), "sm")
    git(repo.work, "commit", "-q", "-m", "add submodule")
    git(repo.work, "push", "-q", "origin", "main")

    wt = repo.worktree("withsub")
    git(wt, "-c", "protocol.file.allow=always", "submodule", "update", "--init", "-q")
    assert run_prune(repo, "--apply") == 0
    line = verdict_line(capsys.readouterr().out, "withsub")
    assert line.startswith("KEEP") and "submodule" in line
    assert wt.exists()


@pytest.mark.parametrize("marker", ["rebase-merge", "rebase-apply", "sequencer", "MERGE_HEAD",
                                    "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG"])
def test_keeps_a_worktree_with_an_operation_in_progress(repo, capsys, marker):
    wt = repo.worktree("midway")
    target = Path(admin_dir(wt)) / marker
    if marker in ("rebase-merge", "rebase-apply", "sequencer"):
        target.mkdir()
    else:
        target.write_text("x\n")
    assert run_prune(repo, "--apply") == 0
    line = verdict_line(capsys.readouterr().out, "midway")
    assert line.startswith("KEEP") and "operation in progress" in line
    assert wt.exists()


def test_keeps_a_worktree_in_the_middle_of_a_real_bisect(repo, capsys):
    # The marker files above are fabricated; this one is git's own.
    wt = repo.worktree("bisecting")
    git(wt, "bisect", "start")
    assert (Path(admin_dir(wt)) / "BISECT_LOG").exists()  # the premise
    assert run_prune(repo, "--apply") == 0
    line = verdict_line(capsys.readouterr().out, "bisecting")
    assert line.startswith("KEEP") and "operation in progress" in line
    assert wt.exists()


# --- what must never be removed: commits only the worktree itself holds --

def test_keeps_a_detached_worktree_whose_earlier_commits_only_its_reflog_holds(repo, capsys):
    # Commit while detached, then move HEAD back to origin/main: HEAD is now an
    # ancestor of the base and the tree is clean, but the commit is reachable
    # from nothing except this worktree's reflog, which removal deletes.
    wt = repo.worktree("wandered", detach=True)
    repo.commit(wt)
    git(wt, "checkout", "-q", "--detach", "origin/main")
    assert git(wt, "status", "--porcelain").stdout == ""  # the premise
    assert run_prune(repo, "--apply") == 0
    line = verdict_line(capsys.readouterr().out, "wandered")
    assert line.startswith("KEEP") and "held only by this worktree" in line
    assert wt.exists()


def test_keeps_a_worktree_whose_commit_only_a_per_worktree_ref_holds(repo, capsys):
    wt = repo.worktree("sideref")
    sha = repo.commit(wt)
    git(wt, "update-ref", "refs/worktree/side", sha)
    git(wt, "reset", "-q", "--hard", "origin/main")
    git(wt, "reflog", "expire", "--expire=now", "--all")
    assert git(repo.work, "branch", "--contains", sha).stdout.strip() == ""  # the premise
    assert run_prune(repo, "--apply") == 0
    line = verdict_line(capsys.readouterr().out, "sideref")
    assert line.startswith("KEEP") and "held only by this worktree" in line
    assert wt.exists()


@pytest.mark.parametrize("holder", ["branch", "tag", "remote"])
def test_earlier_commits_are_fine_when_a_branch_tag_or_remote_holds_them(repo, capsys, holder):
    wt = repo.worktree("wandered-safely", detach=True)
    sha = repo.commit(wt)
    ref = {"branch": "refs/heads/keeps-it", "tag": "refs/tags/keeps-it", "remote": "refs/remotes/origin/keeps-it"}[holder]
    git(repo.work, "update-ref", ref, sha)
    git(wt, "checkout", "-q", "--detach", "origin/main")
    assert run_prune(repo, "--apply") == 0
    capsys.readouterr()
    assert not wt.exists()
    assert git(repo.work, "rev-parse", "--verify", "-q", ref).stdout.strip() == sha


def test_keeps_a_worktree_that_committed_while_detached_and_was_then_switched_to_a_branch(repo, capsys):
    # The reflog is the only thing holding the commit, and it does not matter
    # that HEAD is attached again by the time anyone looks.
    git(repo.work, "branch", "other", "origin/main")
    wt = repo.worktree("switched", detach=True)
    sha = repo.commit(wt)
    git(wt, "switch", "-q", "other")
    assert git(repo.work, "branch", "--contains", sha).stdout.strip() == ""  # the premise
    assert run_prune(repo, "--apply") == 0
    line = verdict_line(capsys.readouterr().out, "switched")
    assert line.startswith("KEEP") and "held only by this worktree" in line
    assert wt.exists()


def test_keeps_a_branch_worktree_that_abandoned_a_commit_by_resetting(repo, capsys):
    wt = repo.worktree("abandoner")
    sha = repo.commit(wt)
    git(wt, "reset", "-q", "--hard", "origin/main")
    assert git(repo.work, "branch", "--contains", sha).stdout.strip() == ""  # the premise
    assert run_prune(repo, "--apply") == 0
    line = verdict_line(capsys.readouterr().out, "abandoner")
    assert line.startswith("KEEP") and "held only by this worktree" in line
    assert "--ignore-reflog" in line  # and the way to accept the loss is named
    assert wt.exists()


def test_ignore_reflog_accepts_losing_what_only_the_reflog_holds(repo, capsys):
    wt = repo.worktree("abandoner")
    repo.commit(wt)
    git(wt, "reset", "-q", "--hard", "origin/main")
    assert run_prune(repo, "--apply", "--ignore-reflog") == 0
    capsys.readouterr()
    assert not wt.exists()


@pytest.mark.parametrize("ref", ["refs/worktree/side", "refs/bisect/bad", "refs/rewritten/step"])
def test_ignore_reflog_still_keeps_a_commit_a_per_worktree_ref_holds(repo, capsys, ref):
    wt = repo.worktree("sideref2")
    sha = repo.commit(wt)
    git(wt, "update-ref", ref, sha)
    git(wt, "reset", "-q", "--hard", "origin/main")
    git(wt, "reflog", "expire", "--expire=now", "--all")
    assert run_prune(repo, "--apply", "--ignore-reflog") == 0
    line = verdict_line(capsys.readouterr().out, "sideref2")
    assert line.startswith("KEEP") and "held only by this worktree" in line
    assert wt.exists()


# --- what must never be read from the wrong repository -------------------

def test_stray_git_location_variables_do_not_redirect_the_checks(repo, capsys, monkeypatch):
    # A hook or wrapper that exports GIT_DIR / GIT_WORK_TREE would make every
    # check read the main checkout, which has no hidden edit.
    wt = repo.worktree("envy")
    git(wt, "update-index", "--skip-worktree", "README.md")
    (wt / "README.md").write_text("precious edit\n")
    Repo.age(wt, 48)
    monkeypatch.setenv("GIT_DIR", str(repo.work / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(repo.work))
    assert pw.run(["--repo", str(repo.work), "--apply"]) == 0
    line = verdict_line(capsys.readouterr().out, "envy")
    assert line.startswith("KEEP") and "hidden from status" in line
    assert (wt / "README.md").read_text() == "precious edit\n"


def test_a_worktree_git_resolves_to_a_different_directory_is_kept(repo, capsys):
    wt = repo.worktree("redirected")
    Repo.age(wt, 48)
    git(repo.work, "config", "extensions.worktreeConfig", "true")
    git(wt, "config", "--worktree", "core.worktree", str(repo.work))
    assert pw.run(["--repo", str(repo.work), "--apply"]) == 0
    line = verdict_line(capsys.readouterr().out, "redirected")
    assert line.startswith("KEEP") and "could not inspect" in line
    assert wt.exists()


# --- what must never be removed: "merged" --------------------------------

def test_keeps_a_worktree_with_commits_not_in_origin_main(repo, capsys):
    wt = repo.worktree("wip")
    repo.commit(wt)
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "wip").startswith("KEEP")
    assert "not merged into origin/main" in verdict_line(out, "wip")
    assert wt.exists()


def test_a_squash_merged_branch_is_kept_and_named_not_guessed(repo, capsys):
    # The same change lands on origin/main under a different commit, as a
    # squash merge does. The branch is not an ancestor, so the script cannot
    # prove it merged and says so rather than deleting on a guess.
    wt = repo.worktree("squashed")
    repo.commit(wt, "feature.txt", "f\n")
    other = repo.worktree("landing")
    repo.merge_into_origin_main(repo.commit(other, "feature.txt", "f\n"))

    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "squashed").startswith("KEEP")
    assert "not merged into origin/main" in verdict_line(out, "squashed")
    assert wt.exists()


def test_merged_is_judged_against_origin_main_not_local_main(repo, capsys):
    landed = repo.worktree("landed")
    repo.merge_into_origin_main(repo.commit(landed, "a.txt"))
    # Local `main` is still at the base commit, behind origin/main.
    assert git(repo.work, "rev-parse", "main").stdout != git(repo.work, "rev-parse", "origin/main").stdout

    # A branch merged only into the LOCAL main was never pushed: keep it.
    local_only = repo.worktree("local-only")
    sha = repo.commit(local_only, "b.txt")
    git(repo.work, "update-ref", "refs/heads/main", sha)

    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "landed").startswith("REMOVE")
    assert verdict_line(out, "local-only").startswith("KEEP")
    assert local_only.exists()


def test_a_local_base_ref_is_allowed_but_says_it_is_not_a_remote_ref(repo, capsys):
    repo.worktree("x")
    assert run_prune(repo, "--base", "main") == 0
    assert "not a remote-tracking ref" in capsys.readouterr().err


def test_a_detached_worktree_with_unpushed_commits_is_kept(repo, capsys):
    wt = repo.worktree("detached-wip", detach=True)
    repo.commit(wt)
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "detached-wip").startswith("KEEP")
    assert wt.exists()


def test_removes_a_merged_detached_worktree(repo, capsys):
    wt = repo.worktree("detached", detach=True)
    assert run_prune(repo, "--apply") == 0
    capsys.readouterr()
    assert not wt.exists()


# --- what must never be removed: in use, recent, special -----------------

def test_keeps_the_worktree_this_command_is_run_from(repo, capsys, monkeypatch):
    wt = repo.worktree("me")
    monkeypatch.chdir(wt / ".")
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "me").startswith("KEEP")
    assert "current worktree" in verdict_line(out, "me")
    assert wt.exists()


def test_keeps_a_recently_touched_worktree(repo, capsys):
    # A just-created worktree at origin/main looks exactly like a finished one.
    wt = repo.worktree("fresh", age_hours=1)
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "fresh").startswith("KEEP")
    assert "touched within" in verdict_line(out, "fresh")
    assert wt.exists()
    # ...and the window is a flag, not a constant.
    assert run_prune(repo, "--apply", "--min-age-hours", "0.5") == 0
    capsys.readouterr()
    assert not wt.exists()


@pytest.mark.parametrize("old", ["index", "HEAD"])
def test_the_age_is_the_newest_of_index_and_head(repo, capsys, old):
    # Either file alone being recent is enough: one of them is rewritten by
    # `git add`/`checkout`, the other by `git commit`/`reset`.
    wt = repo.worktree("mixed")
    admin = Path(admin_dir(wt))
    long_ago, just_now = time.time() - 48 * 3600, time.time() - 3600
    for f in ("index", "HEAD"):
        t = long_ago if f == old else just_now
        os.utime(admin / f, (t, t))
    assert pw.run(["--repo", str(repo.work), "--apply"]) == 0
    assert verdict_line(capsys.readouterr().out, "mixed").startswith("KEEP")
    assert wt.exists()


def test_a_worktree_touched_exactly_the_window_ago_is_old_enough(repo, capsys, monkeypatch):
    wt = repo.worktree("edge")
    admin = Path(admin_dir(wt))
    now = 2_000_000_000.0
    monkeypatch.setattr(pw, "_now", lambda: now)
    for f in ("index", "HEAD"):
        os.utime(admin / f, (now - 24 * 3600, now - 24 * 3600))
    assert pw.run(["--repo", str(repo.work), "--min-age-hours", "24"]) == 0
    assert verdict_line(capsys.readouterr().out, "edge").startswith("REMOVE")


def test_a_dry_run_does_not_make_a_worktree_look_recently_touched(repo, capsys):
    # `git status` may rewrite a stale index, which would refresh the very mtime
    # the age guard reads and make every later run refuse for 24 hours.
    wt = repo.worktree("quiet")
    os.utime(wt / "README.md", None)  # stat-dirty, content unchanged
    Repo.age(wt, 48)
    admin = admin_dir(wt)
    before = {f: os.path.getmtime(os.path.join(admin, f)) for f in ("index", "HEAD")}
    pw.run(["--repo", str(repo.work)])
    capsys.readouterr()
    assert {f: os.path.getmtime(os.path.join(admin, f)) for f in before} == before


def test_never_offers_the_main_checkout(repo, capsys):
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert "work" not in [ln.split()[1] for ln in out.splitlines()
                          if ln.startswith(("REMOVE", "KEEP"))]
    assert repo.work.exists()


def test_keeps_a_worktree_whose_directory_is_missing_and_says_how_to_clear_it(repo, capsys):
    wt = repo.worktree("gone")
    shutil.rmtree(wt)
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "gone").startswith("KEEP")
    assert "git worktree prune" in verdict_line(out, "gone")


def test_a_worktree_git_cannot_inspect_is_kept_and_the_rest_still_go(repo, capsys):
    bad = repo.worktree("bad")
    good = repo.worktree("good")
    Repo.age(bad, 48)
    Repo.age(good, 48)
    (bad / ".git").write_text("gitdir: /nonexistent/nowhere\n")
    assert pw.run(["--repo", str(repo.work), "--apply"]) == 0  # run_prune would age `bad` through git
    out = capsys.readouterr().out
    assert verdict_line(out, "bad").startswith("KEEP")
    assert "could not inspect" in verdict_line(out, "bad")
    assert bad.exists()
    assert not good.exists()


# --- processes -----------------------------------------------------------

def test_keeps_a_worktree_with_a_process_running_inside_it(repo, capsys, monkeypatch):
    wt = repo.worktree("busy")
    nested = wt / "primitives" / "js"
    nested.mkdir(parents=True)
    monkeypatch.setattr(pw, "process_cwds", lambda: [str(nested.resolve())])
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "busy").startswith("KEEP")
    assert "process running inside" in verdict_line(out, "busy")
    assert wt.exists()


def test_a_process_inside_a_worktree_whose_parent_became_a_symlink_still_counts(repo, capsys, monkeypatch):
    # git resolves symlinks when a worktree is added but keeps listing that
    # path afterwards; a parent directory moved and replaced by a link leaves
    # git saying ".../moved/x" while a process's cwd reads ".../moved-real/x".
    wt = repo.worktree("viasymlink", where="moved")
    os.rename(repo.tmp / "moved", repo.tmp / "moved-real")
    os.symlink(repo.tmp / "moved-real", repo.tmp / "moved", target_is_directory=True)
    assert git(repo.work, "worktree", "list", "--porcelain").stdout.count(str(wt)) == 1  # the premise
    monkeypatch.setattr(pw, "process_cwds", lambda: [os.path.realpath(wt)])
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "viasymlink").startswith("KEEP")
    assert "process running inside" in verdict_line(out, "viasymlink")


def test_a_process_in_a_sibling_directory_with_a_shared_prefix_does_not_count(repo, capsys, monkeypatch):
    # ".../wts/done" must not match a process in ".../wts/done-2".
    wt = repo.worktree("done")
    sibling = repo.tmp / "wts" / "done-2"
    sibling.mkdir(parents=True)
    monkeypatch.setattr(pw, "process_cwds", lambda: [str(sibling.resolve())])
    assert run_prune(repo, "--apply") == 0
    capsys.readouterr()
    assert not wt.exists()


def test_keeps_everything_when_the_process_check_cannot_run(repo, capsys, monkeypatch):
    # Not knowing whether something is in use is not the same as it being free.
    wt = repo.worktree("unknown")
    monkeypatch.setattr(pw, "process_cwds", lambda: None)
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "unknown").startswith("KEEP")
    assert "process check unavailable" in verdict_line(out, "unknown")
    assert wt.exists()


def _fake_lsof(monkeypatch, stdout="", returncode=0, raises=None):
    def run(cmd, **kw):
        if raises:
            raise raises
        return subprocess.CompletedProcess(cmd, returncode, stdout, "")
    monkeypatch.setattr(pw.subprocess, "run", run)


def _listing(*dirs):
    return "".join(f"p{i}\nn{d}\n" for i, d in enumerate(dirs, 100))


def test_process_cwds_reads_lsof_and_requires_its_own_cwd_in_the_listing(monkeypatch):
    me = os.path.realpath(os.getcwd())
    _fake_lsof(monkeypatch, _listing(me, "/somewhere/else"))
    assert _REAL_PROCESS_CWDS() == [me, os.path.realpath("/somewhere/else")]
    # A listing that lacks our own cwd cannot be trusted to be complete.
    _fake_lsof(monkeypatch, _listing("/somewhere/else"))
    assert _REAL_PROCESS_CWDS() is None


def test_process_cwds_accepts_lsofs_partial_listing_status_but_not_a_failure(monkeypatch):
    me = os.path.realpath(os.getcwd())
    _fake_lsof(monkeypatch, _listing(me), returncode=1)  # lsof exits 1 when some files were unreadable
    assert _REAL_PROCESS_CWDS() == [me]
    _fake_lsof(monkeypatch, _listing(me), returncode=2)
    assert _REAL_PROCESS_CWDS() is None


def test_process_cwds_is_none_without_lsof_or_when_it_hangs(monkeypatch):
    _fake_lsof(monkeypatch, raises=FileNotFoundError("lsof"))
    assert _REAL_PROCESS_CWDS() is None
    _fake_lsof(monkeypatch, raises=subprocess.TimeoutExpired("lsof", 60))
    assert _REAL_PROCESS_CWDS() is None


def test_a_real_process_inside_a_worktree_keeps_it(repo, capsys, monkeypatch):
    monkeypatch.setattr(pw, "process_cwds", _REAL_PROCESS_CWDS)
    if _REAL_PROCESS_CWDS() is None:
        pytest.skip("lsof is missing or cannot list this process's cwd")
    wt = repo.worktree("real")
    proc = subprocess.Popen(["sleep", "30"], cwd=wt)
    try:
        time.sleep(0.3)
        assert run_prune(repo, "--apply") == 0
        out = capsys.readouterr().out
        assert verdict_line(out, "real").startswith("KEEP")
        assert "process running inside" in verdict_line(out, "real")
        assert wt.exists()
    finally:
        proc.kill()
        proc.wait()


# --- locks ---------------------------------------------------------------

def test_removes_a_stale_agent_lock_and_reports_it(repo, capsys):
    wt = repo.worktree("locked")
    git(repo.work, "worktree", "lock", "--reason", "claude agent agent-x (pid 1)", str(wt))
    assert run_prune(repo) == 0
    line = verdict_line(capsys.readouterr().out, "locked")
    assert line.startswith("REMOVE")
    assert "locked: claude agent agent-x (pid 1)" in line

    assert run_prune(repo, "--apply") == 0
    capsys.readouterr()
    assert not wt.exists()


@pytest.mark.parametrize("reason", [["--reason", "do not delete"], [],
                                    ["--reason", "claude desktop session, leave alone"]])
def test_a_lock_someone_wrote_is_respected_unless_told_otherwise(repo, capsys, reason):
    wt = repo.worktree("human")
    git(repo.work, "worktree", "lock", *reason, str(wt))
    assert run_prune(repo, "--apply") == 0
    line = verdict_line(capsys.readouterr().out, "human")
    assert line.startswith("KEEP") and "--break-locks" in line
    assert wt.exists()

    assert run_prune(repo, "--apply", "--break-locks") == 0
    capsys.readouterr()
    assert not wt.exists()


def test_a_late_file_in_a_locked_worktree_is_refused_and_the_lock_put_back(repo, capsys, monkeypatch):
    # The locked worktree is the main use case, and the one a blanket
    # `--force --force` would have left with no last line of defence.
    wt = repo.worktree("lockedlate")
    reason = "claude agent agent-z (pid 3)"
    git(repo.work, "worktree", "lock", "--reason", reason, str(wt))
    real = pw.remove_worktree

    def drop_file_then_remove(repo_path, w, locked):
        (w.path / "late.txt").write_text("precious\n")
        return real(repo_path, w, locked)

    monkeypatch.setattr(pw, "remove_worktree", drop_file_then_remove)
    assert run_prune(repo, "--apply") == 1
    assert "FAILED" in capsys.readouterr().out
    assert (wt / "late.txt").read_text() == "precious\n"
    assert f"locked {reason}" in git(repo.work, "worktree", "list", "--porcelain").stdout


def test_a_lock_does_not_override_the_other_checks(repo, capsys):
    wt = repo.worktree("locked-wip")
    repo.commit(wt)
    git(repo.work, "worktree", "lock", "--reason", "claude agent agent-y (pid 2)", str(wt))
    assert run_prune(repo, "--apply", "--break-locks") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "locked-wip").startswith("KEEP")
    assert wt.exists()


# --- ignored files -------------------------------------------------------

def test_archives_ignored_files_a_rebuild_would_not_recreate_before_removing(repo, capsys, tmp_path):
    wt = repo.worktree("plans")
    (wt / "docs" / "plans").mkdir(parents=True)
    (wt / "docs" / "plans" / "p.md").write_text("the only copy\n")
    (wt / "node_modules" / "pkg").mkdir(parents=True)
    (wt / "node_modules" / "pkg" / "index.js").write_text("regenerable\n")
    arch = tmp_path / "arch"

    assert run_prune(repo, "--apply", "--archive-dir", str(arch)) == 0
    out = capsys.readouterr().out

    assert not wt.exists()
    here = archived(arch, "plans")
    assert (here / "docs" / "plans" / "p.md").read_text() == "the only copy\n"
    assert not (here / "node_modules").exists()
    assert str(arch) in out


def test_a_regenerable_directory_inside_an_ignored_one_is_not_archived(repo, capsys, tmp_path):
    # `git ls-files --directory` lists a wholly-ignored directory and its
    # children separately; archiving both collided, and archiving the parent
    # would have copied the regenerable child along with it.
    wt = repo.worktree("nested")
    (wt / "docs" / "plans" / "node_modules" / "pkg").mkdir(parents=True)
    (wt / "docs" / "plans" / "node_modules" / "pkg" / "i.js").write_text("rebuilt by npm ci\n")
    (wt / "docs" / "plans" / "keep.md").write_text("only copy\n")
    arch = tmp_path / "arch"
    assert run_prune(repo, "--apply", "--archive-dir", str(arch)) == 0
    capsys.readouterr()
    here = archived(arch, "nested")
    assert (here / "docs" / "plans" / "keep.md").read_text() == "only copy\n"
    assert not (here / "docs" / "plans" / "node_modules").exists()


def test_a_directory_called_build_is_archived_and_an_egg_info_directory_is_not(repo, capsys, tmp_path):
    # `build`, `dist` and `coverage` are sometimes real output, so they are not
    # assumed regenerable. An *.egg-info directory always is.
    wt = repo.worktree("names")
    plans = wt / "docs" / "plans"
    (plans / "build").mkdir(parents=True)
    (plans / "build" / "notes.md").write_text("notes\n")
    (plans / "pkg.egg-info").mkdir()
    (plans / "pkg.egg-info" / "PKG-INFO").write_text("rebuilt\n")
    arch = tmp_path / "arch"
    assert run_prune(repo, "--apply", "--archive-dir", str(arch)) == 0
    capsys.readouterr()
    here = archived(arch, "names") / "docs" / "plans"
    assert (here / "build" / "notes.md").exists()
    assert not (here / "pkg.egg-info").exists()


def test_an_ignored_file_is_archived_even_when_its_name_is_a_cache_directory_name(repo, capsys, tmp_path):
    # Cache names skip directories. A *file* called `venv` is somebody's file.
    # (Ignored through .git/info/exclude, so the worktree stays clean.)
    with open(repo.work / ".git" / "info" / "exclude", "a") as f:
        f.write("/venv\n")
    wt = repo.worktree("filenamed")
    (wt / "venv").write_text("a file, not a virtualenv\n")
    arch = tmp_path / "arch"
    assert run_prune(repo, "--apply", "--archive-dir", str(arch)) == 0
    capsys.readouterr()
    assert (archived(arch, "filenamed") / "venv").read_text() == "a file, not a virtualenv\n"


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root can read anything")
def test_keeps_a_worktree_with_an_ignored_directory_it_cannot_read(repo, capsys, tmp_path):
    # os.walk swallows errors by default; the files in there would be deleted
    # without ever being archived.
    wt = repo.worktree("locked-dir")
    secret = wt / "docs" / "plans" / "secret"
    secret.mkdir(parents=True)
    (secret / "p.md").write_text("only copy\n")
    secret.chmod(0)
    try:
        assert run_prune(repo, "--apply", "--archive-dir", str(tmp_path / "arch")) == 0
        out = capsys.readouterr().out
    finally:
        secret.chmod(0o755)
    assert verdict_line(out, "locked-dir").startswith("KEEP")
    assert (secret / "p.md").read_text() == "only copy\n"


def test_a_symlink_in_an_ignored_directory_is_archived_as_a_link(repo, capsys, tmp_path):
    wt = repo.worktree("linked")
    plans = wt / "docs" / "plans"
    plans.mkdir(parents=True)
    os.symlink("/nonexistent/target", plans / "dangling")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "big.bin").write_text("not part of this worktree\n")
    os.symlink(elsewhere, plans / "dirlink", target_is_directory=True)
    arch = tmp_path / "arch"
    assert run_prune(repo, "--apply", "--archive-dir", str(arch)) == 0
    capsys.readouterr()
    here = archived(arch, "linked") / "docs" / "plans"
    assert os.readlink(here / "dangling") == "/nonexistent/target"
    assert os.path.islink(here / "dirlink")  # the link, not a copy of what it points at


def test_dry_run_names_what_would_be_archived_and_writes_nothing(repo, capsys, tmp_path):
    wt = repo.worktree("plans")
    (wt / "docs" / "plans").mkdir(parents=True)
    (wt / "docs" / "plans" / "p.md").write_text("x\n")
    arch = tmp_path / "arch"
    assert run_prune(repo, "--archive-dir", str(arch)) == 0
    line = verdict_line(capsys.readouterr().out, "plans")
    assert line.startswith("REMOVE") and "docs/plans" in line
    assert not arch.exists()
    assert wt.exists()


def test_keeps_a_worktree_whose_ignored_files_are_too_large_to_archive(repo, capsys, tmp_path, monkeypatch):
    wt = repo.worktree("big")
    (wt / "docs" / "plans").mkdir(parents=True)
    (wt / "docs" / "plans" / "p.md").write_text("x" * 100)
    monkeypatch.setattr(pw, "MAX_ARCHIVE_BYTES", 10)
    assert run_prune(repo, "--apply", "--archive-dir", str(tmp_path / "arch")) == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "big").startswith("KEEP")
    assert "too large to archive" in verdict_line(out, "big")
    assert (wt / "docs" / "plans" / "p.md").exists()


def test_the_size_limit_counts_every_ignored_file_together(repo, capsys, tmp_path, monkeypatch):
    wt = repo.worktree("many")
    (wt / "docs" / "plans").mkdir(parents=True)
    for n in ("a.md", "b.md"):
        (wt / "docs" / "plans" / n).write_text("123456")  # 6 bytes each: under 10 alone, over together
    monkeypatch.setattr(pw, "MAX_ARCHIVE_BYTES", 10)
    assert run_prune(repo, "--apply", "--archive-dir", str(tmp_path / "arch")) == 0
    assert verdict_line(capsys.readouterr().out, "many").startswith("KEEP")
    assert wt.exists()


def test_a_failed_archive_keeps_the_worktree(repo, capsys, tmp_path, monkeypatch):
    wt = repo.worktree("diskfull")
    (wt / "docs" / "plans").mkdir(parents=True)
    (wt / "docs" / "plans" / "p.md").write_text("only copy\n")

    def full(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(pw.shutil, "copy2", full)
    assert run_prune(repo, "--apply", "--archive-dir", str(tmp_path / "arch")) == 1
    assert "FAILED" in capsys.readouterr().out
    assert (wt / "docs" / "plans" / "p.md").read_text() == "only copy\n"


def test_a_reused_archive_dir_never_overwrites_an_earlier_archive(repo, capsys, tmp_path):
    arch = tmp_path / "arch"
    first = repo.worktree("feat")
    (first / "docs" / "plans").mkdir(parents=True)
    (first / "docs" / "plans" / "p.md").write_text("FIRST only copy\n")
    assert run_prune(repo, "--apply", "--archive-dir", str(arch)) == 0
    capsys.readouterr()
    assert not first.exists()

    second = repo.worktree("feat")  # recreated at the same path
    (second / "docs" / "plans").mkdir(parents=True)
    (second / "docs" / "plans" / "p.md").write_text("SECOND only copy\n")
    assert run_prune(repo, "--apply", "--archive-dir", str(arch)) == 1
    out = capsys.readouterr().out
    assert "FAILED" in out and "fresh --archive-dir" in out
    assert (archived(arch, "feat") / "docs" / "plans" / "p.md").read_text() == "FIRST only copy\n"
    assert (second / "docs" / "plans" / "p.md").read_text() == "SECOND only copy\n"


def test_the_default_archive_lives_inside_the_repos_git_dir(repo, capsys):
    wt = repo.worktree("plans")
    (wt / "docs" / "plans").mkdir(parents=True)
    (wt / "docs" / "plans" / "p.md").write_text("x\n")
    assert run_prune(repo, "--apply") == 0
    capsys.readouterr()
    found = list((repo.work / ".git" / "pruned-worktrees").glob("*/plans-*/docs/plans/p.md"))
    assert len(found) == 1


def test_two_worktrees_with_the_same_name_do_not_overwrite_each_others_archive(repo, capsys, tmp_path):
    first = repo.worktree("feat", branch="b-feat-1", where="a")
    second = repo.worktree("feat", branch="b-feat-2", where="b")
    for wt, text in ((first, "FIRST only copy\n"), (second, "SECOND only copy\n")):
        (wt / "docs" / "plans").mkdir(parents=True)
        (wt / "docs" / "plans" / "p.md").write_text(text)
    arch = tmp_path / "arch"
    assert run_prune(repo, "--apply", "--archive-dir", str(arch)) == 0
    capsys.readouterr()
    assert not first.exists() and not second.exists()
    texts = sorted(p.read_text() for p in arch.glob("feat-*/docs/plans/p.md"))
    assert texts == ["FIRST only copy\n", "SECOND only copy\n"]


def test_an_archive_dir_inside_a_worktree_is_refused_before_anything_is_removed(repo, capsys):
    wt = repo.worktree("victim")
    other = repo.worktree("other")
    assert run_prune(repo, "--apply", "--archive-dir", str(wt / "arch")) == 2
    assert "inside" in capsys.readouterr().err
    assert wt.exists() and other.exists()


def test_an_archive_dir_that_is_a_symlink_into_a_worktree_is_refused(repo, capsys, tmp_path):
    wt = repo.worktree("victim")
    link = tmp_path / "innocent-looking"
    os.symlink(wt / "arch", link)
    assert run_prune(repo, "--apply", "--archive-dir", str(link)) == 2
    assert "inside" in capsys.readouterr().err
    assert wt.exists()


def test_the_archive_dir_check_resolves_a_worktrees_recorded_path_too(repo, capsys):
    # git still lists ".../moved/x" after "moved" became a link to "moved-real",
    # so a real path inside the worktree must be compared against its real path.
    wt = repo.worktree("viasym2", where="moved")
    os.rename(repo.tmp / "moved", repo.tmp / "moved-real")
    os.symlink(repo.tmp / "moved-real", repo.tmp / "moved", target_is_directory=True)
    inside = repo.tmp / "moved-real" / "viasym2" / "arch"
    assert run_prune(repo, "--apply", "--archive-dir", str(inside)) == 2
    assert "inside" in capsys.readouterr().err
    assert wt.exists()


# --- branches ------------------------------------------------------------

def test_only_the_removed_worktrees_merged_branch_is_deleted(repo, capsys):
    wt = repo.worktree("done")
    repo.merge_into_origin_main(repo.commit(wt))
    git(repo.work, "branch", "unrelated-merged", "origin/main")
    keep = repo.worktree("wip")
    repo.commit(keep)

    assert run_prune(repo, "--apply") == 0
    capsys.readouterr()

    branches = git(repo.work, "for-each-ref", "--format=%(refname:short)", "refs/heads").stdout.split()
    assert "b-done" not in branches
    assert "unrelated-merged" in branches
    assert "b-wip" in branches
    assert "main" in branches


def test_a_linked_worktree_on_main_is_removed_but_the_branch_main_stays(repo, capsys):
    # main is trivially an ancestor of origin/main; deleting it would lose its
    # upstream configuration and break the next `git checkout main`.
    git(repo.work, "checkout", "-q", "-b", "feature")
    wt = repo.worktree("onmain", checkout="main")
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert not wt.exists()
    assert git(repo.work, "rev-parse", "--verify", "-q", "main").stdout.strip()
    assert "kept branch main" in out


def test_a_branch_that_gains_a_commit_after_the_check_is_not_deleted(repo, capsys, monkeypatch):
    wt = repo.worktree("racy")
    real = pw.remove_worktree

    def late_commit_then_remove(repo_path, w, locked):
        repo.commit(w.path)  # lands after the worktree was judged removable
        return real(repo_path, w, locked)

    monkeypatch.setattr(pw, "remove_worktree", late_commit_then_remove)
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert "kept branch b-racy" in out
    assert git(repo.work, "rev-parse", "--verify", "-q", "b-racy").stdout.strip()
    assert not wt.exists()


# --- changes between the check and the removal ---------------------------

def test_each_worktree_is_judged_again_immediately_before_removal(repo, capsys, monkeypatch):
    wt = repo.worktree("changed")
    real_judge, calls = pw.judge, []

    def judge_then_dirty(w, *a, **k):
        calls.append(w.path.name)
        if len(calls) == 2:  # the re-check made just before removing
            (w.path / "README.md").write_text("edited after the first check\n")
        return real_judge(w, *a, **k)

    monkeypatch.setattr(pw, "judge", judge_then_dirty)
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert "changed since the check" in out
    assert (wt / "README.md").read_text() == "edited after the first check\n"


def test_a_commit_that_lands_before_the_second_check_is_seen_by_it(repo, capsys, monkeypatch):
    # The second check must read HEAD again, not reuse the listing's. (The age
    # guard would otherwise hide this, so it is switched off.)
    wt = repo.worktree("landing")
    real_judge, calls = pw.judge, []

    def commit_then_judge(w, *a, **k):
        calls.append(1)
        if len(calls) == 2:
            repo.commit(w.path)
        return real_judge(w, *a, **k)

    monkeypatch.setattr(pw, "judge", commit_then_judge)
    assert run_prune(repo, "--apply", "--min-age-hours", "0") == 0
    out = capsys.readouterr().out
    assert "changed since the check" in out and "not merged" in out
    assert wt.exists()


def test_a_process_that_starts_before_the_second_check_is_seen_by_it(repo, capsys, monkeypatch):
    # The process list is read again for the second check, not reused.
    wt = repo.worktree("woken")
    listings = iter([[], [os.path.realpath(wt)]])
    monkeypatch.setattr(pw, "process_cwds", lambda: next(listings, [os.path.realpath(wt)]))
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert "changed since the check" in out and "process running inside" in out
    assert wt.exists()


def test_an_ignored_file_that_appears_before_the_second_check_is_archived_too(repo, capsys, tmp_path, monkeypatch):
    wt = repo.worktree("growing")
    (wt / "docs" / "plans").mkdir(parents=True)
    (wt / "docs" / "plans" / "first.md").write_text("first\n")
    real_judge, calls = pw.judge, []

    def add_file_then_judge(w, *a, **k):
        calls.append(1)
        if len(calls) == 2:
            (w.path / "docs" / "plans" / "late.md").write_text("late\n")
        return real_judge(w, *a, **k)

    monkeypatch.setattr(pw, "judge", add_file_then_judge)
    arch = tmp_path / "arch"
    assert run_prune(repo, "--apply", "--archive-dir", str(arch)) == 0
    capsys.readouterr()
    assert not wt.exists()
    assert (archived(arch, "growing") / "docs" / "plans" / "late.md").read_text() == "late\n"


def test_a_commit_made_while_the_archive_is_being_written_keeps_the_worktree(repo, capsys, tmp_path, monkeypatch):
    wt = repo.worktree("slowcopy", detach=True)
    (wt / "docs" / "plans").mkdir(parents=True)
    (wt / "docs" / "plans" / "p.md").write_text("x\n")
    real = pw.archive

    def archive_then_commit(w, ignored, dest):
        real(w, ignored, dest)
        repo.commit(w.path)

    monkeypatch.setattr(pw, "archive", archive_then_commit)
    assert run_prune(repo, "--apply", "--min-age-hours", "0", "--archive-dir", str(tmp_path / "arch")) == 1
    out = capsys.readouterr().out
    assert "FAILED" in out and "HEAD moved" in out
    assert wt.exists()


def test_the_base_branch_name_keeps_its_slashes(repo, capsys):
    # `main` for origin/main, but `release/1.0` for origin/release/1.0.
    git(repo.work, "push", "-q", "origin", "origin/main:refs/heads/release/1.0")
    git(repo.work, "fetch", "-q", "origin")
    wt = repo.worktree("rel", branch="release/1.0")
    assert run_prune(repo, "--apply", "--base", "origin/release/1.0") == 0
    out = capsys.readouterr().out
    assert not wt.exists()
    assert "kept branch release/1.0" in out
    assert git(repo.work, "rev-parse", "--verify", "-q", "release/1.0").stdout.strip()


@pytest.mark.parametrize("spelling", ["release/1.0", "refs/heads/release/1.0", "heads/release/1.0"])
def test_a_local_branch_used_as_the_base_is_never_deleted(repo, capsys, spelling):
    # With the base *being* a local branch, "merged into the base" is trivially
    # true of a worktree sitting on it, and deleting the branch deletes the base
    # (and, here, the only copy of its commit).
    wt = repo.worktree("onbase", branch="release/1.0")
    repo.commit(wt)
    assert run_prune(repo, "--apply", "--base", spelling) == 0
    out = capsys.readouterr()
    assert not wt.exists()
    assert "kept branch release/1.0" in out.out
    assert git(repo.work, "rev-parse", "--verify", "-q", "release/1.0").stdout.strip()


# Spelled out here, not read from the script: a test whose cases come from the
# code under test stops testing a name the moment the code drops it.
@pytest.mark.parametrize("name", ["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                                  "GIT_OBJECT_DIRECTORY"])
def test_every_location_variable_is_dropped_from_gits_environment(repo, capsys, monkeypatch, name):
    # Left in, each of these either redirects git or breaks it; either way a
    # worktree that is clean and merged would not be judged removable.
    wt = repo.worktree("untouched")
    Repo.age(wt, 48)
    monkeypatch.setenv(name, str(repo.tmp / "nowhere"))
    assert pw.run(["--repo", str(repo.work), "--apply"]) == 0
    capsys.readouterr()
    assert not wt.exists()


def test_an_interrupt_during_a_locked_removal_puts_the_lock_back(repo, monkeypatch):
    # KeyboardInterrupt is not a RuntimeError: without a finally, the worktree
    # would be left unlocked and its reason gone.
    wt = repo.worktree("interrupted")
    reason = "claude agent agent-q (pid 9)"
    git(repo.work, "worktree", "lock", "--reason", reason, str(wt))
    real_git = pw.git

    def interrupt_on_remove(r, *args, **kw):
        if args[:2] == ("worktree", "remove"):
            raise KeyboardInterrupt
        return real_git(r, *args, **kw)

    monkeypatch.setattr(pw, "git", interrupt_on_remove)
    with pytest.raises(KeyboardInterrupt):
        run_prune(repo, "--apply")
    monkeypatch.undo()
    assert wt.exists()
    assert f"locked {reason}" in git(repo.work, "worktree", "list", "--porcelain").stdout


def test_a_failure_while_checking_registration_does_not_mask_the_original_error(repo, monkeypatch):
    wt = repo.worktree("masked")
    reason = "claude agent agent-s (pid 7)"
    git(repo.work, "worktree", "lock", "--reason", reason, str(wt))
    real_git = pw.git

    def interrupt_on_remove(r, *args, **kw):
        if args[:2] == ("worktree", "remove"):
            raise KeyboardInterrupt
        return real_git(r, *args, **kw)

    def listing_fails(*a, **k):
        raise RuntimeError("could not list worktrees")

    monkeypatch.setattr(pw, "git", interrupt_on_remove)
    monkeypatch.setattr(pw, "_registered", listing_fails)
    with pytest.raises(KeyboardInterrupt):  # not RuntimeError("could not list worktrees")
        run_prune(repo, "--apply")
    monkeypatch.undo()
    assert f"locked {reason}" in git(repo.work, "worktree", "list", "--porcelain").stdout


def test_a_removal_that_deregisters_the_worktree_before_failing_says_the_lock_is_lost(repo, capsys, monkeypatch):
    # git can drop its record of a worktree and then fail to delete the files;
    # there is no longer anything to lock, and the message must say so.
    wt = repo.worktree("halfgone")
    git(repo.work, "worktree", "lock", "--reason", "claude agent agent-r (pid 5)", str(wt))
    real_git = pw.git

    def deregister_then_fail(r, *args, **kw):
        if args[:2] == ("worktree", "remove"):
            shutil.rmtree(Path(admin_dir(wt)))
            raise RuntimeError("git worktree remove: error: failed to delete")
        return real_git(r, *args, **kw)

    monkeypatch.setattr(pw, "git", deregister_then_fail)
    assert run_prune(repo, "--apply") == 1
    out = capsys.readouterr().out
    assert "FAILED" in out and "no longer lists this worktree" in out


def test_a_file_that_appears_after_the_last_check_is_not_force_removed(repo, capsys, monkeypatch):
    # Only a lock needs --force; a plain removal makes git itself refuse.
    wt = repo.worktree("latefile")
    real = pw.remove_worktree

    def drop_file_then_remove(repo_path, w, locked):
        (w.path / "late.txt").write_text("precious\n")
        return real(repo_path, w, locked)

    monkeypatch.setattr(pw, "remove_worktree", drop_file_then_remove)
    assert run_prune(repo, "--apply") == 1
    out = capsys.readouterr().out
    assert "FAILED" in out
    assert (wt / "late.txt").read_text() == "precious\n"


@pytest.mark.parametrize("error", [RuntimeError("boom"), OSError("boom")])
def test_one_failed_removal_is_reported_and_does_not_stop_the_rest(repo, capsys, monkeypatch, error):
    a = repo.worktree("a")
    b = repo.worktree("b")
    real = pw.remove_worktree

    def flaky(repo_path, wt, locked):
        if wt.path.name == "a":
            raise error
        return real(repo_path, wt, locked)

    monkeypatch.setattr(pw, "remove_worktree", flaky)
    assert run_prune(repo, "--apply") == 1
    out = capsys.readouterr()
    assert "FAILED" in out.out and "boom" in out.out
    assert a.exists()
    assert not b.exists()


# --- base ref and fetch --------------------------------------------------

@pytest.mark.parametrize("spelling", ["full-sha", "short-sha", "expression"])
def test_a_base_that_is_not_a_ref_is_refused_before_anything_is_removed(repo, capsys, spelling):
    # "Merged into a SHA" is trivially true of a branch at that SHA, and no ref
    # holds the commit once the branch is deleted.
    wt = repo.worktree("feat", branch="feat")
    sha = repo.commit(wt)
    base = {"full-sha": sha, "short-sha": sha[:7], "expression": "feat~0"}[spelling]
    assert run_prune(repo, "--apply", "--base", base) == 2
    assert "must name a branch" in capsys.readouterr().err
    assert wt.exists()
    assert git(repo.work, "rev-parse", "--verify", "-q", "refs/heads/feat").stdout.strip() == sha


@pytest.mark.parametrize("spelling", ["HEAD", "@"])
def test_head_as_the_base_means_the_main_checkouts_branch_not_each_worktrees_own(repo, capsys, spelling):
    # Resolved inside each worktree, HEAD is that worktree's own HEAD and
    # everything is "merged" into it.
    attached = repo.worktree("attached")
    repo.commit(attached)
    detached = repo.worktree("detached", detach=True)
    repo.commit(detached)
    assert run_prune(repo, "--apply", "--ignore-reflog", "--base", spelling) == 0
    out = capsys.readouterr().out
    for name in ("attached", "detached"):
        assert verdict_line(out, name).startswith("KEEP") and "not merged into" in verdict_line(out, name)
    assert attached.exists() and detached.exists()


def test_a_tag_named_like_the_branch_does_not_fool_the_late_commit_check(repo, capsys, monkeypatch):
    repo.worktree("onfeat", branch="feat")
    git(repo.work, "tag", "feat", "origin/main")  # ambiguous: the name now means a tag too
    real = pw.remove_worktree

    def late_commit_then_remove(repo_path, w, locked):
        repo.commit(w.path)
        return real(repo_path, w, locked)

    monkeypatch.setattr(pw, "remove_worktree", late_commit_then_remove)
    assert run_prune(repo, "--apply") == 0
    assert "kept branch feat" in capsys.readouterr().out
    assert git(repo.work, "rev-parse", "--verify", "-q", "refs/heads/feat").stdout.strip()


def test_a_remote_whose_name_contains_a_slash_protects_the_right_branch(repo, capsys):
    git(repo.work, "remote", "add", "a/b", str(repo.origin))
    git(repo.work, "fetch", "-q", "a/b")
    git(repo.work, "checkout", "-q", "-b", "feature")
    wt = repo.worktree("onmain", checkout="main")
    assert run_prune(repo, "--apply", "--fetch", "--base", "a/b/main") == 0
    out = capsys.readouterr().out
    assert not wt.exists()
    assert "kept branch main" in out
    assert git(repo.work, "rev-parse", "--verify", "-q", "refs/heads/main").stdout.strip()


def test_a_tag_as_the_base_is_allowed_and_a_detached_worktree_never_reports_a_kept_branch(repo, capsys):
    detached = repo.worktree("loose", detach=True)
    tagged = repo.worktree("tagged")
    sha = repo.commit(tagged)
    git(repo.work, "tag", "release-x", sha)  # the tag holds the commit once the branch is gone
    assert run_prune(repo, "--apply", "--base", "release-x") == 0
    out = capsys.readouterr().out
    assert "kept branch None" not in out
    assert not detached.exists()
    assert git(repo.work, "rev-parse", "--verify", "-q", "refs/heads/b-tagged", check=False).returncode != 0
    assert git(repo.work, "rev-parse", "refs/tags/release-x").stdout.strip() == sha


def test_a_reflog_git_cannot_read_keeps_the_worktree(repo, capsys):
    # Not being able to read the reflog is not the same as it being empty.
    wt = repo.worktree("garbled")
    log = Path(admin_dir(wt)) / "logs" / "HEAD"
    log.write_text("not a reflog entry\n")
    assert run_prune(repo, "--apply") == 0
    assert verdict_line(capsys.readouterr().out, "garbled").startswith("KEEP")
    assert wt.exists()


def test_a_missing_base_ref_is_an_error_and_changes_nothing(repo, capsys):
    wt = repo.worktree("done")
    assert run_prune(repo, "--apply", "--base", "origin/nope") == 2
    err = capsys.readouterr().err
    assert "origin/nope" in err
    assert wt.exists()


def test_without_fetch_a_stale_origin_main_is_the_conservative_answer(repo, capsys):
    # origin/main on the server has moved on and contains the branch; the
    # local remote-tracking ref has not heard. Judging against the stale ref
    # keeps the worktree; --fetch refreshes it and then removes it.
    wt = repo.worktree("late")
    sha = repo.commit(wt)
    git(repo.work, "push", "-q", "origin", f"{sha}:refs/heads/tmp")
    git(repo.origin, "update-ref", "refs/heads/main", sha)

    assert run_prune(repo, "--apply") == 0
    assert verdict_line(capsys.readouterr().out, "late").startswith("KEEP")
    assert wt.exists()

    assert run_prune(repo, "--apply", "--fetch") == 0
    capsys.readouterr()
    assert not wt.exists()


def test_a_failed_fetch_is_an_error_and_changes_nothing(repo, capsys):
    wt = repo.worktree("done")
    git(repo.work, "remote", "set-url", "origin", str(repo.tmp / "no-such-remote.git"))
    assert run_prune(repo, "--apply", "--fetch") == 2
    assert "could not fetch" in capsys.readouterr().err
    assert wt.exists()


def test_fetch_needs_a_base_that_names_a_configured_remote(repo, capsys):
    wt = repo.worktree("done")
    assert run_prune(repo, "--apply", "--fetch", "--base", "main") == 2
    assert "not under a configured remote" in capsys.readouterr().err
    assert wt.exists()


def test_not_a_git_repository_is_an_error(tmp_path, capsys):
    assert pw.run(["--repo", str(tmp_path)]) == 2
    assert "not a git repository" in capsys.readouterr().err

"""Tests for scripts/prune_worktrees.py — removes linked git worktrees that are
provably safe to remove (GH #668).

Run from the repo root:

    python3 -m pytest -q scripts/test_prune_worktrees.py

Every test drives a real throwaway repository (a bare "origin", a clone, and
real `git worktree add` checkouts), because the script's whole job is to be
right about what git says. Mirrors scripts/test_content_language.py: the
script is loaded by path under a private module name.

The cases are the ones the 2026-10-23 manual cleanup (44 of 45 worktrees) had
to handle by hand: locked worktrees, a local `main` behind `origin/main`,
ignored files that exist nowhere else, and branches that only look merged.
"""
import importlib.util
import os
import shutil
import subprocess
import time

import pytest

_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "prune_worktrees.py")
_spec = importlib.util.spec_from_file_location("_prune_worktrees", _SCRIPT)
pw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pw)

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


class Repo:
    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.ages = {}
        self.origin = tmp_path / "origin.git"
        self.work = tmp_path / "work"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.work)],
                       check=True, capture_output=True)
        (self.work / ".gitignore").write_text("node_modules/\ndocs/plans/\n")
        (self.work / "README.md").write_text("base\n")
        git(self.work, "add", "-A")
        git(self.work, "commit", "-q", "-m", "base")
        git(self.work, "push", "-q", "-u", "origin", "main")

    def worktree(self, name, branch=None, detach=False, age_hours=48):
        path = self.tmp / "wts" / name
        if detach:
            git(self.work, "worktree", "add", "-q", "--detach", str(path), "origin/main")
        else:
            git(self.work, "worktree", "add", "-q", "-b", branch or f"b-{name}",
                str(path), "origin/main")
        self.ages[path] = age_hours
        return path

    @staticmethod
    def age(path, hours):
        """Make the worktree look untouched for `hours` hours."""
        admin = git(path, "rev-parse", "--absolute-git-dir").stdout.strip()
        t = time.time() - hours * 3600
        for f in ("index", "HEAD"):
            p = os.path.join(admin, f)
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


# --- what must never be removed -----------------------------------------

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


def test_a_dry_run_does_not_make_a_worktree_look_recently_touched(repo, capsys):
    # `git status` may rewrite a stale index, which would refresh the very mtime
    # the age guard reads and make every later run refuse for 24 hours.
    wt = repo.worktree("quiet")
    os.utime(wt / "README.md", None)  # stat-dirty, content unchanged
    Repo.age(wt, 48)
    admin = git(wt, "rev-parse", "--absolute-git-dir").stdout.strip()
    before = os.path.getmtime(os.path.join(admin, "index"))
    pw.run(["--repo", str(repo.work)])
    capsys.readouterr()
    assert os.path.getmtime(os.path.join(admin, "index")) == before


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


@pytest.mark.skipif(shutil.which("lsof") is None, reason="needs lsof")
def test_a_real_process_inside_a_worktree_keeps_it(repo, capsys, monkeypatch):
    monkeypatch.undo()  # restore the real process_cwds
    for k, v in _GIT_ENV.items():
        monkeypatch.setenv(k, v)
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

def test_removes_a_stale_locked_worktree_and_reports_the_lock(repo, capsys):
    wt = repo.worktree("locked")
    git(repo.work, "worktree", "lock", "--reason", "claude agent x (pid 1)", str(wt))
    assert run_prune(repo) == 0
    line = verdict_line(capsys.readouterr().out, "locked")
    assert line.startswith("REMOVE")
    assert "locked: claude agent x (pid 1)" in line

    assert run_prune(repo, "--apply") == 0
    capsys.readouterr()
    assert not wt.exists()


def test_a_lock_does_not_override_the_other_checks(repo, capsys):
    wt = repo.worktree("locked-wip")
    repo.commit(wt)
    git(repo.work, "worktree", "lock", str(wt))
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "locked-wip").startswith("KEEP")
    assert wt.exists()


# --- ignored files -------------------------------------------------------

def test_archives_ignored_files_that_exist_nowhere_else_before_removing(repo, capsys, tmp_path):
    wt = repo.worktree("plans")
    (wt / "docs" / "plans").mkdir(parents=True)
    (wt / "docs" / "plans" / "p.md").write_text("the only copy\n")
    (wt / "node_modules" / "pkg").mkdir(parents=True)
    (wt / "node_modules" / "pkg" / "index.js").write_text("regenerable\n")
    arch = tmp_path / "arch"

    assert run_prune(repo, "--apply", "--archive-dir", str(arch)) == 0
    out = capsys.readouterr().out

    assert not wt.exists()
    assert (arch / "plans" / "docs" / "plans" / "p.md").read_text() == "the only copy\n"
    assert not (arch / "plans" / "node_modules").exists()
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
    assert (arch / "nested" / "docs" / "plans" / "keep.md").read_text() == "only copy\n"
    assert not (arch / "nested" / "docs" / "plans" / "node_modules").exists()


def test_a_symlink_in_an_ignored_directory_is_archived_as_a_link(repo, capsys, tmp_path):
    wt = repo.worktree("linked")
    (wt / "docs" / "plans").mkdir(parents=True)
    os.symlink("/nonexistent/target", wt / "docs" / "plans" / "dangling")
    arch = tmp_path / "arch"
    assert run_prune(repo, "--apply", "--archive-dir", str(arch)) == 0
    capsys.readouterr()
    assert os.readlink(arch / "linked" / "docs" / "plans" / "dangling") == "/nonexistent/target"


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


def test_the_default_archive_lives_inside_the_repos_git_dir(repo, capsys):
    wt = repo.worktree("plans")
    (wt / "docs" / "plans").mkdir(parents=True)
    (wt / "docs" / "plans" / "p.md").write_text("x\n")
    assert run_prune(repo, "--apply") == 0
    capsys.readouterr()
    found = list((repo.work / ".git" / "pruned-worktrees").glob("*/plans/docs/plans/p.md"))
    assert len(found) == 1


# --- detached HEAD, branches, base ---------------------------------------

def test_removes_a_merged_detached_worktree(repo, capsys):
    wt = repo.worktree("detached", detach=True)
    assert run_prune(repo, "--apply") == 0
    capsys.readouterr()
    assert not wt.exists()


def test_a_detached_worktree_with_unpushed_commits_is_kept(repo, capsys):
    wt = repo.worktree("detached-wip", detach=True)
    repo.commit(wt)
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert verdict_line(out, "detached-wip").startswith("KEEP")
    assert wt.exists()


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


def test_a_branch_that_gains_a_commit_after_the_check_is_not_deleted(repo, capsys, monkeypatch):
    wt = repo.worktree("racy")
    real = pw.remove_worktree

    def late_commit_then_remove(repo_path, w, force_lock):
        repo.commit(w.path)  # lands after the worktree was judged removable
        return real(repo_path, w, force_lock)

    monkeypatch.setattr(pw, "remove_worktree", late_commit_then_remove)
    assert run_prune(repo, "--apply") == 0
    out = capsys.readouterr().out
    assert "kept branch b-racy" in out
    assert git(repo.work, "rev-parse", "--verify", "-q", "b-racy").stdout.strip()
    assert not wt.exists()


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


# --- failure handling ----------------------------------------------------

def test_one_failed_removal_is_reported_and_does_not_stop_the_rest(repo, capsys, monkeypatch):
    a = repo.worktree("a")
    b = repo.worktree("b")
    real = pw.remove_worktree

    def flaky(repo_path, wt, force_lock):
        if wt.path.name == "a":
            raise RuntimeError("boom")
        return real(repo_path, wt, force_lock)

    monkeypatch.setattr(pw, "remove_worktree", flaky)
    assert run_prune(repo, "--apply") == 1
    out = capsys.readouterr()
    assert "FAILED" in out.out and "boom" in out.out
    assert a.exists()
    assert not b.exists()


def test_not_a_git_repository_is_an_error(tmp_path, capsys):
    assert pw.run(["--repo", str(tmp_path)]) == 2
    assert "not a git repository" in capsys.readouterr().err

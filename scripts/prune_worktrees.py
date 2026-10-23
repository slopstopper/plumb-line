#!/usr/bin/env python3
"""Remove linked git worktrees that are provably safe to remove (GH #668).

    python3 scripts/prune_worktrees.py             # dry run: say what would go
    python3 scripts/prune_worktrees.py --apply     # do it

Stale worktrees pile up under .claude/worktrees/ because nothing goes back to
tidy them, and a stale lock (left by the agent that made the worktree) makes a
plain `git worktree remove` refuse. This removes a worktree only when every
check below passes, and otherwise says which one failed:

  * not the main checkout, and not the worktree this command is run from
  * its directory exists (otherwise: `git worktree prune`), and git resolves it
    to that directory (a stray GIT_DIR or core.worktree would make every other
    check read a different repository)
  * no process has its working directory inside it (`lsof`; if that check
    cannot run, nothing is removed, because not knowing is not the same as free)
  * not touched within --min-age-hours (a just-created worktree at origin/main
    looks exactly like a finished one)
  * clean: no tracked changes, no untracked files, no edit hidden from
    `git status` by skip-worktree or assume-unchanged, no submodule (its git
    dir lives inside the worktree's own), no rebase/merge/cherry-pick/bisect
    in progress. `git status` is asked with the user's config overridden
  * HEAD is an ancestor of the base ref (default origin/main): every commit is
    already on the base. A squash-merged branch is NOT an ancestor, so it is
    kept and named, never guessed at
  * no commit is held only by the worktree itself: per-worktree refs
    (refs/worktree, refs/bisect), and for a detached HEAD its reflog, must not
    reach commits that no branch, remote or tag reaches
  * ignored files a rebuild would not recreate are archived first (one
    directory per worktree; an existing archive file is never overwritten); if
    they are too large, or cannot be copied, the worktree is kept
  * a lock is cleared only if the agent that made it wrote it ("claude agent
    ..."); any other lock is a person's and needs --break-locks

Each worktree is judged again immediately before it is removed, from fresh
reads of HEAD and of the processes, and HEAD is read once more after the
archive. It is then removed without --force, so git itself refuses anything that
appeared since. A locked worktree is unlocked first for that, and locked again
if git refuses. The merged local branch of a removed worktree is deleted too,
unless it is the base's own branch name (`main` for origin/main) or has gained
commits. Nothing is fetched unless --fetch is given; a stale origin/main only
ever makes the answer more conservative.

Limits: `lsof -d cwd` sees only processes whose working directory is inside the
worktree, and only those lsof is allowed to see. An editor with the folder open
but a different working directory is not detected. A commit made after the
final HEAD read, in the instant before git removes a detached worktree, is not
detected (a branch keeps it; see above). Commits a branch worktree abandoned by
amend or reset, held only by its HEAD reflog, are not protected. A sparse
checkout always reads as having hidden edits, so it is always kept. Pure
stdlib; needs git >= 2.17 (`worktree remove`).

Exit status: 0 done (a dry run, or every removal worked); 1 an --apply removal
failed; 2 cannot run (not a repository, base ref missing, fetch failed,
archive dir inside a worktree).
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Ignored directories a fresh checkout or install rebuilds. Only names that are
# always a cache: `build`, `dist` and `coverage` are sometimes real output, so
# they are archived (or the worktree is kept if that is too large), and a file
# is never skipped by its name.
REGENERABLE = {
    "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache",
    ".mypy_cache", ".import_linter_cache", ".vitest", ".tox",
}
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
LISTED = 3  # names shown in a reason before "..."
AGENT_LOCK = "claude agent "  # how Claude Code words the lock it puts on its worktrees
IN_PROGRESS = ("rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD",
               "REVERT_HEAD", "BISECT_LOG", "sequencer")
PER_WORKTREE_REFS = ("refs/worktree", "refs/bisect", "refs/rewritten")
# Variables that point git at a repository; a hook or wrapper that exports one
# would make every call below read that repository instead of the worktree.
_LOCATION_ENV = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
                 "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_PREFIX", "GIT_IMPLICIT_WORK_TREE"}


@dataclass
class Worktree:
    path: Path
    head: str
    branch: str | None  # None when detached
    locked: str | None  # None unlocked; "" locked without a reason


def _git_env():
    # No optional locks: `git status` must not rewrite a stale index, or the
    # mtime the age check reads would move every time this script looks.
    env = {k: v for k, v in os.environ.items() if k not in _LOCATION_ENV}
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def git(repo, *args, check=True):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=_git_env())
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip() or p.stdout.strip()}")
    return p


def list_worktrees(repo):
    """Every worktree, main checkout first, from `git worktree list --porcelain`."""
    out = git(repo, "worktree", "list", "--porcelain").stdout
    found = []
    for block in out.strip().split("\n\n"):
        fields = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        if "worktree" not in fields:
            continue
        branch = fields.get("branch")
        found.append(Worktree(
            path=Path(fields["worktree"]),
            head=fields.get("HEAD", ""),
            branch=branch.removeprefix("refs/heads/") if branch else None,
            locked=fields.get("locked") if "locked" in fields else None,
        ))
    return found


def process_cwds():
    """Working directories of the processes `lsof` can see, or None when that
    cannot be established. Our own cwd must be in the answer; if it is not, the
    listing is not trustworthy."""
    try:
        p = subprocess.run(["lsof", "-a", "-d", "cwd", "-Fn"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode > 1:  # 1 is lsof's "some files were not listable"
        return None
    cwds = [os.path.realpath(ln[1:]) for ln in p.stdout.splitlines() if ln.startswith("n/")]
    return cwds if os.path.realpath(os.getcwd()) in cwds else None


def _now():
    return time.time()


def _inside(path, root):
    return path == root or path.startswith(root + os.sep)


def _listed(names):
    names = list(names)
    shown = ", ".join(names[:LISTED])
    return shown + (", ..." if len(names) > LISTED else "")


def _admin(wt):
    return git(wt, "rev-parse", "--absolute-git-dir").stdout.strip()


def _head(wt):
    return git(wt, "rev-parse", "HEAD").stdout.strip()


def _touched_age_hours(admin):
    mtimes = [os.path.getmtime(os.path.join(admin, f)) for f in ("index", "HEAD")
              if os.path.exists(os.path.join(admin, f))]
    return (_now() - max(mtimes)) / 3600 if mtimes else float("inf")


def _regenerable(name):
    return name in REGENERABLE or name.endswith(".egg-info")


def _raise(error):
    raise error


def archivable_ignored(wt):
    """Relative paths of the ignored files a rebuild would not recreate.

    `ls-files --directory` collapses directories but also lists a wholly-ignored
    directory and its children separately, so the directories are walked here
    (pruning the regenerable ones) and the files de-duplicated. A directory that
    cannot be read raises: its files would be deleted unarchived."""
    out = git(wt, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z").stdout
    files = set()
    for rel in filter(None, out.split("\0")):
        parts = rel.rstrip("/").split("/")
        is_dir = rel.endswith("/")
        if any(_regenerable(p) for p in (parts if is_dir else parts[:-1])):
            continue
        if not is_dir:
            files.add(rel)
            continue
        for d, dirs, names in os.walk(Path(wt) / rel, onerror=_raise):
            # os.walk lists a symlink to a directory in `dirs` but never descends
            # into it, so it has to be archived as the link it is.
            names += [x for x in dirs if os.path.islink(os.path.join(d, x)) and not _regenerable(x)]
            dirs[:] = [x for x in dirs if not _regenerable(x)]
            files.update(os.path.relpath(os.path.join(d, n), wt) for n in names)
    return sorted(files)


def _groups(files):
    """Short names for a file list: the first two path components."""
    return dict.fromkeys("/".join(f.split("/")[:2]) for f in files)


def _not_clean(wt, admin):
    """Reasons the worktree is not provably clean."""
    why = []
    # The explicit flag beats the user's config (status.showUntrackedFiles=no
    # would otherwise hide untracked files).
    status = git(wt, "status", "--porcelain", "--untracked-files=all").stdout.splitlines()
    if any(not ln.startswith("??") for ln in status):
        why.append("tracked changes")
    untracked = [ln[3:] for ln in status if ln.startswith("??")]
    if untracked:
        why.append(f"untracked files ({_listed(untracked)})")
    # skip-worktree (sparse checkout) is tagged `S`; assume-unchanged is lowercase.
    hidden = [ln[2:] for ln in git(wt, "ls-files", "-v").stdout.splitlines() if ln[0] == "S" or ln[0].islower()]
    if hidden:
        why.append(f"edits hidden from status (skip-worktree or assume-unchanged: {_listed(hidden)})")
    if os.path.isdir(os.path.join(admin, "modules")):
        why.append("has submodules (their git dirs live inside this worktree's)")
    pending = [m for m in IN_PROGRESS if os.path.exists(os.path.join(admin, m))]
    if pending:
        why.append(f"operation in progress ({', '.join(pending)})")
    return why


def _held_only_here(wt, detached):
    """How many commits only this worktree's own state keeps alive: removing
    the worktree deletes its per-worktree refs and its reflog."""
    tips = git(wt, "for-each-ref", "--format=%(objectname)", *PER_WORKTREE_REFS).stdout.split()
    if detached:  # on a branch, the branch holds what the reflog would
        tips += git(wt, "reflog", "show", "--format=%H", "HEAD", check=False).stdout.split()
    if not tips:
        return 0
    return int(git(wt, "rev-list", "--count", *tips, "--not", "--branches", "--remotes", "--tags").stdout)


def judge(wt, base, *, cwd, cwds, min_age_hours, break_locks):
    """(reasons to keep, ignored files to archive, HEAD that was judged). No
    reasons = removable. Everything is read fresh from git here, never taken
    from the worktree listing."""
    if not wt.path.is_dir():
        return ["directory missing (run `git worktree prune`)"], [], None
    root = os.path.realpath(wt.path)
    top = git(wt.path, "rev-parse", "--show-toplevel").stdout.strip()
    if os.path.realpath(top) != root:
        raise RuntimeError(f"git resolves this worktree to {top}")
    admin, head = _admin(wt.path), _head(wt.path)
    why = []
    if _inside(cwd, root):
        why.append("current worktree")
    if cwds is None:
        why.append("process check unavailable (lsof)")
    elif any(_inside(c, root) for c in cwds):
        why.append("process running inside")
    if _touched_age_hours(admin) < min_age_hours:
        why.append(f"touched within {min_age_hours:g}h")
    if wt.locked is not None and not wt.locked.startswith(AGENT_LOCK) and not break_locks:
        why.append(f"locked: {wt.locked or '(no reason)'} (pass --break-locks to remove anyway)")
    why += _not_clean(wt.path, admin)
    if git(wt.path, "merge-base", "--is-ancestor", head, base, check=False).returncode != 0:
        ahead = git(wt.path, "rev-list", "--count", f"{base}..{head}").stdout.strip()
        why.append(f"not merged into {base} ({ahead} commit(s) not on it)")
    held = _held_only_here(wt.path, detached=wt.branch is None)
    if held:
        why.append(f"{held} commit(s) held only by this worktree (its reflog or per-worktree refs)")
    if why:
        return why, [], head
    ignored = archivable_ignored(wt.path)
    if sum(os.lstat(wt.path / p).st_size for p in ignored) > MAX_ARCHIVE_BYTES:
        return [f"ignored files too large to archive ({_listed(_groups(ignored))})"], [], head
    return [], ignored, head


def archive_path(dest, wt):
    """One directory per worktree: two worktrees may share a name."""
    tag = hashlib.sha1(os.path.realpath(wt.path).encode()).hexdigest()[:8]
    return Path(dest) / f"{wt.path.name}-{tag}"


def archive(wt, ignored, dest):
    here = archive_path(dest, wt)
    clash = [r for r in ignored if os.path.lexists(here / r)]
    if clash:
        raise RuntimeError(f"the archive already holds {_listed(clash)}; pass a fresh --archive-dir")
    for rel in ignored:
        dst = here / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wt.path / rel, dst, follow_symlinks=False)


def remove_worktree(repo, wt, locked):
    # Never --force: git refuses modified or untracked files itself, which is
    # the last line of defence against a change that arrived after the check.
    # A lock is the one thing that would otherwise need force, so it is lifted
    # for the removal and put back if git refuses.
    if not locked:
        git(repo, "worktree", "remove", str(wt.path))
        return
    git(repo, "worktree", "unlock", str(wt.path))
    try:
        git(repo, "worktree", "remove", str(wt.path))
    except RuntimeError:
        git(repo, "worktree", "lock", *(["--reason", wt.locked] if wt.locked else []), str(wt.path), check=False)
        raise


def run(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="remove (default: dry run)")
    ap.add_argument("--base", default="origin/main", help="ref a worktree's HEAD must already be on")
    ap.add_argument("--fetch", action="store_true", help="fetch the base ref's remote first")
    ap.add_argument("--min-age-hours", type=float, default=24.0)
    ap.add_argument("--break-locks", action="store_true", help="also remove worktrees locked by a person")
    ap.add_argument("--archive-dir", help="default: <git dir>/pruned-worktrees/<UTC timestamp>-<pid>")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args(argv)

    probe = git(args.repo, "rev-parse", "--git-common-dir", check=False)
    if probe.returncode != 0:
        print(f"prune_worktrees: not a git repository: {args.repo}", file=sys.stderr)
        return 2
    common = Path(args.repo, probe.stdout.strip()).resolve()
    everything = list_worktrees(args.repo)
    repo, linked = everything[0].path, everything[1:]

    if args.fetch:
        remote = args.base.split("/")[0]
        if remote not in git(repo, "remote").stdout.split():
            print(f"prune_worktrees: --fetch needs a base like <remote>/<branch>; {remote!r} is not a configured remote",
                  file=sys.stderr)
            return 2
        if git(repo, "fetch", "--quiet", remote, check=False).returncode != 0:
            print(f"prune_worktrees: could not fetch {remote!r}", file=sys.stderr)
            return 2
    if git(repo, "rev-parse", "--verify", "-q", f"{args.base}^{{commit}}", check=False).returncode != 0:
        print(f"prune_worktrees: base ref {args.base!r} not found (fetch it, or pass --base)", file=sys.stderr)
        return 2
    if git(repo, "show-ref", "--verify", "-q", f"refs/remotes/{args.base}", check=False).returncode != 0:
        print(f"prune_worktrees: note: {args.base!r} is not a remote-tracking ref; "
              "a branch merged only locally counts as merged", file=sys.stderr)
    base_sha = git(repo, "rev-parse", "--short", args.base).stdout.strip()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = Path(args.archive_dir) if args.archive_dir else common / "pruned-worktrees" / f"{stamp}-{os.getpid()}"
    real_dest = os.path.realpath(dest)
    for wt in linked:
        if _inside(real_dest, os.path.realpath(wt.path)):
            print(f"prune_worktrees: the archive dir {str(dest)!r} is inside worktree {wt.path.name!r}, "
                  "which would delete it", file=sys.stderr)
            return 2

    cwd = os.path.realpath(os.getcwd())
    opts = dict(cwd=cwd, min_age_hours=args.min_age_hours, break_locks=args.break_locks)
    protected = args.base.split("/", 1)[-1]  # the base's own branch name: main for origin/main

    def inspect(wt, cwds):
        try:
            return judge(wt, args.base, cwds=cwds, **opts)
        except (RuntimeError, OSError) as e:
            return [f"could not inspect: {e}"], [], None

    cwds = process_cwds()
    verdicts = [(wt, *inspect(wt, cwds)) for wt in linked]

    failed = removed = 0
    for wt, why, ignored, _ in verdicts:
        label = wt.branch or "(detached)"
        if why:
            print(f"KEEP    {wt.path.name} {label}  {'; '.join(why)}")
            continue
        notes = [f"merged into {args.base}, clean"]
        if wt.locked is not None:
            notes.append(f"locked: {wt.locked}" if wt.locked else "locked")
        if ignored:
            notes.append(f"archives {_listed(_groups(ignored))} to {archive_path(dest, wt)}")
        print(f"REMOVE  {wt.path.name} {label}  {'; '.join(notes)}")
        if not args.apply:
            continue
        try:
            # Judged again, from fresh reads of HEAD and of the processes: this
            # is the last look before deleting.
            why, ignored, head = inspect(wt, process_cwds())
            if why:
                print(f"        kept: changed since the check: {'; '.join(why)}")
                continue
            if ignored:
                archive(wt, ignored, dest)
                if _head(wt.path) != head:
                    raise RuntimeError("HEAD moved while the archive was being written")
            remove_worktree(repo, wt, locked=wt.locked is not None)
            if wt.branch == protected:
                print(f"        kept branch {wt.branch}: it is the base's own branch")
            elif wt.branch:
                # Re-checked, not assumed: a commit may have landed in the
                # worktree after it was judged, and -D would orphan it.
                if git(repo, "merge-base", "--is-ancestor", wt.branch, args.base, check=False).returncode == 0:
                    git(repo, "branch", "-D", wt.branch)
                else:
                    print(f"        kept branch {wt.branch}: it gained commits not on {args.base} after the check")
            removed += 1
        except (RuntimeError, OSError) as e:
            failed += 1
            print(f"FAILED  {wt.path.name}  {e}")

    to_remove = sum(1 for _, why, _, _ in verdicts if not why)
    print(f"\n{to_remove} removable, {len(verdicts) - to_remove} kept (base {args.base} @ {base_sha})")
    if args.apply:
        print(f"removed {removed}" + (f", {failed} FAILED" if failed else ""))
    else:
        print("dry run: nothing changed; re-run with --apply to remove them")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))

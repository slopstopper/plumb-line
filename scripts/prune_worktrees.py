#!/usr/bin/env python3
"""Remove linked git worktrees that are provably safe to remove (GH #668).

    python3 scripts/prune_worktrees.py             # dry run: say what would go
    python3 scripts/prune_worktrees.py --apply     # do it

Stale worktrees pile up under .claude/worktrees/ because nothing goes back to
tidy them, and a stale lock (left by the agent that made the worktree) makes a
plain `git worktree remove` refuse. This removes a worktree only when every
check below passes, and otherwise says which one failed:

  * not the main checkout, and not the worktree this command is run from
  * its directory exists (otherwise: `git worktree prune`)
  * no process has its working directory inside it (`lsof`; if that check
    cannot run, nothing is removed, because not knowing is not the same as free)
  * not touched within --min-age-hours (a just-created worktree at origin/main
    looks exactly like a finished one)
  * no tracked changes and no untracked files
  * HEAD is an ancestor of the base ref (default origin/main): every commit is
    already on the base. A squash-merged branch is NOT an ancestor, so it is
    kept and named, never guessed at
  * ignored files that may exist nowhere else are archived first; if they
    cannot be (too large), the worktree is kept

A lock is cleared only after all of that. The merged local branch of a removed
worktree is deleted too. Nothing is pushed or fetched unless --fetch is given;
a stale origin/main only ever makes the answer more conservative.

Limits: `lsof` shows only the processes it is allowed to see (other users'
processes need privileges). Pure stdlib.

Exit status: 0 done (a dry run, or every removal worked); 1 an --apply removal
failed; 2 cannot run (not a repository, base ref missing, fetch failed).
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Ignored paths a fresh checkout/install rebuilds; everything else ignored is
# archived before removal (plans, specs, settings.local.json, ...).
REGENERABLE = {
    "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache",
    ".mypy_cache", ".import_linter_cache", ".vitest", ".tox", "coverage", "dist", "build",
}
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
LISTED = 3  # names shown in a reason before "..."


@dataclass
class Worktree:
    path: Path
    head: str
    branch: str | None  # None when detached
    locked: str | None  # None unlocked; "" locked without a reason
    prunable: bool


def git(repo, *args, check=True):
    # No optional locks: `git status` must not rewrite a stale index, or the
    # mtime the age check reads would move every time this script looks.
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=env)
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
            prunable="prunable" in fields,
        ))
    return found


def process_cwds():
    """Working directories of the processes `lsof` can see, or None when that
    cannot be established. Our own cwd must be in the answer; if it is not, the
    listing is not trustworthy."""
    if shutil.which("lsof") is None:
        return None
    try:
        p = subprocess.run(["lsof", "-a", "-d", "cwd", "-Fn"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode > 1:
        return None
    cwds = [os.path.realpath(ln[1:]) for ln in p.stdout.splitlines() if ln.startswith("n/")]
    return cwds if os.path.realpath(os.getcwd()) in cwds else None


def _inside(path, root):
    return path == root or path.startswith(root + os.sep)


def _listed(names):
    names = list(names)
    shown = ", ".join(names[:LISTED])
    return shown + (", ..." if len(names) > LISTED else "")


def _touched_age_hours(wt):
    admin = git(wt, "rev-parse", "--absolute-git-dir").stdout.strip()
    mtimes = [os.path.getmtime(os.path.join(admin, f)) for f in ("index", "HEAD")
              if os.path.exists(os.path.join(admin, f))]
    return (time.time() - max(mtimes)) / 3600 if mtimes else float("inf")


def _regenerable(name):
    return name in REGENERABLE or name.endswith(".egg-info")


def archivable_ignored(wt):
    """Relative paths of the ignored files a rebuild would not bring back.

    `ls-files --directory` collapses directories but also lists a wholly-ignored
    directory and its children separately, so the directories are walked here
    (pruning the regenerable ones) and the files de-duplicated."""
    out = git(wt, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z").stdout
    files = set()
    for rel in filter(None, out.split("\0")):
        if any(_regenerable(p) for p in rel.rstrip("/").split("/")):
            continue
        top = Path(wt) / rel
        if not rel.endswith("/"):
            files.add(rel)
            continue
        for d, dirs, names in os.walk(top):
            # A symlink to a directory is listed in `dirs` but not descended into.
            names += [x for x in dirs if os.path.islink(os.path.join(d, x))]
            dirs[:] = [x for x in dirs if not _regenerable(x) and not os.path.islink(os.path.join(d, x))]
            files.update(os.path.relpath(os.path.join(d, n), wt) for n in names if not _regenerable(n))
    return sorted(files)


def _groups(files):
    """Short names for a file list: the first two path components."""
    return dict.fromkeys("/".join(f.split("/")[:2]) for f in files)


def judge(wt, base, *, cwd, cwds, min_age_hours):
    """(reasons to keep, ignored paths to archive). No reasons = removable."""
    if wt.prunable or not wt.path.is_dir():
        return ["directory missing (run `git worktree prune`)"], []
    root = os.path.realpath(wt.path)
    why = []
    if _inside(cwd, root):
        why.append("current worktree")
    if cwds is None:
        why.append("process check unavailable (lsof)")
    elif any(_inside(c, root) for c in cwds):
        why.append("process running inside")
    age = _touched_age_hours(wt.path)
    if age < min_age_hours:
        why.append(f"touched within {min_age_hours:g}h")
    if git(wt.path, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        why.append("tracked changes")
    untracked = [ln[3:] for ln in git(wt.path, "status", "--porcelain").stdout.splitlines() if ln.startswith("??")]
    if untracked:
        why.append(f"untracked files ({_listed(untracked)})")
    if git(wt.path, "merge-base", "--is-ancestor", wt.head, base, check=False).returncode != 0:
        ahead = git(wt.path, "rev-list", "--count", f"{base}..{wt.head}").stdout.strip()
        why.append(f"not merged into {base} ({ahead} commit(s) not on it)")
    if why:
        return why, []
    ignored = archivable_ignored(wt.path)
    if sum(os.lstat(wt.path / p).st_size for p in ignored) > MAX_ARCHIVE_BYTES:
        return [f"ignored files too large to archive ({_listed(_groups(ignored))})"], []
    return [], ignored


def archive(wt, ignored, dest):
    for rel in ignored:
        src, dst = wt.path / rel, dest / wt.path.name / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst, follow_symlinks=False)


def remove_worktree(repo, wt, force_lock):
    flags = ["--force", "--force"] if force_lock else ["--force"]
    git(repo, "worktree", "remove", *flags, str(wt.path))


def run(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="remove (default: dry run)")
    ap.add_argument("--base", default="origin/main", help="ref a worktree's HEAD must already be on")
    ap.add_argument("--fetch", action="store_true", help="fetch the base ref's remote first")
    ap.add_argument("--min-age-hours", type=float, default=24.0)
    ap.add_argument("--archive-dir", help="default: <git dir>/pruned-worktrees/<UTC timestamp>")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args(argv)

    probe = git(args.repo, "rev-parse", "--git-common-dir", check=False)
    if probe.returncode != 0:
        print(f"prune_worktrees: not a git repository: {args.repo}", file=sys.stderr)
        return 2
    common = Path(args.repo, probe.stdout.strip()).resolve()
    repo = list_worktrees(args.repo)[0].path

    if args.fetch:
        remote = args.base.split("/")[0]
        if git(repo, "fetch", "--quiet", remote, check=False).returncode != 0:
            print(f"prune_worktrees: could not fetch {remote!r}", file=sys.stderr)
            return 2
    if git(repo, "rev-parse", "--verify", "-q", f"{args.base}^{{commit}}", check=False).returncode != 0:
        print(f"prune_worktrees: base ref {args.base!r} not found (fetch it, or pass --base)", file=sys.stderr)
        return 2
    base_sha = git(repo, "rev-parse", "--short", args.base).stdout.strip()

    cwd = os.path.realpath(os.getcwd())
    cwds = process_cwds()
    dest = Path(args.archive_dir) if args.archive_dir else \
        common / "pruned-worktrees" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    verdicts = []
    for wt in list_worktrees(repo)[1:]:
        why, ignored = judge(wt, args.base, cwd=cwd, cwds=cwds, min_age_hours=args.min_age_hours)
        verdicts.append((wt, why, ignored))

    failed = removed = 0
    for wt, why, ignored in verdicts:
        label = wt.branch or "(detached)"
        if why:
            print(f"KEEP    {wt.path.name} {label}  {'; '.join(why)}")
            continue
        notes = [f"merged into {args.base}, clean"]
        if wt.locked is not None:
            notes.append(f"locked: {wt.locked}" if wt.locked else "locked")
        if ignored:
            notes.append(f"archives {_listed(_groups(ignored))} to {dest}")
        print(f"REMOVE  {wt.path.name} {label}  {'; '.join(notes)}")
        if not args.apply:
            continue
        try:
            if ignored:
                archive(wt, ignored, dest)
            remove_worktree(repo, wt, force_lock=wt.locked is not None)
            if wt.branch:
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

    to_remove = sum(1 for _, why, _ in verdicts if not why)
    print(f"\n{to_remove} removable, {len(verdicts) - to_remove} kept (base {args.base} @ {base_sha})")
    if args.apply:
        print(f"removed {removed}" + (f", {failed} FAILED" if failed else ""))
    else:
        print("dry run: nothing changed; re-run with --apply to remove them")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))

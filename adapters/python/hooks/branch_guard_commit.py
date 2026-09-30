"""branch_guard_commit — run the branch guard as a git pre-commit hook (#464).

Git gives a commit hook neither the {filePath} stdin nor PLUMBLINE_BRANCH the
branch guard reads, so wired in directly the guard blocks every commit. This
wrapper works both out from git and judges each staged path with the guard's
own decide() and PLUMBLINE_CFG checks, in-process: one Python start per
commit, not one per file. Copy it next to branch_guard.py, which it imports.
JS twin: branch-guard-commit.mjs. Cases: adapters/commit-hook-cases.json."""
import errno
import json
import os
import signal
import subprocess
import sys

# The guard is imported from this file's own directory, named explicitly:
# under PYTHONSAFEPATH or `python3 -P` / `-I` the script's directory is not on
# sys.path, and the import failed with exit 1.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from branch_guard import _is_branch_name, config_from_env, decide  # noqa: E402


def branch_from_ref(ref):
    """The branch HEAD names, from `git symbolic-ref HEAD`'s full ref, or None
    when HEAD is on no branch (detached, or pointing outside refs/heads/). The
    full ref, never --short: git shortens refs/heads/main to "heads/main" when
    a tag named main exists, and that string is not a protected branch."""
    return ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else None


def staged_paths(output):
    """The staged paths from `git diff --cached --name-only -z` output. Git
    paths are bytes: each is decoded as UTF-8 with U+FFFD for a bad sequence,
    as the JS twin's TextDecoder does (the two agree sequence for sequence),
    so a path that is not UTF-8 is still judged, not refused."""
    return [p.decode("utf-8", "replace") for p in output.split(b"\0")[:-1]]


def _operation(dir_name):
    """What a rebase-merge or rebase-apply directory is named for in a reason:
    `git am` also stops in rebase-apply, and writes no head-name."""
    return "a rebase or git am" if dir_name == "rebase-apply" else "a rebase"


def rebase_branch(dir_name, data, code):
    """The branch a rebase in progress is rebasing (#547), from the head-name
    file git records in its rebase-merge or rebase-apply directory, given the
    file's bytes (None when it cannot be read) and the read error's errno
    name. Returns {"branch": ...} for a branch; for anything else, the branch
    as far as it is known and "why", the reason it cannot be used. JS twin:
    rebaseBranch."""
    op = _operation(dir_name)
    if data is None:
        return {"branch": None,
                "why": f"HEAD is detached by {op} whose {dir_name}/head-name cannot be read: {code}"}
    ref = data.decode("utf-8", "replace").removesuffix("\n")
    branch = branch_from_ref(ref)
    if branch is None:
        return {"branch": None,
                "why": f"HEAD is detached by {op} of {json.dumps(ref, ensure_ascii=False)}, "
                       "which is not a branch"}
    if not _is_branch_name(branch):
        return {"branch": branch,
                "why": f"HEAD is detached by {op} of {json.dumps(branch, ensure_ascii=False)}, "
                       "which is not a branch name"}
    return {"branch": branch}


def update_ref_branches(data):
    """The other branches a rebase with --update-refs will move (#547
    review), from its update-refs file: each ref takes three lines, the ref
    and two object ids, and only refs/heads/ refs are branches. JS twin:
    updateRefBranches."""
    lines = data.decode("utf-8", "replace").split("\n")
    return [b for b in (branch_from_ref(line) for line in lines[::3]) if b is not None]


def judge_commit(branch, paths, config, why=None):
    """Judge a commit: every staged path through decide(), stopping at the
    first block. The branch is unknown when HEAD is on no branch (`branch`
    None) or on one git would not accept as a branch name, such as `-x`, which
    `git symbolic-ref` can still point HEAD at: then only a path allowed on
    every branch passes (#449). With the config already checked and a
    non-empty path, decide()'s only block on an unknown branch is the code
    edit, so that reason is replaced with one naming HEAD rather than
    PLUMBLINE_BRANCH, which this hook never reads; `why`, when given, says why
    the branch is unknown (a rebase in progress, #547). JS twin: judgeCommit."""
    known = branch is not None and _is_branch_name(branch)
    for file_path in paths:
        r = decide(
            file_path=file_path,
            branch=branch if branch is not None else "",
            protected_branches=tuple(config.get("protectedBranches", ["main"])),
            docs_allowlist=tuple(config.get("docsAllowlist", [])),
        )
        if r["allow"]:
            continue
        if known:
            return r
        if why is None:
            why = ("HEAD is not on a branch" if branch is None
                   else f"HEAD is on {json.dumps(branch, ensure_ascii=False)}, which is not a branch name")
        return {"allow": False,
                "reason": f"blocked: code edit to {file_path} with the branch unknown "
                          f"({why}). Switch to a branch first."}
    return {"allow": True, "reason": "no staged path is blocked"}


class _Refused(Exception):
    """A reason to block, from a git step that failed."""


def _git(args, what, ok_statuses=(0,)):
    """Run git; the finished process, or _Refused with the reason to block.
    Reasons match the JS twin's: the errno name when git cannot start (Node's
    error code), the signal's name when it is killed."""
    try:
        r = subprocess.run(["git", *args], stdin=subprocess.DEVNULL, capture_output=True)
    except OSError as e:
        code = errno.errorcode.get(e.errno, str(e)) if e.errno else str(e)
        raise _Refused(f"the branch guard's commit hook could not run git ({code}).") from None
    if r.returncode < 0:
        try:
            name = signal.Signals(-r.returncode).name
        except ValueError:
            name = f"signal {-r.returncode}"
        raise _Refused(f"the branch guard's commit hook could not {what} "
                       f"(git {args[0]} was killed by {name}).")
    if r.returncode not in ok_statuses:
        raise _Refused(f"the branch guard's commit hook could not {what} "
                       f"(git {args[0]} exited {r.returncode}).")
    return r


def _main():
    # The config first: a bad PLUMBLINE_CFG blocks whatever is staged.
    config, reason = config_from_env()
    if reason:
        return {"allow": False, "reason": reason}
    # --quiet: exit 1, silently, when HEAD is detached.
    head = _git(["symbolic-ref", "--quiet", "HEAD"], "read the branch", (0, 1))
    branch = (branch_from_ref(head.stdout.decode("utf-8", "replace").removesuffix("\n"))
              if head.returncode == 0 else None)
    why = None
    also, also_why = [], None
    # HEAD is detached during a rebase (#547). While git's rebase directory
    # exists, which git itself reads as a rebase in progress, the branch is
    # the one it records as being rebased, and with --update-refs every other
    # branch it will move is judged too. With no rebase directory a detached
    # HEAD stays unknown (#449).
    if head.returncode != 0:
        for dir_name in ("rebase-merge", "rebase-apply"):
            where = _git(["rev-parse", "--git-path", dir_name], "find the rebase state").stdout
            where = where.decode("utf-8", "replace").removesuffix("\n")
            if not os.path.exists(where):
                continue
            data, code = None, None
            try:
                with open(os.path.join(where, "head-name"), "rb") as f:
                    data = f.read()
            except OSError as e:
                code = errno.errorcode.get(e.errno, str(e)) if e.errno else str(e)
            r = rebase_branch(dir_name, data, code)
            branch, why = r["branch"], r.get("why")
            update_refs = os.path.join(where, "update-refs")
            if os.path.exists(update_refs):
                try:
                    with open(update_refs, "rb") as f:
                        also = update_ref_branches(f.read())
                except OSError as e:
                    ucode = errno.errorcode.get(e.errno, str(e)) if e.errno else str(e)
                    also_why = f"HEAD is detached by a rebase whose {dir_name}/update-refs cannot be read: {ucode}"
            break
    # --cached against HEAD (or the empty tree on an unborn branch), in the
    # index git is committing: during `git commit -a` or `git commit <path>`
    # that is the temporary index GIT_INDEX_FILE names. --no-renames: a rename
    # is listed as the path it leaves and the path it makes, so moving a code
    # file into docs/ is judged by the code path it deletes.
    # --ignore-submodules=none: diff.ignoreSubmodules or a submodule's
    # `ignore` setting would otherwise hide a staged submodule bump.
    diff = _git(["diff", "--cached", "--name-only", "-z", "--no-renames", "--ignore-submodules=none"],
                "list the staged files")
    paths = staged_paths(diff.stdout)
    r = judge_commit(branch, paths, config, why)
    if not r["allow"]:
        return r
    # Every branch the rebase will move must allow the commit (#547 review).
    if also_why is not None:
        return judge_commit(None, paths, config, also_why)
    for other in also:
        r2 = judge_commit(other, paths, config,
                          f"the rebase also moves {json.dumps(other, ensure_ascii=False)}, "
                          "which is not a branch name")
        if not r2["allow"]:
            return r2
    return r


if __name__ == "__main__":
    # Reasons are written as UTF-8, as Node writes them, whatever the locale
    # or PYTHONIOENCODING says, as the guard does.
    if sys.stderr is not None:
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    try:
        result = _main()
    except _Refused as e:
        result = {"allow": False, "reason": f"blocked: {e}"}
    except Exception as e:  # noqa: BLE001 — fail closed on anything
        result = {"allow": False, "reason": f"blocked: the branch guard's commit hook could not run ({e})."}
    if not result["allow"]:
        if sys.stderr is not None:
            sys.stderr.write(result["reason"] + "\n")
        # Exit 2 on every block and failure, as the guards do; git refuses
        # the commit on any non-zero exit.
        sys.exit(2)
    sys.exit(0)

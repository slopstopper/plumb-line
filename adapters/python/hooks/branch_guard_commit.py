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


def judge_commit(branch, paths, config):
    """Judge a commit: every staged path through decide(), stopping at the
    first block. The branch is unknown when HEAD is on no branch (`branch`
    None) or on one git would not accept as a branch name, such as `-x`, which
    `git symbolic-ref` can still point HEAD at: then only a path allowed on
    every branch passes (#449). With the config already checked and a
    non-empty path, decide()'s only block on an unknown branch is the code
    edit, so that reason is replaced with one naming HEAD rather than
    PLUMBLINE_BRANCH, which this hook never reads. JS twin: judgeCommit."""
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
    # --cached against HEAD (or the empty tree on an unborn branch), in the
    # index git is committing: during `git commit -a` or `git commit <path>`
    # that is the temporary index GIT_INDEX_FILE names. --no-renames: a rename
    # is listed as the path it leaves and the path it makes, so moving a code
    # file into docs/ is judged by the code path it deletes.
    # --ignore-submodules=none: diff.ignoreSubmodules or a submodule's
    # `ignore` setting would otherwise hide a staged submodule bump.
    diff = _git(["diff", "--cached", "--name-only", "-z", "--no-renames", "--ignore-submodules=none"],
                "list the staged files")
    return judge_commit(branch, staged_paths(diff.stdout), config)


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

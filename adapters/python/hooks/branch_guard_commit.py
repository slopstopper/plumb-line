"""branch_guard_commit — run the branch guard as a git pre-commit hook (#464).

Git gives a commit hook neither the {filePath} stdin nor PLUMBLINE_BRANCH the
branch guard reads, so wired in directly the guard blocks every commit. This
wrapper works both out from git and judges each staged path with the guard's
own decide() and PLUMBLINE_CFG checks, in-process: one Python start per
commit, not one per file. Copy it next to branch_guard.py, which it imports.
JS twin: branch-guard-commit.mjs. Cases: adapters/commit-hook-cases.json."""
import subprocess
import sys

from branch_guard import config_from_env, decide


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
    first block. `branch` None is a HEAD on no branch: unknown, so only a path
    allowed on every branch passes (#449). With the config already checked and
    a non-empty path, decide()'s only block on an unknown branch is the code
    edit, so that reason is replaced with one naming HEAD rather than
    PLUMBLINE_BRANCH, which this hook never reads."""
    for file_path in paths:
        r = decide(
            file_path=file_path,
            branch=branch if branch is not None else "",
            protected_branches=tuple(config.get("protectedBranches", ["main"])),
            docs_allowlist=tuple(config.get("docsAllowlist", [])),
        )
        if r["allow"]:
            continue
        if branch is not None:
            return r
        return {"allow": False,
                "reason": f"blocked: code edit to {file_path} with the branch unknown "
                          "(HEAD is not on a branch). Switch to a branch first."}
    return {"allow": True, "reason": "no staged path is blocked"}


class _Refused(Exception):
    """A reason to block, from a git step that failed."""


def _git(args, what, ok_statuses=(0,)):
    """Run git; the finished process, or _Refused with the reason to block."""
    try:
        r = subprocess.run(["git", *args], stdin=subprocess.DEVNULL, capture_output=True)
    except OSError as e:
        raise _Refused(f"the branch guard's commit hook could not run git ({e.strerror or e}).") from None
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
    diff = _git(["diff", "--cached", "--name-only", "-z", "--no-renames"], "list the staged files")
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

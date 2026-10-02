"""pre_commit_gate — block a commit if any runner fails; with PLUMBLINE_CFG
set, only on a protected branch (#613). JS twin: pre-commit-gate.mjs."""
import inspect
import itertools
import json
import os
import shlex
import subprocess
import sys

# Marks an empty iterable; a runner that is itself None is not "no runners".
_NONE = object()


def decide(runners):
    # A gate that ran nothing did not pass (#476): every way of not running the
    # tests blocks (#467), as in the JS twin. Only the first runner is read to
    # tell, so a generator is still read lazily and stops at the first failure.
    runners = iter(runners)
    first = next(runners, _NONE)
    if first is _NONE:
        return {"allow": False, "reason": "pre-commit blocked: no gates configured"}
    for name, fn in itertools.chain([first], runners):
        ok = fn()
        # Only True passes (#493): any other answer is one the gate cannot
        # read, and reading it by truth let 1, "ok" or an un-awaited coroutine
        # through. As in the JS twin, which awaits its runners.
        if inspect.isawaitable(ok):
            if inspect.iscoroutine(ok):
                ok.close()  # never awaited on purpose; close it quietly
            return {"allow": False, "reason": f"pre-commit blocked: {name} returned an awaitable; "
                                              "the Python gate runs synchronous runners only"}
        if ok is False:
            return {"allow": False, "reason": f"pre-commit blocked: {name} failed"}
        if ok is not True:
            return {"allow": False,
                    "reason": f"pre-commit blocked: {name} returned a result that is not true or false"}
    return {"allow": True, "reason": "all gates passed"}


# What testsOnOtherBranches may be (#613); absent means "skip".
_TESTS_ON_OTHER_BRANCHES = ("skip", "run")


def _guard_modules():
    """(branch_guard, branch_guard_commit), imported from this file's own
    directory, where bootstrap copies them (#613): the gate reads
    PLUMBLINE_CFG with the branch guard's checks and the branch as its commit
    hook does. Imported only when PLUMBLINE_CFG is set, so a gate copied
    alone still runs with it unset, as before. Named explicitly, as
    branch_guard_commit.py does: under `python3 -P` the script's directory
    is not on sys.path."""
    here = os.path.dirname(os.path.realpath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import branch_guard
    import branch_guard_commit
    return branch_guard, branch_guard_commit


def classify_branch(resolved, protected_branches, is_branch_name):
    """Where a commit lands, for the gate (#613), from resolve_branch() in
    branch_guard_commit.py: ("protected", branch), ("unknown", why) or
    ("other", branch). `is_branch_name` is the branch guard's rule. Judged in
    the commit hook's order: the branch itself, then every other branch a
    rebase with --update-refs will move. Any of them protected makes the
    commit protected; any of them unknown makes it unknown, which the gate
    treats as protected. JS twin: classifyBranch."""
    branch, why = resolved["branch"], resolved.get("why")
    if why is not None or branch is None or not is_branch_name(branch):
        if why is None:
            why = ("HEAD is not on a branch" if branch is None
                   else f"HEAD is on {json.dumps(branch, ensure_ascii=False)}, which is not a branch name")
        return ("unknown", why)
    if branch in protected_branches:
        return ("protected", branch)
    if resolved.get("also_why") is not None:
        return ("unknown", resolved["also_why"])
    for other in resolved.get("also", []):
        if not is_branch_name(other):
            return ("unknown", f"the rebase also moves {json.dumps(other, ensure_ascii=False)}, "
                               "which is not a branch name")
        if other in protected_branches:
            return ("protected", other)
    return ("other", branch)


# The gate's messages (#613), approved as text by the owner: change them only
# with the owner's approval. JS twin: MESSAGES.
def _protected_failed(branch):
    return (f"pre-commit blocked: the tests failed, and `{branch}` is a protected branch. Fix the code, or "
            f"commit on another branch (`git switch -c <name>`); there the tests can fail, and the work reaches "
            f"`{branch}` through review, not a local merge. Mark a test as an expected failure only if the user "
            "decides it should wait; mark it strict, with their reason.")


def _unknown_failed(why):
    return (f"pre-commit blocked: the tests failed, and the branch is unknown ({why}), so it is treated as "
            "protected. Fix the code, or commit on a named branch.")


def _skipped(branch):
    return (f'pre-commit: tests not run on `{branch}` (testsOnOtherBranches is "skip"), so this commit is '
            'unchecked. Set testsOnOtherBranches to "run" to run them here.')


def _other_failed(branch):
    return (f"pre-commit: the tests failed on `{branch}`; committed anyway (only protected branches block). "
            "This commit is red: say so when you report it.")


def _env_text(name):
    """The variable read from its bytes as UTF-8, whatever the locale says. Under
    an 8-bit locale, os.environ decodes each byte as one character, so a byte
    that is not UTF-8 looks valid and valid non-ASCII text is garbled (#501
    review). None when unset; a single U+FFFD for the whole value when it is
    not UTF-8, which _env_problem reads as a reason to block."""
    if os.supports_bytes_environ:
        raw = os.environb.get(name.encode())
    else:  # Windows: the environment is already text
        value = os.environ.get(name)
        raw = None if value is None else value.encode("utf-8", "surrogatepass")
    if raw is None:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return "\ufffd"


def _env(name):
    """The variable as the hook reads it, after _env_problem has passed it."""
    return _env_text(name)


def _env_problem(name):
    """Why an environment variable cannot be used, or None (#501). The JS twin
    only sees bytes that are not UTF-8 as U+FFFD, so U+FFFD counts as not valid
    here too. JS twin: envProblem."""
    text = _env_text(name)
    if text is not None and "\ufffd" in text:
        return (f"{name} is not valid UTF-8 (or holds U+FFFD, which invalid bytes are "
                "replaced with). Set it to UTF-8 text.")
    return None


# CLI. Every way of not running the tests exits 2 (#467): a Claude Code hook
# treats only exit 2 as a block, so exit 1 (or a traceback) let the commit
# through. Git treats any non-zero exit as a block, so nothing changes there.
# With PLUMBLINE_CFG set the gate is branch-aware (#613): a protected or
# unknown branch runs the tests and blocks on failure; any other branch skips
# them, or with testsOnOtherBranches "run" runs them and only reports a
# failure. The test command is checked first, so a broken one blocks even
# where the tests would be skipped. Cases: adapters/commit-hook-cases.json.
def _main():
    problem = _env_problem("PLUMBLINE_TEST_CMD")
    if problem:
        return {"allow": False, "reason": f"pre-commit blocked: {problem}"}
    cmd = _env("PLUMBLINE_TEST_CMD") or ""
    argv = shlex.split(cmd)
    if not argv:
        return {"allow": False, "reason": "pre-commit blocked: PLUMBLINE_TEST_CMD is not set"}

    # The command reaches the process as the UTF-8 bytes it was given, as in
    # the JS twin: subprocess would re-encode str arguments by the locale
    # (#501 re-review). Windows takes str arguments.
    run_argv = [w.encode("utf-8") for w in argv] if os.supports_bytes_environ else argv

    def _runner():
        return subprocess.run(run_argv).returncode == 0

    # With no PLUMBLINE_CFG the tests run on every branch and a failure
    # blocks, as before #613, and nothing else is read.
    if _env_text("PLUMBLINE_CFG") is None:
        return decide(runners=[(cmd, _runner)])
    try:
        branch_guard, branch_guard_commit = _guard_modules()
    except ImportError as e:
        return {"allow": False,
                "reason": "pre-commit blocked: PLUMBLINE_CFG is set, and the gate reads it with the branch "
                          f"guard's files, which cannot be loaded ({e}). Copy branch_guard.py and "
                          "branch_guard_commit.py beside the gate."}
    config, reason = branch_guard.config_from_env()
    if reason:
        return {"allow": False, "reason": "pre-commit " + reason}
    mode = config.get("testsOnOtherBranches", "skip")
    if mode not in _TESTS_ON_OTHER_BRANCHES:
        return {"allow": False,
                "reason": 'pre-commit blocked: PLUMBLINE_CFG testsOnOtherBranches must be "skip" or "run".'}
    # A branch that cannot be read is unknown, so treated as protected.
    try:
        resolved = branch_guard_commit.resolve_branch()
    except branch_guard_commit.GitRefused as e:
        resolved = {"branch": None, "why": f"the gate {e}"}
    except Exception as e:  # noqa: BLE001 — fail closed: unknown, never a pass
        resolved = {"branch": None, "why": f"the gate could not read the branch ({e})"}
    kind, which = classify_branch(resolved, config.get("protectedBranches", ["main"]),
                                  branch_guard._is_branch_name)
    if kind == "other" and mode == "skip":
        return {"allow": True, "reason": "tests skipped", "notice": _skipped(which)}
    r = decide(runners=[(cmd, _runner)])
    if r["allow"]:
        return r
    if kind == "other":
        return {"allow": True, "reason": "tests failed", "notice": _other_failed(which)}
    return {"allow": False,
            "reason": _protected_failed(which) if kind == "protected" else _unknown_failed(which)}


def _say(text):
    """Write a reason to stderr; with stderr closed the exit code still says it."""
    if sys.stderr is not None:
        sys.stderr.write(text)


if __name__ == "__main__":
    # Reasons are written as UTF-8, as Node writes them, whatever the locale
    # or PYTHONIOENCODING says; a closed stderr (2>&-) must not turn a block
    # into exit 1 (v0.11.5 dogfood, as #471 did for the guards).
    if sys.stderr is not None:
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    try:
        r = _main()
    except Exception as e:  # noqa: BLE001 — fail closed on anything
        r = {"allow": False, "reason": f"pre-commit blocked: the test command could not be run ({e})"}
    if not r["allow"]:
        _say(r["reason"] + "\n")
        sys.exit(2)
    if r.get("notice"):
        _say(r["notice"] + "\n")
    sys.exit(0)

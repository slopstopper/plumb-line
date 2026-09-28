"""pre_commit_gate — block a commit if any runner fails."""
import inspect
import itertools
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

# CLI. Every way of not running the tests exits 2 (#467): a Claude Code hook
# treats only exit 2 as a block, so exit 1 (or a traceback) let the commit
# through. Git treats any non-zero exit as a block, so nothing changes there.
def _env_problem(name):
    """Why an environment variable cannot be used, or None (#501). The JS twin
    only sees bytes that are not UTF-8 as U+FFFD, so U+FFFD counts as not valid
    here too. JS twin: envProblem."""
    value = os.environ.get(name)
    if value is None:
        return None
    try:
        text = value.encode("utf-8", "surrogateescape").decode("utf-8")
    except UnicodeError:
        text = "\ufffd"
    if "\ufffd" in text:
        return (f"{name} is not valid UTF-8 (or holds U+FFFD, which invalid bytes are "
                "replaced with). Set it to UTF-8 text.")
    return None


def _main():
    problem = _env_problem("PLUMBLINE_TEST_CMD")
    if problem:
        return {"allow": False, "reason": f"pre-commit blocked: {problem}"}
    cmd = os.environ.get("PLUMBLINE_TEST_CMD", "")
    argv = shlex.split(cmd)
    if not argv:
        return {"allow": False, "reason": "pre-commit blocked: PLUMBLINE_TEST_CMD is not set"}

    def _runner():
        return subprocess.run(argv).returncode == 0

    return decide(runners=[(cmd, _runner)])


if __name__ == "__main__":
    try:
        r = _main()
    except Exception as e:  # noqa: BLE001 — fail closed on anything
        r = {"allow": False, "reason": f"pre-commit blocked: the test command could not be run ({e})"}
    if not r["allow"]:
        sys.stderr.write(r["reason"] + "\n")
        sys.exit(2)
    sys.exit(0)

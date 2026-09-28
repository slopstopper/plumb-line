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

"""pre_commit_gate — block a commit if any runner fails."""
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
        if not fn():
            return {"allow": False, "reason": f"pre-commit blocked: {name} failed"}
    return {"allow": True, "reason": "all gates passed"}

# CLI. Every way of not running the tests exits 2 (#467): a Claude Code hook
# treats only exit 2 as a block, so exit 1 (or a traceback) let the commit
# through. Git treats any non-zero exit as a block, so nothing changes there.
def _main():
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

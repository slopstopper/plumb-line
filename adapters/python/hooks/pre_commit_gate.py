"""pre_commit_gate — block a commit if any runner fails."""
import os
import shlex
import subprocess
import sys

def decide(runners):
    for name, fn in runners:
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

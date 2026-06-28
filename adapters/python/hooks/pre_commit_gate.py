"""pre_commit_gate — block a commit if any runner fails."""
import json
import os
import shlex
import subprocess
import sys

def decide(runners):
    for name, fn in runners:
        if not fn():
            return {"allow": False, "reason": f"pre-commit blocked: {name} failed"}
    return {"allow": True, "reason": "all gates passed"}

if __name__ == "__main__":
    cmd = os.environ.get("PLUMBLINE_TEST_CMD")
    if not cmd:
        sys.stderr.write("PLUMBLINE_TEST_CMD not set\n")
        sys.exit(1)

    def _runner():
        result = subprocess.run(shlex.split(cmd))
        return result.returncode == 0

    r = decide(runners=[(cmd, _runner)])
    if not r["allow"]:
        sys.stderr.write(r["reason"] + "\n")
        sys.exit(2)
    sys.exit(0)

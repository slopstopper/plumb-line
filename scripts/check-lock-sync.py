#!/usr/bin/env python3
"""check-lock-sync.py — guard that requirements-test.txt is still a *universal* lock.

plumb-line supports Python 3.9, but several test deps have newer releases that
require >=3.10 (e.g. click 8.4.x, coverage 7.15, grimp 3.14). The lock keeps 3.9
alive by compiling *universally*:

    uv pip compile requirements-test.in --generate-hashes --universal \
        --python-version 3.9 -o requirements-test.txt

That produces per-Python-version splits carrying environment markers, e.g.

    click==8.1.8 ; python_full_version < '3.10'
    click==8.4.2 ; python_full_version >= '3.10'

Dependabot cannot run uv. When it bumps a pip dependency it regenerates the
lock with a plain resolver, which *flattens* those splits into unconditional
pins (a single `click==8.4.2`). That pin requires Python >=3.10, so
`pip install --require-hashes` fails on the 3.9 CI leg before a single test
runs — the failure that keeps landing on Dependabot pip PRs.

This guard detects the flattening: a correctly compiled universal lock contains
`python_full_version < '3.10'` markers; a flattened one contains none. Run it in
CI so a mangled lock can never merge, and so the failure is legible instead of a
cryptic "No matching distribution found for click==8.4.2".
"""
from __future__ import annotations

import sys
from pathlib import Path

LOCK = Path(__file__).resolve().parent.parent / "requirements-test.txt"
MARKER = "python_full_version < '3.10'"

RECOMPILE = (
    "uv pip compile requirements-test.in --generate-hashes --universal \\\n"
    "    --python-version 3.9 -o requirements-test.txt"
)


def main(argv: list[str]) -> int:
    lock = Path(argv[1]) if len(argv) > 1 else LOCK
    if not lock.exists():
        print(f"✗ {lock.name} not found", file=sys.stderr)
        return 1

    text = lock.read_text(encoding="utf-8")
    count = text.count(MARKER)
    if count == 0:
        print(
            f"✗ {lock.name} is not a universal lock: no "
            f"`{MARKER}` markers found.\n"
            "  The Python 3.9 / >=3.10 dependency splits were flattened (this is\n"
            "  what Dependabot does when it regenerates the lock without uv), so\n"
            "  `pip install --require-hashes` will fail on the Python 3.9 runner.\n"
            "  Recompile the lock from requirements-test.in:\n\n"
            f"    {RECOMPILE}\n\n"
            "  then commit the result (git commit -s).",
            file=sys.stderr,
        )
        return 1

    print(f"✓ {lock.name} is a universal lock ({count} Python-version split markers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

# Support policy

## Supported Python versions

plumb-line supports the CPython versions that are **not** end-of-life.

- The **floor** is raised when a version reaches EOL — **proactively, on Python's
  published [EOL calendar](https://devguide.python.org/versions/)**, not
  reactively when a dependency happens to force it.
- CI tests the current floor and the newest released CPython; every version in
  between is supported.

**Current floor: Python 3.11.** (3.9 and 3.10 are past or near EOL; downstream
users on <3.11 are on unsupported runtimes.)

### Why this policy

Setting the floor at whatever a dependency *just* dropped lands us on the version
about to go EOL — so the floor needed re-litigating every few weeks, and every
Python-dropping dependency bump became a per-PR judgement call. Pinning the floor
to "not EOL" makes every such bump automatically safe to take (it's dropping a
dead runtime) and removes the recurring decision. A scheduled reminder
(`.github/workflows/python-eol-reminder.yml`) opens an issue ahead of each EOL so
the floor moves *before* dependencies force it.

## Reporting issues

Bugs and feature requests: <https://github.com/slopstopper/plumb-line/issues>.
Security reports: see [SECURITY.md](SECURITY.md).

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

## Supported Node.js versions

plumb-line supports the Node.js release lines that are **in maintenance or
active LTS** — the same not-EOL rule as Python, against Node's published
[release schedule](https://github.com/nodejs/release#release-schedule) — with
one honest addition: the floor is never claimed below **the lowest version CI
actually exercises**. The v0.9.0 lesson ([#233]): the published `>= 16` floor
was partly false (the `./http` subpath needs Node ≥ 18) and untestable (the
test runner needs ≥ 20), so the supported floor is the tested floor.

- The floor is raised when a release line reaches EOL, proactively on the
  calendar — or earlier when a toolchain floor forces it, in which case the
  raise is a minor release and the reason is recorded (the #233 precedent).
- CI tests the current floor and the newest LTS; lines in between are
  supported.

**Current floor: Node 20.** (18 is EOL; CI exercises 20 and 22.)

[#233]: https://github.com/slopstopper/plumb-line/issues/233

## Reporting issues

Bugs and feature requests: <https://github.com/slopstopper/plumb-line/issues>.
Security reports: see [SECURITY.md](SECURITY.md).

"""The honest-deferral example's claims, enforced (#485).

`examples/honest-deferral/` shows the one form of "make the failing test
pass" that the method skill allows when the reason is outside the code: keep
the assertion, mark the test as a *strict* expected failure with its reason,
and hand the decision back. These tests prove the two properties the skill
relies on, in both languages:

- as shipped, the requirement test is recorded as an expected failure and
  the suite exits 0, while the test for the failure you can observe (the
  carrier is unreachable, so the quote says so) passes;
- the moment the requirement is met (simulated here by making the carrier
  reachable in a copy, never in the example's own code), the strict marker
  turns the unexpected pass into a failing suite, so the deferral cannot
  outlive its reason unnoticed.

The JS half needs `npm ci` in examples/honest-deferral/js. Without it that
half skips loudly locally; CI installs it and fails the examples step on any
skip here.

Run from the repo root: python3 -m pytest -q examples/test_honest_deferral.py
"""
import os
import shutil
import subprocess
import sys

import pytest

EXAMPLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "honest-deferral")
PY = os.path.join(EXAMPLE, "python")
JS = os.path.join(EXAMPLE, "js")

# Makes the carrier reachable for every test in the copy: the quote the
# carrier's published rate card gives for the standard parcel.
PY_REACHABLE = '''
import pytest
import carrier


@pytest.fixture(autouse=True)
def _carrier_reachable(monkeypatch):
    monkeypatch.setattr(carrier, "fetch_quote", lambda parcel: 12.40)
'''

JS_REACHABLE = '''
import { client } from "./src/carrier.js";
client.fetchQuote = async () => 12.4;
'''


def _pytest(cwd):
    env = {k: v for k, v in os.environ.items() if k != "CARRIER_API_KEY"}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rxX", "-p", "no:cacheprovider", "."],
        cwd=cwd, capture_output=True, text=True, env=env)


def _copy(src, tmp_path):
    dst = tmp_path / "example"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
        "node_modules", "__pycache__", ".pytest_cache"))
    return dst


def test_python_deferral_is_recorded_and_the_observable_failure_is_handled(tmp_path):
    r = _pytest(_copy(PY, tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 passed" in r.stdout and "1 xfailed" in r.stdout, r.stdout
    # The reason travels with the marker, so the report says why.
    assert "carrier sandbox" in r.stdout, r.stdout


def test_python_strict_marker_fails_the_suite_once_the_requirement_is_met(tmp_path):
    dst = _copy(PY, tmp_path)
    (dst / "conftest.py").write_text(PY_REACHABLE, encoding="utf-8")
    r = _pytest(dst)
    assert r.returncode != 0, r.stdout
    assert "XPASS(strict)" in r.stdout, r.stdout


def _vitest(cwd, *extra):
    vitest = os.path.join(JS, "node_modules", ".bin", "vitest")
    if not os.path.exists(vitest):
        pytest.skip("JS example toolchain not installed: run npm ci in examples/honest-deferral/js")
    env = {k: v for k, v in os.environ.items()
           if k not in ("CARRIER_API_KEY", "FORCE_COLOR")}
    env["NO_COLOR"] = "1"
    return subprocess.run([vitest, "run", *extra], cwd=cwd, capture_output=True,
                          text=True, env=env)


def _copy_js(tmp_path):
    dst = _copy(JS, tmp_path)
    os.symlink(os.path.join(JS, "node_modules"), dst / "node_modules")
    return dst


def test_js_deferral_is_recorded_and_the_observable_failure_is_handled(tmp_path):
    r = _vitest(_copy_js(tmp_path))
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "1 passed" in out and "1 expected fail" in out, out


def test_js_strict_marker_fails_the_suite_once_the_requirement_is_met(tmp_path):
    dst = _copy_js(tmp_path)
    (dst / "reachable.setup.js").write_text(JS_REACHABLE, encoding="utf-8")
    (dst / "vitest.config.js").write_text(
        'export default { test: { setupFiles: ["./reachable.setup.js"] } };\n',
        encoding="utf-8")
    r = _vitest(dst)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out
    # The failure must be the strict marker's, not a broken run: the
    # observable-failure test still passes and the deferred one fails.
    assert "1 failed" in out and "1 passed" in out, out

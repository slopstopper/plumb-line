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
# "The carrier is reachable" is simulated where reality would change: the key
# is provisioned and the carrier answers the request. The example's code runs
# unchanged, and its missing-key test (which unsets the key) still applies.
PY_REACHABLE = '''
import io
import json

import pytest

import carrier


class _Answer(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture(autouse=True)
def _carrier_reachable(monkeypatch):
    monkeypatch.setenv("CARRIER_API_KEY", "sandbox-key")
    monkeypatch.setattr(carrier.urllib.request, "urlopen",
                        lambda request, timeout: _Answer(json.dumps({"price": 12.40}).encode()))
'''

JS_REACHABLE = '''
process.env.CARRIER_API_KEY = "sandbox-key";
globalThis.fetch = async () => new Response(JSON.stringify({ price: 12.4 }), { status: 200 });
'''


def _pytest(cwd):
    env = {k: v for k, v in os.environ.items()
           if k not in ("CARRIER_API_KEY", "FORCE_COLOR")}
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
    # The failure is the strict marker's: the missing-key test still passes.
    assert "XPASS(strict)" in r.stdout and "1 failed, 1 passed" in r.stdout, r.stdout


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


# --- #485 review: a marker must not absorb a crash --------------------------
# Both markers accept a failing test as expected. If the code crashed on the
# missing key instead of answering "unavailable", a deferral that absorbed the
# crash would hide exactly the regression the skill warns about. The
# observable-failure test must catch it, running the real code with the key
# unset; pytest's raises=AssertionError also refuses to count a crash.

PY_CRASH = ('raise CarrierUnavailable("no CARRIER_API_KEY: the carrier sandbox cannot be reached")',
            'raise KeyError("CARRIER_API_KEY")')
JS_CRASH = ('throw new CarrierUnavailable("no CARRIER_API_KEY: the carrier sandbox cannot be reached")',
            'throw new TypeError("CARRIER_API_KEY")')


def _break(path, old_new):
    old, new = old_new
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{path.name} no longer has the line this test breaks"
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_python_a_crash_on_the_missing_key_fails_the_suite(tmp_path):
    dst = _copy(PY, tmp_path)
    _break(dst / "carrier.py", PY_CRASH)
    r = _pytest(dst)
    assert r.returncode != 0, r.stdout
    # Both tests fail: the observable one, and the deferred one, whose
    # raises=AssertionError does not accept a KeyError as the expected failure.
    assert "2 failed" in r.stdout, r.stdout


def test_js_a_crash_on_the_missing_key_fails_the_suite(tmp_path):
    dst = _copy_js(tmp_path)
    _break(dst / "src" / "carrier.js", JS_CRASH)
    r = _vitest(dst)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out
    # it.fails accepts any error, so the deferred test still reads as an
    # expected fail; the observable-failure test is what catches the crash.
    assert "1 failed" in out and "1 expected fail" in out, out

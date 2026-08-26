"""
Integrity test for the incident-toolserver demo (deterministic).

The demo's claim is behavioral: the broken run looks clean while three of five
tools are stubs, and the instrumented run makes the same computation confess.
This test locks that behavior by running both scripts and asserting the output
markers — a drift detector for the demo, like test_fixture_integrity.py is for
the audit fixtures. Run with: `pytest -q examples/incident-toolserver/test_demo.py`
"""

import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="node is required to run the demo scripts"
)


def run(script):
    result = subprocess.run(
        ["node", str(HERE / script)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return result.stdout


def test_broken_run_looks_clean_and_says_nothing_about_mocks():
    out = run("broken/toolserver.mjs")
    assert "operational (5/5 tools succeeded)" in out, \
        "broken report must aggregate the stub successes into a green summary"
    assert "mock" not in out.lower(), \
        "the broken run must carry no signal that anything is fake — that's the incident"


def test_instrumented_run_confesses_the_mock_fraction():
    out = run("instrumented/toolserver.mjs")
    assert "derivedFromMock: true" in out, \
        "the aggregated report must inherit taint from the stub tools"
    assert "3/5" in out, \
        "the mock fraction must be computed from lineage, not estimated"
    assert "weakestSource: mock" in out


def test_instrumented_run_flags_the_attempted_launder():
    out = run("instrumented/toolserver.mjs")
    assert "laundering:" in out, \
        "claiming the tainted report as 'real' must be flagged by auditMeta"

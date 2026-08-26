"""
Integrity test for the incident-loadsheet demo (deterministic).

The demo's claim is behavioral: the broken run prints a tidy, wrong load sheet
with no signal that any input was guessed, and the instrumented run makes the
same computation carry its uncertainty. This test locks that behavior by
running both scripts and asserting the output markers — a drift detector for
the demo. Run with: `pytest -q examples/incident-loadsheet/test_loadsheet_demo.py`
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(script):
    result = subprocess.run(
        [sys.executable, str(HERE / script)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return result.stdout


def test_broken_run_looks_clean_and_says_nothing_about_guesses():
    out = run("broken/loadsheet.py")
    assert "load sheet: complete" in out, \
        "broken run must end with a confident, tidy summary"
    assert "inferred" not in out.lower(), \
        "the broken run must carry no signal that any category was guessed — that's the incident"


def test_broken_total_is_understated():
    out = run("broken/loadsheet.py")
    assert "total takeoff mass: 693 kg" in out, \
        "broken total must reflect the three misclassified adults (84 kg counted as 35 kg)"


def test_instrumented_run_carries_the_uncertainty():
    out = run("instrumented/loadsheet.py")
    assert "confidence: low" in out
    assert "weakest_source: inferred" in out
    assert "3/10" in out, \
        "the inferred fraction must be computed from lineage, not estimated"


def test_instrumented_run_flags_the_attempted_overclaim():
    out = run("instrumented/loadsheet.py")
    assert "over-claiming: confidence 'high' exceeds weakest lineage confidence 'low'" in out, \
        "claiming high confidence over inferred inputs must be flagged by audit_meta"

"""
Integrity test for the incident-pipeline demo (deterministic).

The demo's claim is behavioral: the broken run stores two contradictory
conclusions as indistinguishable artifacts, and the instrumented run makes
each conclusion carry the chain that produced it, so the flip is attributable
in one read. This test locks that behavior by running both scripts and
asserting the output markers. Run with:
`pytest -q examples/incident-pipeline/test_pipeline_demo.py`
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


def test_broken_run_stores_contradictory_indistinguishable_conclusions():
    out = run("broken/pipeline.py")
    assert "conclusion: effect: positive (mean +0.40)" in out
    assert "conclusion: effect: negative (mean -0.40)" in out, \
        "the inherited script's sign flip must silently invert the conclusion"
    assert "preprocess" not in out.lower() and "lineage" not in out.lower(), \
        "broken artifacts must carry no record of which processing produced them — that's the incident"


def test_instrumented_run_attributes_each_conclusion_to_its_chain():
    out = run("instrumented/pipeline.py")
    assert "preprocess.baseline_subtract@v1" in out
    assert "preprocess.inherited@v2" in out, \
        "each conclusion must name the exact processing step that produced it"
    assert "measurements.csv [real/high]" in out, \
        "the chain must bottom out at the recorded raw source"


def test_instrumented_run_flags_the_lineage_free_conclusion():
    out = run("instrumented/pipeline.py")
    assert "unreproducible: derived value has no lineage" in out, \
        "a conclusion stored without its lineage must be flagged by audit_meta"

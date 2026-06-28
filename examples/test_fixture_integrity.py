"""
Fixture-integrity regression test (deterministic).

The audit *skill* is an LLM behavior and cannot be unit-tested deterministically
(see AUDIT-EXPECTATIONS.md for the blind-audit harness that scores it). What CAN
regress silently is the fixtures themselves: a refactor could remove a planted
violation from `broken/`, or accidentally introduce one into `clean/`, and the
answer keys (VIOLATIONS.md) would quietly stop matching the code.

This test locks the structural markers of each planted violation: present in
`broken/`, absent in `clean/`. It is a drift detector for the fixtures, not a
test of the audit skill. Run with: `pytest -q examples/test_fixture_integrity.py`
"""

import re
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parent
JS = EXAMPLES / "js-payments-service"
PY = EXAMPLES / "python-data-pipeline"


def read(*parts):
    return Path(*parts).read_text(encoding="utf-8")


# --- JS payments fixture -----------------------------------------------------


def test_js_p2_boundary_leak_present_in_broken_absent_in_clean():
    # data layer must not import from the ui layer (upward import).
    ui_import = re.compile(r"""import[^;]*from\s+['"][^'"]*ui/""")
    assert ui_import.search(read(JS, "broken/src/data/rates.js")), \
        "broken JS data/rates.js should contain the planted upward ui import (P2)"
    assert not ui_import.search(read(JS, "clean/src/data/rates.js")), \
        "clean JS data/rates.js must not import from ui"


def test_js_p5_hardcoded_prior_present_in_broken_absent_in_clean():
    broken = read(JS, "broken/src/engine/pricing.js")
    clean = read(JS, "clean/src/engine/pricing.js")
    # Match actual code (an assignment), not a JSDoc/comment mention of the name.
    reads_config = re.compile(r"=\s*config\.processingFeeRate")
    assert re.search(r"const\s+FEE\s*=", broken), \
        "broken JS engine/pricing.js should hardcode a FEE const (P5)"
    assert reads_config.search(clean), \
        "clean JS engine/pricing.js should assign the fee rate from injected config"
    assert not reads_config.search(broken), \
        "broken JS engine/pricing.js should NOT read the fee from config (that's the violation)"


def test_js_p3_provenance_confidence_present_in_clean_absent_in_broken():
    clean = read(JS, "clean/src/services/gateway.js")
    broken = read(JS, "broken/src/services/gateway.js")
    # Match object keys in the return shape, not the words in a comment.
    prov_key = re.compile(r"provenance\s*:")
    conf_key = re.compile(r"confidence\s*:")
    assert prov_key.search(clean) and conf_key.search(clean), \
        "clean JS gateway response must carry provenance + confidence keys (P3)"
    assert not prov_key.search(broken) and not conf_key.search(broken), \
        "broken JS gateway response should drop the provenance/confidence keys (planted P3)"


def test_js_clean_propagates_weights_version_lineage():
    # Hardening: the engine records weightsVersion; the service must carry it
    # through so a sibling-adopted lineage field is not dropped (P8 consistency).
    assert "weightsVersion" in read(JS, "clean/src/engine/pricing.js")
    assert "weightsVersion" in read(JS, "clean/src/services/gateway.js"), \
        "clean JS gateway should propagate weightsVersion from the engine result"


# --- Python data-pipeline fixture -------------------------------------------


def test_py_p2_boundary_leak_present_in_broken_absent_in_clean():
    ui_import = re.compile(r"from\s+src\.ui")
    assert ui_import.search(read(PY, "broken/src/data/schema.py")), \
        "broken PY data/schema.py should contain the planted upward ui import (P2)"
    assert not ui_import.search(read(PY, "clean/src/data/schema.py")), \
        "clean PY data/schema.py must not import from src.ui"


def test_py_p5_hardcoded_prior_present_in_broken_absent_in_clean():
    broken = read(PY, "broken/src/engine/aggregate.py")
    clean = read(PY, "clean/src/engine/aggregate.py")
    assert "SIGNAL_THRESHOLD" in broken, \
        "broken PY engine/aggregate.py should hardcode SIGNAL_THRESHOLD (P5)"
    assert re.search(r"""config\[['"]signal_threshold['"]\]""", clean), \
        "clean PY engine/aggregate.py should read signal_threshold from injected config"
    assert not re.search(r"""config\[['"]signal_threshold['"]\]""", broken), \
        "broken PY engine/aggregate.py should NOT read the threshold from config"


def test_py_p8_lineage_present_in_clean_absent_in_broken():
    clean = read(PY, "clean/src/services/source.py")
    broken = read(PY, "broken/src/services/source.py")
    assert "lineage" in clean, \
        "clean PY services/source.py must record a lineage field (P8)"
    assert "lineage" not in broken, \
        "broken PY services/source.py should drop lineage (the planted P8 violation)"

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


def test_py_clean_ui_propagates_weights_version_structurally():
    # Cross-language parity of the same hardening: the v0.6.0 harness caught the
    # Python clean ui carrying weights_version only inside display_text — a
    # structured consumer could not see which priors produced the result. The
    # clean fixture must expose it as a return-dict key, mirroring JS
    # clean/src/ui/checkout.js.
    clean = read(PY, "clean/src/ui/report.py")
    assert re.search(r'"weights_version"\s*:\s*result\[', clean), \
        "clean PY ui report must propagate weights_version as a structured key"


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


# --- ratchet-adoption fixture (#119) -----------------------------------------

RATCHET = EXAMPLES / "ratchet-adoption"


def test_ratchet_fixture_pins_all_sites_in_clean_and_one_fewer_in_broken():
    import json
    clean = json.loads(read(RATCHET, "clean/.plumb-line/ratchet.json"))["sites"]["python.output"]
    broken = json.loads(read(RATCHET, "broken/.plumb-line/ratchet.json"))["sites"]["python.output"]
    assert clean == ["src/pricing/fx.py::apply_fx", "src/pricing/fx.py::total"]
    assert broken == ["src/pricing/fx.py::apply_fx"], "broken leaves `total` unpinned so it is a NEW site"
    assert read(RATCHET, "clean/src/pricing/fx.py") == read(RATCHET, "broken/src/pricing/fx.py"), \
        "the two trees differ only in the ratchet file"


# --- the incident demos must RUN in CI, never skip (ADR-0016) ----------------

CI_WORKFLOW = EXAMPLES.parent / ".github" / "workflows" / "ci.yml"


def ci_step(name_fragment):
    """The `run:` body of the first ci.yml step whose name contains the fragment."""
    ci = read(CI_WORKFLOW)
    start = ci.index("- name: " + name_fragment)
    rest = ci[start:]
    end = rest.find("\n      - ", 1)
    return rest if end < 0 else rest[:end]


def test_every_incident_demo_test_is_named_the_way_the_ci_guard_greps_for_it():
    demos = sorted(p.name for p in EXAMPLES.glob("incident-*/test_*_demo.py"))
    assert demos == ["test_loadsheet_demo.py", "test_pipeline_demo.py",
                     "test_toolserver_demo.py"], demos


def test_ci_fails_if_an_incident_demo_test_skips():
    # ADR-0016: a skipped proof is a lost proof. test_toolserver_demo.py skips
    # without node, and these three tests are the only proof of the transcripts
    # the README publishes — so CI must require them to run, the way it already
    # does for the end-to-end SARIF test.
    step = ci_step("examples — fixtures")
    assert "-rs" in step, "pytest needs -rs for the skip guard to have anything to grep"
    assert "_demo.py" in step and "SKIPPED" in step, \
        "the examples step must grep its own output for a skipped incident-demo test"
    assert "::error::" in step, "a skipped demo must fail the job, not warn"

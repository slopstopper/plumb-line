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

import pytest

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


# --- ratchet-adoption-js fixture (#393) --------------------------------------

RATCHET_JS = EXAMPLES / "ratchet-adoption-js"


def test_js_ratchet_fixture_pins_all_sites_in_clean_and_one_fewer_in_broken():
    import json
    clean = json.loads(read(RATCHET_JS, "clean/.plumb-line/ratchet.json"))["sites"]["js.output"]
    broken = json.loads(read(RATCHET_JS, "broken/.plumb-line/ratchet.json"))["sites"]["js.output"]
    assert clean == ["src/pricing/fx.js::applyFx", "src/pricing/fx.js::total"]
    assert broken == ["src/pricing/fx.js::applyFx"], "broken leaves `total` unpinned so it is a NEW site"
    assert read(RATCHET_JS, "clean/src/pricing/fx.js") == read(RATCHET_JS, "broken/src/pricing/fx.js"), \
        "the two trees differ only in the ratchet file"


def test_js_ratchet_fixture_config_registers_the_adapter_plugin_by_relative_path():
    # The fixture proves the JS half end to end only if it runs the REAL rule
    # from adapters/js/provenance-lint — not a copy that could drift.
    for tree in ("broken", "clean"):
        cfg = read(RATCHET_JS, tree, "eslint-provenance.cjs")
        assert 'require("../../../adapters/js/provenance-lint/index.cjs")' in cfg, tree
        assert '"plumb-line/require-provenance-output": "error"' in cfg, tree


# --- the incident demos must RUN in CI, never skip (ADR-0016) ----------------

CI_WORKFLOW = EXAMPLES.parent / ".github" / "workflows" / "ci.yml"


RELEASE_WORKFLOW = EXAMPLES.parent / ".github" / "workflows" / "release.yml"


def workflow_step(workflow, name_fragment):
    """The first step of `workflow` whose name contains the fragment, and its
    offset in the file (so a test can check what runs before it)."""
    text = read(workflow)
    start = text.index("- name: " + name_fragment)
    rest = text[start:]
    end = rest.find("\n      - ", 1)
    return (rest if end < 0 else rest[:end]), start


def ci_step(name_fragment):
    """The `run:` body of the first ci.yml step whose name contains the fragment."""
    return workflow_step(CI_WORKFLOW, name_fragment)[0]


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


# --- the release gate is PR CI itself, never a hand-kept copy of it ---------

_SKIP_GUARD = re.compile(r"grep -qE '(SKIPPED[^']*)'")


def test_examples_step_fails_on_skipped_must_run_tests():
    step = ci_step("examples — fixtures")
    assert "-rs" in step and "set -o pipefail" in step
    guard = _SKIP_GUARD.search(step)
    assert guard and "test_ratchet_fixtures" in guard.group(1) and "_demo" in guard.group(1)
    assert "::error::" in step


def test_every_js_fixture_tree_is_installed_before_the_examples_step():
    trees = sorted({p.parent.parent.name for p in EXAMPLES.glob("*/*/package-lock.json")})
    assert trees, "expected JS fixtures with lockfiles under examples/"
    install, at = workflow_step(CI_WORKFLOW, "JS fixture toolchain")
    _, examples_at = workflow_step(CI_WORKFLOW, "examples — fixtures")
    assert at < examples_at, "the toolchain must be installed before the examples step"
    for tree in trees:
        assert tree in install, f"fixture {tree} is not installed"


def _job(workflow_text, name):
    """The body of a top-level job (two-space indent) in a workflow file."""
    m = re.search(r"^  %s:\n(.*?)(?=^  [a-z][a-z-]*:\n|\Z)" % re.escape(name), workflow_text, re.M | re.S)
    assert m, f"no job {name!r}"
    return m.group(1)


def test_release_publishes_only_after_the_whole_of_ci_passes():
    # A release must not pass a narrower gate than a PR. The hand-kept copy
    # of CI's steps in release.yml drifted (0.11.2 published with the JS
    # ratchet byte checks skipped, and without the SARIF end-to-end suite or
    # the scripts/ checkers), so the release now CALLS ci.yml and publishes
    # only when every one of its jobs passes.
    ci = read(CI_WORKFLOW)
    release = read(RELEASE_WORKFLOW)
    on_block = ci[ci.index("\non:"):ci.index("\npermissions:")]
    assert "workflow_call:" in on_block, "ci.yml must be callable by the release workflow"
    gate = _job(release, "ci")
    assert "uses: ./.github/workflows/ci.yml" in gate
    assert re.search(r"needs:\s*\[?\s*guard", gate), "run CI after the tag guard"
    publish = _job(release, "release")
    assert re.search(r"needs:\s*\[?[^\n]*\bci\b", publish), "publish only after ci passes"
    for step in ("npm test", "pytest -q examples", "pytest -q\n"):
        assert step not in publish, f"test step {step!r} copied into the publish job; CI owns tests"

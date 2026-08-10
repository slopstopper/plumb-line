"""Tests for scripts/check_version_prose.py — the wire-version prose gate.

Run from the repo root:

    python3 -m pytest -q scripts/test_version_prose.py

Mirrors the scripts/test_bundle_conformance.py precedent: a pytest suite for a
repo-infrastructure script that lives outside any package, loaded by path under
a private module name.
"""
import importlib.util
import os

_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_version_prose.py")
_spec = importlib.util.spec_from_file_location("_check_version_prose", _SCRIPT)
cvp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cvp)


def test_reads_current_version_from_provenance_source():
    assert cvp.read_current_version("# comment\nPROVENANCE_VERSION = 2\n") == 2


def test_current_version_reference_passes():
    findings = cvp.scan_text("README.md", "envelope schema version 2 is current", 2)
    assert findings == []


def test_previous_version_reference_is_flagged():
    findings = cvp.scan_text("README.md", "envelope schema version 1 is current", 2)
    assert len(findings) == 1
    assert findings[0].found == 1
    assert findings[0].expected == 2
    assert findings[0].line_no == 1


def test_future_version_reference_is_flagged():
    # A grep-for-N-1 design would miss this; a typo or premature bump must fail.
    findings = cvp.scan_text("README.md", "schema version 5", 2)
    assert len(findings) == 1
    assert findings[0].found == 5


def test_badge_form_is_flagged():
    findings = cvp.scan_text("R.md", "[![provenance: plumb-line v1](x)](y)", 2)
    assert len(findings) == 1


def test_constant_adjacent_form_is_flagged():
    findings = cvp.scan_text("R.md", "the `PROVENANCE_VERSION` stays `1` here", 2)
    assert len(findings) == 1


def test_unrelated_numbers_are_not_flagged():
    findings = cvp.scan_text("R.md", "SPEC section 1 lists 3 rules and 2 laws", 2)
    assert findings == []


def test_historical_paths_are_exempt():
    assert cvp.is_exempt_path("CHANGELOG.md")
    assert cvp.is_exempt_path("docs/adr/0010-wire-v2-schema-batch.md")
    assert cvp.is_exempt_path("docs/dogfood.md")
    assert cvp.is_exempt_path("docs/validation-results.md")
    assert not cvp.is_exempt_path("README.md")
    assert not cvp.is_exempt_path("ROADMAP.md")

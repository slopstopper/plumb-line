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


def test_marker_on_same_line_exempts_it():
    text = "Additive; `PROVENANCE_VERSION` stayed 1. <!-- wire-version-historical -->"
    assert cvp.scan_text("ROADMAP.md", text, 2) == []


def test_marker_alone_on_next_line_exempts_previous_line():
    text = "Additive; `PROVENANCE_VERSION` stayed 1.\n<!-- wire-version-historical -->\n"
    assert cvp.scan_text("ROADMAP.md", text, 2) == []


def test_marker_alone_skips_blank_lines_to_reach_target():
    text = "schema version 1\n\n<!-- wire-version-historical -->\n"
    assert cvp.scan_text("ROADMAP.md", text, 2) == []


def test_marker_does_not_exempt_unrelated_lines():
    text = "schema version 1\nschema version 1 <!-- wire-version-historical -->\n"
    findings = cvp.scan_text("ROADMAP.md", text, 2)
    assert len(findings) == 1
    assert findings[0].line_no == 1


BADGE_V2 = (
    "[![provenance: plumb-line v2]"
    "(https://img.shields.io/badge/provenance-plumb--line_v2-3b82f6)]"
    "(https://github.com/slopstopper/plumb-line/blob/main/primitives/SPEC.md)"
)


def test_badge_present_passes():
    assert cvp.badge_mismatch(BADGE_V2, "intro\n" + BADGE_V2 + "\noutro") is None


def test_badge_absent_is_reported():
    stale = BADGE_V2.replace("v2", "v1")
    msg = cvp.badge_mismatch(BADGE_V2, "intro\n" + stale + "\noutro")
    assert msg is not None
    assert "report.mjs --badge" in msg


# --- retrospective review of #204: false positives on ordinary prose -------
#
# The proximity pattern matched any digits near the constant name, so correct
# sentences hard-failed CI with a nonsense number — and the failure message
# advised tagging the line historical, which would mislabel live prose.

def test_issue_reference_near_the_constant_is_not_a_version():
    assert cvp.scan_text("x.md", "`PROVENANCE_VERSION` (issue #160) is the wire version", 2) == []


def test_adr_number_near_the_constant_is_not_a_version():
    assert cvp.scan_text("x.md", "PROVENANCE_VERSION — see ADR 0010", 2) == []


def test_release_version_is_not_the_wire_version():
    """The two numbers are explicitly independent in this project;
    'plumb-line v0.8.0' must not read as wire version 0."""
    assert cvp.scan_text("x.md", "plumb-line v0.8.0 ships the floor change", 2) == []
    assert cvp.scan_text("x.md", "the `PROVENANCE_VERSION` bump in v0.8.0", 2) == []


def test_assertion_forms_are_still_caught():
    """Tightening the pattern must not cost detection."""
    for line in ("`PROVENANCE_VERSION` stays `1`", "PROVENANCE_VERSION = 1",
                 "PROVENANCE_VERSION is 1", "`PROVENANCE_VERSION` stayed 1",
                 "`PROVENANCE_VERSION` → 1", "[![provenance: plumb-line v1](x)](y)",
                 "plumb-line_v1 badge", "envelope schema version 1"):
        assert cvp.scan_text("x.md", line, 2), line


def test_marker_exempts_the_whole_wrapped_block():
    """Exempting one line meant a mention mid-bullet still failed, telling the
    author to add the marker they had already added."""
    wrapped = ("- v0.4.0 shipped; `PROVENANCE_VERSION` stayed 1 for this\n"
               "  release; additive only.\n"
               "  <!-- wire-version-historical -->\n")
    assert cvp.scan_text("ROADMAP.md", wrapped, 2) == []


def test_live_badge_returns_none_instead_of_raising(monkeypatch):
    """report.mjs exits non-zero when conformance diverges — it withholds the
    badge by design. check=True turned that into a traceback in a CI step about
    stale docs, and discarded the prose findings computed before it."""
    import subprocess

    class _Result:
        stdout = ""
        returncode = 1

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Result())
    assert cvp.live_badge() is None


def test_historical_paths_are_exempt():
    assert cvp.is_exempt_path("CHANGELOG.md")
    assert cvp.is_exempt_path("docs/adr/0010-wire-v2-schema-batch.md")
    assert cvp.is_exempt_path("docs/dogfood.md")
    assert cvp.is_exempt_path("docs/validation-results.md")
    assert not cvp.is_exempt_path("README.md")
    assert not cvp.is_exempt_path("ROADMAP.md")

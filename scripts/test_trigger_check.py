"""Tests for scripts/trigger_check.py — the tiered skill-trigger harness (#291).

Covers the pure logic only (matching, scoring, tier selection/merge); the
claude -p probing is exercised manually, not in CI.

Run from the repo root:

    python3 -m pytest -q scripts/test_trigger_check.py
"""
import importlib.util
import os

_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "trigger_check.py")
_spec = importlib.util.spec_from_file_location("_trigger_check", _SCRIPT)
tc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tc)


def test_skill_match_on_field_not_substring():
    # The 2026-08-18 artifact: a query naming plumb-line-audit.md put the
    # string into remediate's args; a raw substring match counted it as an
    # audit trigger. Matching must read the "skill" field.
    remediate = '{"skill": "plumb-line:plumb-line-remediate", "args": "apply plumb-line-audit.md"}'
    audit = '{"skill": "plumb-line:plumb-line-audit"}'
    bare = '{"skill": "plumb-line-audit"}'
    assert tc.skill_match(remediate, "plumb-line-audit") is False
    assert tc.skill_match(audit, "plumb-line-audit") is True
    assert tc.skill_match(bare, "plumb-line-audit") is True
    assert tc.skill_match("not json {", "plumb-line-audit") is False


def test_skill_name_extraction_for_miss_diagnostics():
    # On a miss the harness records WHICH skill won, distinguishing
    # "another skill captured it" from "answered inline with no skill".
    assert tc.skill_name('{"skill": "plumb-line:plumb-line-method"}') == "plumb-line:plumb-line-method"
    assert tc.skill_name("not json {") is None
    assert tc.skill_name('{"args": "no skill field"}') is None


def test_score_pass_rules():
    rows = [
        {"should_trigger": True, "runs": [True, True]},
        {"should_trigger": True, "runs": [False, False]},
        {"should_trigger": False, "runs": [False]},
        {"should_trigger": False, "runs": [True]},
    ]
    scored = tc.score(rows)
    assert [r["pass"] for r in scored] == [True, False, True, False]
    assert scored[0]["trigger_rate"] == 1.0


def test_contested_selection_only_reruns_screen_failures():
    scored = [
        {"query": "a", "should_trigger": True, "pass": True},
        {"query": "b", "should_trigger": True, "pass": False},
        {"query": "c", "should_trigger": False, "pass": False},
        {"query": "d", "should_trigger": False, "pass": True},
    ]
    contested = tc.contested(scored)
    assert [r["query"] for r in contested] == ["b", "c"]


def test_installed_locations_finds_target_and_reports_absence(tmp_path):
    # The 2026-08-18 void run: the target skill did not exist in the probe
    # environment (installed plugin predated it), and 0/10 read as a
    # description gap. The preflight must find where the target is actually
    # installed — and say "nowhere" loudly.
    root = tmp_path / "cache"
    (root / "slopstopper" / "plumb-line" / "0.7.3" / "skills" / "plumb-line-audit").mkdir(parents=True)
    (root / "other" / "toolkit" / "1.0.0" / "skills" / "unrelated").mkdir(parents=True)
    hits = tc.installed_locations("plumb-line-audit", str(root))
    assert hits == [{"plugin": "slopstopper/plumb-line", "version": "0.7.3"}]
    assert tc.installed_locations("plumb-line-adopt", str(root)) == []


def test_stale_installs_flags_versions_behind_the_repo():
    # #295: plugin updates are manual and easy to miss — the owner's install
    # sat at 0.7.3 with 0.9.0 released, voiding a whole measurement run. The
    # preflight compares probed installs against this repo's own version and
    # warns; measuring a stale install stays allowed, but never silently.
    installs = [{"plugin": "slopstopper/plumb-line", "version": "0.7.3"},
                {"plugin": "slopstopper/plumb-line", "version": "0.9.0"},
                {"plugin": "other/thing", "version": "2.0.0"}]
    stale = tc.stale_installs(installs, "0.9.0")
    assert stale == [{"plugin": "slopstopper/plumb-line", "version": "0.7.3"}]
    # Non-semver versions are never flagged (unknown, not stale).
    assert tc.stale_installs([{"plugin": "x", "version": "dev"}], "0.9.0") == []


def test_merge_labels_rates_by_model_tier():
    screen = [
        {"query": "a", "should_trigger": True, "pass": True, "trigger_rate": 1.0},
        {"query": "b", "should_trigger": True, "pass": False, "trigger_rate": 0.0},
    ]
    confirm = [
        {"query": "b", "should_trigger": True, "pass": True, "trigger_rate": 1.0},
    ]
    merged = tc.merge(screen, confirm, screen_model="m-small", confirm_model="m-big")
    by_q = {r["query"]: r for r in merged}
    # Uncontested keeps the screen verdict, labeled with the screen model.
    assert by_q["a"]["measured_by"] == "m-small"
    # Contested takes the confirm verdict, labeled with the confirm model,
    # and keeps the screen result visible rather than overwriting history.
    assert by_q["b"]["measured_by"] == "m-big"
    assert by_q["b"]["pass"] is True
    assert by_q["b"]["screen"] == {"trigger_rate": 0.0, "pass": False}

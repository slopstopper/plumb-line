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


# --- #317: the results JSON is a contracted measurement record --------------

def _merged():
    return [
        {"query": "a", "should_trigger": True, "runs": [True, True],
         "winners": ["plumb-line-audit", "plumb-line-audit"],
         "trigger_rate": 1.0, "pass": True, "measured_by": "haiku"},
        {"query": "b", "should_trigger": False, "runs": [True],
         "winners": ["other"], "trigger_rate": 1.0, "pass": False,
         "measured_by": "haiku"},
    ]


def _payload(**over):
    base = dict(target="t", installs=[], tiers={"screen": "haiku", "confirm": None},
                runs={"screen": 1, "confirm": 2}, threshold=0.5, merged=_merged())
    base.update(over)
    return tc.build_payload(**base)


def test_score_honours_an_injected_threshold():
    rows = [{"should_trigger": True, "runs": [True, False]}]      # rate 0.5
    assert tc.score(rows, threshold=0.5)[0]["pass"] is True
    assert tc.score(rows, threshold=0.75)[0]["pass"] is False


def test_payload_carries_its_contract_and_its_conditions():
    payload = _payload(target="plumb-line-audit",
                       installs=[{"plugin": "o/p", "version": "0.10.0"}])
    keys = list(payload)
    assert keys[0] == "results-format" and payload["results-format"] == tc.RESULTS_FORMAT
    assert payload["threshold"] == 0.5
    assert payload["runs"] == {"screen": 1, "confirm": 2}
    assert payload["summary"] == {"passed": 1, "total": 2}
    assert payload["results"] == _merged()


def test_validate_accepts_the_harness_own_payload():
    assert tc.validate_results(_payload()) == []


def test_validate_flags_missing_contract_and_unknown_version():
    payload = _payload()
    del payload["results-format"]
    assert any("results-format" in i for i in tc.validate_results(payload))
    payload["results-format"] = "v9"
    assert any("v9" in i for i in tc.validate_results(payload))


def test_validate_flags_a_verdict_inconsistent_with_the_stamped_threshold():
    # A stored pass must be reproducible from rate, threshold and expectation;
    # a row that says pass while its numbers say fail is a laundered verdict.
    payload = _payload()
    payload["results"][1]["pass"] = True
    issues = tc.validate_results(payload)
    assert any("row 2" in i and "pass" in i for i in issues), issues


def test_validate_flags_a_threshold_outside_the_unit_interval():
    payload = _payload()
    payload["threshold"] = 1.5
    assert any("threshold" in i for i in tc.validate_results(payload))


def test_validate_rejects_a_boolean_threshold():
    payload = _payload()
    payload["threshold"] = True
    assert any("threshold" in i for i in tc.validate_results(payload))


def test_validate_flags_a_summary_that_does_not_add_up():
    payload = _payload()
    payload["summary"]["passed"] = 2
    assert any("summary" in i for i in tc.validate_results(payload))


def test_cli_threshold_flag_and_its_default():
    args = tc.parse_args(["evals.json", "t", "out.json"])
    assert args.threshold == tc.THRESHOLD == 0.5
    args = tc.parse_args(["evals.json", "t", "out.json", "--threshold", "0.75"])
    assert args.threshold == 0.75


def test_cli_validate_mode_reads_a_results_file(tmp_path):
    import json
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_payload()), encoding="utf-8")
    assert tc.main(["--validate", str(good)]) == 0
    bad = tmp_path / "bad.json"
    bad.write_text('{"target": "t"}', encoding="utf-8")
    assert tc.main(["--validate", str(bad)]) == 1
